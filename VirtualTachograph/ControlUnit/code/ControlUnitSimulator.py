import threading
import socket
import os
import base64
from datetime import datetime, timezone
import subprocess
from time import sleep
import json
import copy
from tb_rest_client.rest_client_ce import *
from Crypto.PublicKey import RSA
from tb_device_mqtt import TBDeviceMqttClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

# Constantes
MAX_SPEED = 90.0 # Velocidad máxima permitida
SPEED_DIFFERENCE = 8.0 # Diferencia máxima entre la velocidad del odómetro y la velocidad del GPS
MAX_CONNECTIONS = 3 
GENERATE_WARNINGS_EVERY = 1 # Generar alertas cada 1 segundo
TELEMETRY_FREQUENCY = 15 # Enviar telemetría a ThingsBoard cada 15 segundos
SENSORS_SAMPLING_FREQUENCY = 5 # Frecuencia  de muestreo de los sensores
FREQUENCY_TRY_ESTABLISH_SESSION = 10 # Frecuencia para intentar establecer la sesión con el message router

def get_host_name():
    """ Get the host name of the machine executing the script --> name of the POD if executed using kubernetes!!"""
    bashCommandName = 'echo $HOSTNAME'
    host = subprocess \
        .check_output(['sh', '-c', bashCommandName]) \
        .decode("utf-8")[0:-1]
    return host

# Variables globales
current_state = {
    "Position": "None",
    "Speed": 0.0,
    "GPSSpeed": 0.0,
    "Driver": "None",
    "Timestamp": 0
}
logs = [] # Lista de logs
event_logs = [] # lista de eventos
last_time = 0 # Último tiempo en el que se generó un log
connected_thingsboard = False
client = None  # Cliente MQTT
rest_client = None  # Cliente REST
session_established = False # Variable para controlar si la sesión con el message router está establecida
my_tachograph_unit_name = os.getenv(get_host_name()+"-id") # Nombre del tacógrafo coincide con el id
current_symmetric_key = None # Clave simétrica de sesión
private_key = None
public_key = None

# Mutex para proteger el acceso a las variables globales
lock_current_state = threading.Lock()
lock_logs = threading.Lock()
lock_telemetry_frequency = threading.Lock()
lock_sensors_sampling_frequency = threading.Lock()
lock_event_logs = threading.Lock()

# Funciones de generación de eventos
def generate_overspeed_warning():
    warning = {
        "Position": current_state["Position"],
        "Warning": f"OVERSPEED: Speed: {current_state['Speed']} - Driver: {current_state['Driver']}",
        "Timestamp": int(datetime.utcnow().timestamp() * 1000)
    }
    print(f"\n[ WARNING ] - {warning['Warning']} - Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} - Position: ({warning['Position']}")
    with lock_event_logs:
        event_logs.append(warning)

def generate_movement_without_driver_warning():
    warning = {
        "Position": current_state["Position"],
        "Warning": f"MOVEMENT WITHOUT DRIVER: Speed: {current_state['Speed']}",
        "Timestamp": int(datetime.utcnow().timestamp() * 1000)
    }
    print(f"\n[ WARNING ] - {warning['Warning']} - Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} - Position: ({warning['Position']})")
    with lock_event_logs:
        event_logs.append(warning)

def generate_speed_incoherence_warning():
    warning = {
        "Position": current_state["Position"],
        "Warning": f"SPEED INCOHERENCE: Speed: {current_state['Speed']} - GPSSpeed: {current_state['GPSSpeed']} - Driver: {current_state['Driver']}",
        "Timestamp": int(datetime.utcnow().timestamp() * 1000)
    }
    print(f"\n[ WARNING ] - {warning['Warning']} - Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} - Position: ({warning['Position']})")
    with lock_event_logs:
        event_logs.append(warning)

def generate_disconnected_driver_event():
    warning = {
        "Position": current_state["Position"],
        "Warning": "DISCONNECTED DRIVER",
        "Timestamp": int(datetime.utcnow().timestamp() * 1000)
    }
    print(f"\n[ WARNING ] - {warning['Warning']} - Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} - Position: ({warning['Position']})")
    with lock_event_logs:
        event_logs.append(warning)

def generate_connected_driver_event():
    warning = {
        "Position": current_state["Position"],
        "Warning": f"CONNECTED DRIVER: Driver: {current_state['Driver']}",
        "Timestamp": int(datetime.utcnow().timestamp() * 1000)
    }
    print(f"\n[ WARNING ] - {warning['Warning']} - Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} - Position: ({warning['Position']})")
    with lock_event_logs:
        event_logs.append(warning)

# --------------------------------- FUNCIONES RELACIONADAS CON LA CRIPTOGRAFÍA ---------------------------------

def sign_message(private_key, message):
    """Firma el mensaje con la clave privada RSA"""
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode()

def verify_signature(public_key, signature, message):
    """
    Verifica si un mensaje ha sido firmado con la clave privada correspondiente a la clave pública dada.

    :param public_key: Clave pública RSA.
    :param signature: Firma digital en base64 (string).
    :param message: Mensaje original en formato bytes.
    :return: True si la firma es válida, False en caso contrario.
    """
    try:
        # Decodificar la firma de base64 a bytes
        signature_bytes = base64.b64decode(signature)

        # Verificar la firma con el mismo esquema PSS usado en `sign_message`
        public_key.verify(
            signature_bytes,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        print("✅ Firma válida.")
        return True

    except Exception as e:
        print(f"❌ Firma inválida: {e}")
        return False
    
def cypher_telemetry(log, symmetric_key):
    """
    Cifra un diccionario 'log' utilizando AES-256 en modo GCM.
    Devuelve un diccionario con el ciphertext, nonce y tag codificados en base64 para enviarlo fácilmente.
    """
    from base64 import b64encode

    nonce = os.urandom(12)  # 12 bytes recomendado para GCM
    cipher = Cipher(algorithms.AES(symmetric_key), modes.GCM(nonce), backend=default_backend())
    encryptor = cipher.encryptor()

    json_data = json.dumps(log).encode('utf-8') # Convertir el diccionario a bytes
    ciphertext = encryptor.update(json_data) + encryptor.finalize() 

    return {
        "ciphertext": b64encode(ciphertext).decode('utf-8'),
        "nonce": b64encode(nonce).decode('utf-8'),
        "tag": b64encode(encryptor.tag).decode('utf-8')
    }


def generate_rsa_keys(size=2048):
    """ Función que se encarga de generar las claves RSA """
    """
    Genera un par de claves RSA (privada y pública).
    
    :param size: Tamaño de la clave en bits (por defecto 2048).
    :return: Tupla (clave_privada_pem, clave_publica_pem)
    """

    clave = RSA.generate(size) 
    clave_privada = clave.export_key().decode()
    clave_publica = clave.publickey().export_key().decode()
    
    return clave_privada, clave_publica

def save_public_key(public_key_pem, filename="public_key.pem"):
    with open(filename, "w") as f:
        f.write(public_key_pem)
    print(f"Clave pública guardada en {filename}")

def save_private_key(private_key_pem, password, filename="private_key.pem"):
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(),
        password=None,
        backend=default_backend()
    )

    encrypted_private_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode())
    )

    with open(filename, "wb") as f:
        f.write(encrypted_private_key)

    print(f"Clave privada cifrada guardada en {filename}")

def load_private_key(password, filename="private_key.pem"):
    with open(filename, "rb") as f:
        encrypted_key = f.read()

    private_key = serialization.load_pem_private_key(
        encrypted_key,
        password=password.encode(),
        backend=default_backend()
    )

    return private_key

def load_public_key(filename="public_key.pem"):
    """Carga una clave pública desde un archivo PEM."""
    try:
        with open(filename, "rb") as f:
            public_key_data = f.read()

        public_key = serialization.load_pem_public_key(public_key_data)
        print(f"Clave pública cargada desde {filename}")
        return public_key

    except Exception as e:
        print(f"Error al cargar la clave pública: {e}")
        return None


def decrypt_with_private_key(encrypted_data, private_key):
    """Descifra los datos cifrados con la clave privada."""
    try:
        # Asegúrate de que encrypted_data esté en formato bytes
        if isinstance(encrypted_data, str):
            encrypted_data = base64.b64decode(encrypted_data)  # Decodificar de base64 a bytes

        # Descifrado de los datos con la clave privada
        decrypted_data = private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        return decrypted_data

    except Exception as e:
        print(f"Error al descifrar los datos con la clave privada: {e}")
        return None
# ----------------------------------------------------------------------------------------------------------------------




# --------------------------------- FUNCIONES RELACIONADAS CON EL MANEJO DEL TACOGRAFO ---------------------------------
def data_logger():
    """ Función que se encarga de generar los logs correspondiente a las alertas """
    global last_time
    while True:
        with lock_current_state: # Mutex para proteger el acceso a las variables globales (current_state)
            if current_state["Timestamp"] > last_time: 
                # Si el conductor no está presente y el vehículo se está moviendo, generamos un aviso
                if current_state["Driver"] == "None" and current_state["Speed"] > 0.0:
                    generate_movement_without_driver_warning()
                # Si la velocidad supera la máxima permitida, generamos un aviso
                if current_state["Speed"] > MAX_SPEED:
                    generate_overspeed_warning()
                # Si la diferencia entre la velocidad del odómetro y la velocidad del GPS supera un umbral, generamos un aviso
                if current_state["Speed"] - current_state["GPSSpeed"] > SPEED_DIFFERENCE:
                    generate_speed_incoherence_warning()

                last_time = int(datetime.utcnow().timestamp() * 1000) # Tiempo en milisegundos
        sleep(GENERATE_WARNINGS_EVERY)

def process_received_message(data):
    """ Obtiene y procesa los mensajes recibidos por el servidor en función del dispositivo que los envía y actualiza el estado actual """
    global current_state
    global logs
    try:
        data = json.loads(data) # Convertimos el mensaje a un diccionario 
        with lock_current_state: # Mutex para proteger el acceso a las variables globales (current_state)
            
            current_state["Timestamp"] = data["Timestamp"]

            # Actualizamos el estado actual en función del tipo de mensaje
            if data["Type"] == "GPS":
                current_state["Position"] = data["Position"]
                current_state["GPSSpeed"] = data["Speed"]

            elif data["Type"] == "Odometer":
                current_state["Speed"] = data["Speed"]

            elif data["Type"] == "CardReader":
                current_state["Driver"] = data["driver_present"]
                # Si el conductor se ha desconectado
                if data["is_driver"] == 0:
                    generate_disconnected_driver_event()
                # Si el conductor se ha conectado
                elif data["is_driver"] == 1:
                    generate_connected_driver_event()

            else:
                print("Error: Unknown message type")
                return
                
            with lock_logs:
                logs.append(copy.deepcopy(current_state)) # Añadimos una copia del estado actual a los logs

    except json.JSONDecodeError as jde:
        print("Error al decodificar el mensaje JSON: ", jde)

    except KeyError as ke:
        print("Error: Missing key in data ", ke)

def client_listener(connection, address):
    global SENSORS_SAMPLING_FREQUENCY
    """ Función que se encarga de recibir los mensajes enviados por los dispositivos. Llama a process_received_message para procesar los mensajes """
    print("{} - New connection {} {}".format(datetime.timestamp(datetime.now()) * 1000, connection, address))
    try:
        while True:
            data = connection.recv(1024) # Recibimos mensajes de 1024 bytes

            if not data:
                continue

            else:
                data = data.decode("utf-8")
                print("{} - He recibido el mensaje: {}".format(datetime.timestamp(datetime.now()) * 1000, data))
                process_received_message(data) 

                # Enviamos un mensaje de confirmación en formato JSON
                confirmation_message = {
                    "Status": "ok",
                    "Timestamp": int(datetime.utcnow().timestamp() * 1000),  # Timestamp en milisegundos
                    "SamplingFrequency": SENSORS_SAMPLING_FREQUENCY
                }
                connection.sendall(bytes(json.dumps(confirmation_message), "utf-8"))

    except ConnectionResetError as cre:
        print("Error de conexión: ", cre)
    except Exception as e:
        print("Error inesperado: ", e)
    finally:
        print("Closing connection...")
        connection.close()

def thingsboard_communications():
    """Función que establece la conexión con ThingsBoard (MQTT + REST)"""
    global client, rest_client, connected_thingsboard, session_established

    # Obtener credenciales de ThingsBoard
    THINGSBOARD_HOST = os.getenv("THINGSBOARD_HOST")
    THINGSBOARD_PORT = int(os.getenv("THINGSBOARD_PORT", 8080))
    THINGSBOARD_PORT_MQTT = int(os.getenv("THINGSBOARD_PORT_MQTT", 1883))
    TENANT_USERNAME = os.getenv("TENANT_USERNAME")
    TENANT_PASSWORD = os.getenv("TENANT_PASSWORD")
    REST_URL = f"{THINGSBOARD_HOST}:{THINGSBOARD_PORT}"

    with open('/etc/secrets/tokens.json') as f:
        tokens = json.load(f)

    DEVICE_TOKEN = tokens.get(get_host_name() + "-ACCESS_TOKEN")

    try:

        # 1. Creamos los clientes REST y MQTT
        # Cliente REST global
        rest_client = RestClientCE(base_url=REST_URL)
        rest_client.login(username=TENANT_USERNAME, password=TENANT_PASSWORD)
        print("✅ Autenticación con ThingsBoard REST exitosa")

        try:
            client = TBDeviceMqttClient(THINGSBOARD_HOST, THINGSBOARD_PORT_MQTT, DEVICE_TOKEN)
            client.set_server_side_rpc_request_handler(on_server_side_rpc_request)  # Manejador RPC
            client.connect()

            # 2. Nos suscribimos a cambios en los atributos
            client.subscribe_to_all_attributes(on_attributes_change)
        except Exception as e:
            print("❌ Error conectando cliente mqtt a Thingsboard: ", e)
        
        # 3. Obtenemos la clave pública del tacografo y la enviamos como atributo compartido mediante Thingsboard
        public_key = load_public_key()
        # Convertimos la clave pública a formato PEM (cadena) para enviarla como atributo
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()

        # Enviar clave pública como atributo compartido mediante API REST
        send_shared_attribute("public_key_tachograph", public_key_pem)  
        print("✅ Clave pública del dispositivo enviada como atributo compartido")

        connected_thingsboard = True

    except Exception as e:
        print("❌ Error conectando a ThingsBoard:", e)
        connected_thingsboard = False
        session_established = False

def send_shared_attribute(attribute_key, attribute_value):
    """Enviar un atributo compartido usando el cliente REST"""
    global rest_client, my_tachograph_unit_name
    CUSTOMER_ID = os.getenv("CUSTOMER_ID")

    if rest_client:
        try:

            # Obtenemos los dispositivos del Customer
            devices_page = rest_client.get_customer_devices(CUSTOMER_ID, page_size=10, page=0)

            devices = devices_page.data  # Extraer la lista de dispositivos
            
            # Se busca el dispositivo que tenga como nombre my_tachograph_name y se envia el atributo compartido
            for device in devices:
                device_id = device.id.id
                device_name = device.name
                
                if device_name == my_tachograph_unit_name:
                    print("Dispositivo", device_name, "encontrado")
                    rest_client.save_device_attributes(device_id, "SHARED_SCOPE", {attribute_key: attribute_value})
                    print(f"✅ Atributo {attribute_key} enviado: {attribute_value} al dipositivo {device_name}")
        
        except Exception as e:
            print(f"❌ Error enviando atributo {attribute_key}:", e)
    else:
        print("REST client is None")

def on_attributes_change(result, exception):
    """ Maneja la configuración de sesión cuando hay un cambio en uno de los atributos correspondientes """
    try:
        if exception is not None: 
            print("Exception:", str(exception)) 
        else:
            print("Attributes have changed!: ", result)

            if "session_encrypted_key" in result:
                # 1. Obtenemos los campos de la información de sesión
                encrypted_symmetric_key = result["session_encrypted_key"]
                session_data = result["session_data"]
                message_router_public_pem = result["message_router_public_key"]
                signature = result["signature"]

                # 2. Si la clave de sesion simétrica no está vacía (significa que se acaba de iniciar la sesion)
                if encrypted_symmetric_key != "":
                    
                    # 2.1 Cargamos la clave pública del Message Router 
                    message_router_public_key = serialization.load_pem_public_key(
                        message_router_public_pem.encode()
                    )

                    # 2.2 Verificamos la firma de la clave simétrica cifrada + la clave pública del message_router para confirmar que ha sido enviada por el message_router
                    combined_data = (encrypted_symmetric_key + message_router_public_pem).encode()
                    print("\nVERIFICAR FIRMA CORRECTA")
                    print("Tipo de message_router_public_key: ", type(message_router_public_key))
                    print("Tipo de signature: ", type(signature))
                    print("Tipo de combined_data ", type(combined_data))
                    print("combined_data ", combined_data, "\n")

                    if not verify_signature(message_router_public_key, signature, combined_data):
                        print("❌ Invalid session signature! Rejecting configuration.")
                        return
                    
                    # 2.3 Desciframos la clave de sesión simétrica con la clave privada del tacografo
                    password_private_key = os.getenv("PRIVATE_KEY_PASSWORD")
                    device_private_key = load_private_key(password_private_key)

                    symmetric_key = decrypt_with_private_key(encrypted_symmetric_key, device_private_key)
                    print("🔑 Session key established successfully!")

                    # 2.4 Guardamos la clave simétrica para futuras comunicaciones
                    global current_symmetric_key
                    current_symmetric_key = symmetric_key

                    global session_established
                    session_established = True
                    print(f"✔️ New session established: {session_data}")

    except Exception as e:
        print("❌ Error processing session configuration:", e)


def on_server_side_rpc_request(request_id, request_body):
    """ Función que se encarga de manejar las peticiones RPC recibidas por el servidor """
    print("\nReceived RPC request: ", request_body, " - Request ID: ", request_id, "\n")
    global my_tachograph_unit_name
    global TELEMETRY_FREQUENCY
    global SENSORS_SAMPLING_FREQUENCY

    response = {}

    if request_body["method"] == "modify_frequencies":
        raw_params = request_body["params"]
        params = json.loads(raw_params)

        # Si la unidad de tacógrafo coincide con la mía, modifico las frecuencias
        if params["TachographUnit"] is not None and params["TachographUnit"] == my_tachograph_unit_name:

            # Modificar la frecuencia de telemetría si está presente
            if params["TelemetryFrequency"] is not None:
                with lock_telemetry_frequency:
                    old_telemetry_frequency = TELEMETRY_FREQUENCY
                    TELEMETRY_FREQUENCY = float(params["TelemetryFrequency"])
                    print("\nFrecuencia de telemetría modificada de {} a {}".format(old_telemetry_frequency, TELEMETRY_FREQUENCY))

            # Modificar la frecuencia de muestreo de sensores si está presente
            if params["SensorsSamplingFrequency"] is not None:
                with lock_sensors_sampling_frequency:
                    old_sensors_sampling_frequency = SENSORS_SAMPLING_FREQUENCY
                    SENSORS_SAMPLING_FREQUENCY = float(params["SensorsSamplingFrequency"])
                    print("\nFrecuencia de muestreo de sensores modificada de {} a {}".format(old_sensors_sampling_frequency, SENSORS_SAMPLING_FREQUENCY))

            # Respuesta de éxito
            response = {
                "status": "success",
                "message": "Frequencies modified successfully.",
                "TelemetryFrequency": TELEMETRY_FREQUENCY,
                "SensorsSamplingFrequency": SENSORS_SAMPLING_FREQUENCY
            }
        else:
            # Respuesta de error si la unidad de tacógrafo no es la esperada
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} The command received is not for me")
            response = {
                "status": "error",
                "message": "The command is not for this tachograph unit."
            }

    else:
        # Si el método RPC no es "modify_frequencies"
        response = {
            "status": "error",
            "message": "Unknown method"
        }

    # Enviar la respuesta al cliente (ThingsBoard)
    client.send_rpc_reply(request_id, response)

def send_telemetry_to_thingsboard():
    """Función que envía telemetría a ThingsBoard en un hilo separado"""
    global client, connected_thingsboard, logs, session_established, current_symmetric_key

    print("Waiting to be connected to ThingsBoard...")
    while True:
        if connected_thingsboard:
            if session_established:
                print(f"Waiting {TELEMETRY_FREQUENCY} to send telemetry to ThingsBoard...")
                sleep(TELEMETRY_FREQUENCY)  # Esperamos TELEMETRY_FREQUENCY segundos antes de enviar datos
                print("Sending telemetry to ThingsBoard...")

                print("\nLogs: ", logs)
                with lock_logs:
                    local_logs = list(logs)  # Copia segura de los logs
                    logs.clear()  # Limpiamos registros después de enviarlos
                
                if local_logs:  # Solo enviar si hay datos en los logs
                    try:
                        for log in local_logs:
                            cyphered_log = cypher_telemetry(log, symmetric_key=current_symmetric_key)
                            password_private_key = os.getenv("PRIVATE_KEY_PASSWORD")
                            device_private_key = load_private_key(password_private_key)

                            telemetry_with_ts = {
                                "ts": int(datetime.utcnow().timestamp() * 1000),  # Timestamp en milisegundos
                                "values": {
                                    "status": "OK",
                                    "message": "Telemetry sent correctly",
                                    "cyphered_telemetry": cyphered_log,
                                }
                            }

                            # Convertimos el objeto de telemetría cifrada a un string JSON antes de firmarlo
                            telemetry_str = json.dumps(telemetry_with_ts["values"]["cyphered_telemetry"], separators=(",", ":"))

                            # Firmamos la telemetria cifrada
                            signature = sign_message(device_private_key, telemetry_str.encode())
                            telemetry_with_ts["values"]["signature"] = signature

                            # Enviamos la telemetría con la firma a ThingsBoard
                            client.send_telemetry(telemetry_with_ts) 
                            print("Telemetry sent to ThingsBoard: ", telemetry_with_ts)

                    except Exception as e:
                        print("\nError sending telemetry to ThingsBoard:", e)
            else:
                # Si aún no se ha configurado el dispositivo (no se ha establecido una sesión con el message router)
                print("Session not established yet. Sending initial telemetry...")

                initial_telemetry = {
                    "ts": int(datetime.utcnow().timestamp() * 1000), 
                    "values": {
                        "status": "Waiting for session configuration",
                        "message": "Device not yet configured"
                    }
                }

                # Enviar telemetría inicial a ThingsBoard
                client.send_telemetry(initial_telemetry)
                print("Initial telemetry sent to ThingsBoard:", initial_telemetry)

                print(f"Esperando {FREQUENCY_TRY_ESTABLISH_SESSION} hasta volver a enviar mensaje de telemetría inicial de nuevo")
                sleep(FREQUENCY_TRY_ESTABLISH_SESSION)
    
def send_events_to_thingsboard():
    global client, connected_thingsboard, session_established, current_symmetric_key

    print("Waiting to be connected to ThingsBoard (for events)...")
    while True:
        if connected_thingsboard and session_established:
            print(f"Waiting {TELEMETRY_FREQUENCY} to send events to ThingsBoard...")
            sleep(TELEMETRY_FREQUENCY)  # Frecuencia a la que se envían los eventos

            with lock_event_logs:
                local_events = list(event_logs)
                event_logs.clear()

            for event in local_events:
                try:
                
                    cyphered_event = cypher_telemetry(event, symmetric_key=current_symmetric_key)
                    password_private_key = os.getenv("PRIVATE_KEY_PASSWORD")
                    device_private_key = load_private_key(password_private_key)

                    # Convertimos el objeto de evento cifrado a un string JSON antes de firmarlo
                    event_str = json.dumps(cyphered_event, separators=(",", ":"))
                    # Firmamos el evento cifrado
                    signature = sign_message(device_private_key, event_str.encode())

                    event_with_ts = {
                        "ts": int(datetime.utcnow().timestamp() * 1000), # Timestamp en milisegundos
                        "values": {
                            "status_event": "OK",
                            "message_event": f"Event sent correctly",
                            "cyphered_event": cyphered_event,
                            "signature_event": signature
                        }
                    }

                    client.send_telemetry(event_with_ts)
                    print(f"Event sent to ThingsBoard: {event_with_ts}")
                except Exception as e:
                    print("\nError sending event to ThingsBoard:", e)
        else:
            print("Not connected/session not established for events.")
            sleep(FREQUENCY_TRY_ESTABLISH_SESSION)

if __name__ == '__main__':
    try:
        # Generamos y guardamos la clave pública y privada del Tacógrafo
        private_key = os.getenv(get_host_name()+"-private-key")
        public_key = os.getenv(get_host_name()+"-public-key")
        password = os.getenv("PRIVATE_KEY_PASSWORD")
        if not password:
            raise ValueError("❌ Error: PRIVATE_KEY_PASSWORD no está definido en las variables de entorno.")
        save_private_key(private_key, password)
        save_public_key(public_key)
        print("Par de claves RSA generadas y guardadas.")

        # Thread que se encarga de generar los logs
        t1 = threading.Thread(target=data_logger, daemon=True)
        # Thread que se encarga de la comunicación con ThingsBoard
        t2 = threading.Thread(target=thingsboard_communications, daemon=True)
        # Thread que se encarga de publicar la telemetria en ThingsBoard
        t3 = threading.Thread(target=send_telemetry_to_thingsboard, daemon=True)
         # Thread que se encarga de publicar los eventos en ThingsBoard
        t4 = threading.Thread(target=send_events_to_thingsboard, daemon=True)

        t1.start()
        t2.start()
        t3.start()
        t4.start()

        HOST = os.getenv("HOST", "127.0.0.1")
        PORT = int(os.getenv("PORT", 5000))
        
        # Escuchamos conexiones de los componenetes card_reader, odometer y gnss
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: 
            s.bind((HOST, PORT)) # Enlazamos el socket al puerto y host
            s.listen(MAX_CONNECTIONS) # Establecemos el número máximo de conexiones
            print("Listening on {}:{}".format(HOST, PORT))

            # Bucle infinito para aceptar conexiones. Se crea un hilo client_listener por cada conexión
            while True:
                print("{} - Waiting for connection...".format(datetime.now()))
                connection, address = s.accept()
                threading.Thread(target=client_listener, args=(connection, address)).start()

        t1.join() 
        t2.join()
        t3.join()
        t4.join()

    except Exception as e:
        print("Error inesperado: ", e)

    finally:
        print("\nTacógrafo desconectado")

