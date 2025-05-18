import json
import os
import threading
from time import sleep
import datetime
import base64
import signal
import sys
from base64 import b64decode
from telemetry_register_interface import register_telemetry
from events_register_interface import register_event
from tb_rest_client.rest_client_ce import *
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

# Variables globales
active_devices = {} # {device_id : { public_key : value }, {session_key : value } }

FREQUENCY_CHECK_ACTIVE_DEVICES = 30
FREQUENCY_CHECK_TELEMETRY = 30
FREQUENCY_CHECK_EVENTS = 30

# Diccionario para almacenar último timestamp de consulta por dispositivo
last_query_timestamps = {}
last_event_query_timestamps = {}


# --------------------------------- FUNCIONES RELACIONADAS CON LA CRIPTOGRAFÍA ---------------------------------
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
        return True

    except Exception as e:
        print(f"❌ Firma inválida: {e}")
        return False

def decrypt_with_private_key(encrypted_data, private_key):
    """Descifra los datos cifrados con la clave privada."""
    try:
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
    
def generate_symmetric_key():
    """Genera una clave AES-256 aleatoria"""
    return os.urandom(32)  # 256 bits (32 bytes)

def encrypt_with_public_key(data, public_key):
    """Cifra datos con la clave pública RSA"""
    encrypted_data = public_key.encrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(encrypted_data).decode()

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

def decipher_log(encrypted_data, symmetric_key):
    """
    Descifra un log previamente cifrado con AES-GCM.
    Recibe un diccionario con 'ciphertext', 'nonce' y 'tag' en base64.
    Devuelve el diccionario original (log).
    """

    ciphertext = b64decode(encrypted_data["ciphertext"])
    nonce = b64decode(encrypted_data["nonce"])
    tag = b64decode(encrypted_data["tag"])

    cipher = Cipher(algorithms.AES(symmetric_key), modes.GCM(nonce, tag), backend=default_backend())
    decryptor = cipher.decryptor()

    decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()
    log = json.loads(decrypted_data.decode('utf-8'))
    return log

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

def generate_rsa_keys(size=2048):
    """Genera un par de claves RSA"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=size
    )

    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    return private_key, public_key_pem 

def save_public_key(public_key_pem, filename="public_key.pem"):
    """Guarda la clave pública en un archivo"""
    with open(filename, "w") as f:
        f.write(public_key_pem)
    print(f"Clave pública guardada en {filename}")

def save_private_key(private_key, password, filename="private_key.pem"):
    """Guarda la clave privada cifrada con una contraseña"""
    encrypted_private_key = private_key.private_bytes(  # 🔥 Ahora `private_key` es un OBJETO válido
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

# ---------------------------------------------------------------------------------------------------




# --------------------------------- FUNCIONES RELACIONADAS CON EL MANEJO DE LOS TACOGRAFOS ---------------------------------
def generate_session_config(device_id, device_public_key, message_router_private_key, message_router_public_key):
    """Genera y serializa la configuración cifrada de la sesión en un solo atributo."""
    global active_devices

    # Ciframos la clave simétrica con la clave pública del dispositivo para que solo la pueda descifrar él
    symmetric_key = generate_symmetric_key()
    active_devices[device_id] = {"session_key": symmetric_key}
    print("Active devices: ", active_devices)
    encrypted_symmetric_key = encrypt_with_public_key(symmetric_key, device_public_key)

    # Datos de sesión  
    session_data = {
        "session_id": os.urandom(16).hex(),
        "timestamp": datetime.datetime.timestamp(datetime.datetime.now()) * 1000
    }

    # Convertimos a formato pem la clave pública del message_router
    message_router_public_pem = message_router_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    # Firmamos la clave simétrica cifrada y la clave pública del message_router con la clave privada del message_router
    combined_data = (encrypted_symmetric_key + message_router_public_pem).encode()
    print("\nFIRMA CORRECTA")
    signature = sign_message(message_router_private_key, combined_data)

    # Serializamos toda la información en un solo JSON
    session_config = {
        "session_encrypted_key": encrypted_symmetric_key,
        "session_data": session_data,
        "message_router_public_key": message_router_public_pem,
        "signature": signature
    }

    return session_config  # Devolvemos un solo string JSON con toda la información de sesión

def receive_telemetry():
    """ 
        Hilo que monitoriza la telemetría generada por los tacógrafos. 
        Consulta periódicamente a ThingsBoard, recupera datos cifrados y firmados, 
        verifica la firma y descifra la telemetría si es válida. 
    """
    global active_devices, last_query_timestamps

    # Obtener variables de entorno necesarias para conectarse a ThingsBoard
    THINGSBOARD_HOST = os.getenv("THINGSBOARD_HOST")
    THINGSBOARD_PORT = os.getenv("THINGSBOARD_PORT")
    TENANT_USERNAME = os.getenv("TENANT_USERNAME")
    TENANT_PASSWORD = os.getenv("TENANT_PASSWORD")
    THINGSBOARD_URL = f"{THINGSBOARD_HOST}:{THINGSBOARD_PORT}"
    CUSTOMER_ID = os.getenv("CUSTOMER_ID")

    try:
        # Crear cliente REST y autenticarse con las credenciales del tenant
        with RestClientCE(base_url=THINGSBOARD_URL) as rest_client:

            # Autenticación
            rest_client.login(username=TENANT_USERNAME, password=TENANT_PASSWORD)
            print("[ Receive Telemetry ] ✅ Autenticación en ThingsBoard exitosa")

            while True:
                # Obtener lista de dispositivos registrados bajo el cliente especificado
                devices_page = rest_client.get_customer_devices(CUSTOMER_ID, page_size=10, page=0)
                devices = devices_page.data

                for device in devices:
                    device_id = device.id.id
                    device_name = device.name

                    # Saltar dispositivos que no están activos actualmente
                    if device_id not in active_devices:
                        continue

                    print(f"[ Receive Telemetry ] 🔍 Consultando telemetría de {device_name} (ID: {device_id})")

                    # Obtener atributos del servidor: lastActivityTime (timestamp de la última actividad del dispositivo)
                    attrs = rest_client.get_attributes_by_scope(
                        EntityId(device.id, 'DEVICE'),
                        'SERVER_SCOPE',
                        keys=["lastActivityTime"]
                    )

                    # Determinar el rango de tiempo a consultar: desde la última actividad hasta ahora
                    if not attrs:
                        # Si no hay atributo registrado, usar valor anterior o asumir una ventana de 1 minuto
                        current_timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
                        last_timestamp = last_query_timestamps.get(device_id, current_timestamp - 60000)
                    else:
                        last_activity_ts = int(attrs[0]["value"])
                        last_timestamp = last_activity_ts
                        current_timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)

                    print(f"[ Receive Telemetry ] Rango: {last_timestamp} - {current_timestamp}")

                    # Guardar timestamp actual para próxima iteración
                    last_query_timestamps[device_id] = current_timestamp

                    # Obtener datos de telemetría cifrada y sus firmas en el rango de tiempo especificado
                    telemetry_data = rest_client.get_timeseries(
                        EntityId(device.id, 'DEVICE'),
                        keys='cyphered_telemetry,signature',
                        start_ts=last_timestamp,
                        end_ts=current_timestamp,
                        limit=500
                    )

                     # Verificar que existen datos de telemetría cifrada
                    if not telemetry_data or 'cyphered_telemetry' not in telemetry_data:
                        print(f"[ Receive Telemetry ] ⚠️ No hay datos de telemetría para {device_name}.")
                        continue
                    
                    # Obtener la clave de sesión del dispositivo activo
                    session_key = active_devices[device_id].get("session_key")
                    if not session_key:
                        print(f"[ Receive Telemetry ] ⚠️ No se encontró clave de sesión para {device_name}.")
                        continue
                    
                    # Iterar sobre los datos de telemetría
                    for idx, value_entry in enumerate(telemetry_data['cyphered_telemetry']):
                        telemetry_str = value_entry["value"]
                        timestamp = value_entry["ts"]

                        try:
                             # Obtener firma correspondiente al dato de telemetría
                            signature_value = telemetry_data['signature'][idx]["value"]
                        except Exception as e:
                            print(f"[ Receive Telemetry ] ❌ No se pudo obtener firma: {e}")
                            continue
                        
                        # Cargar clave pública del dispositivo desde PEM
                        device_public_key_str = active_devices[device_id]["public_key"]
                        device_public_key = serialization.load_pem_public_key(device_public_key_str.encode())

                         # Verificar la firma antes de descifrar el contenido
                        if verify_signature(device_public_key, signature_value, telemetry_str.encode()):
                             # Firma válida → descifrar contenido
                            decrypted_data = decipher_log(json.loads(telemetry_str), session_key)
                            readable_time = datetime.datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                            print(f"[ Receive Telemetry ] ✅ ({readable_time}) Telemetría válida de {device_name}: {decrypted_data}")
                            
                            # Añadir timestamp legible antes de enviar
                            decrypted_data["Timestamp"] = readable_time
                            # Añadir id del tacografo antes de enviar
                            decrypted_data["Tachograph_id"] = device_name

                            # Enviar telemetría al microservicio de telemetría
                            try:
                                response = register_telemetry(decrypted_data)
                                print(f"[ Receive Telemetry ] 🚀 Telemetría enviada al microservicio: {response}")
                            except Exception as e:
                                print(f"[ Receive Telemetry ] ❌ Error al enviar al microservicio de telemetría: {e}")
                                                    
                        else:
                            print(f"[ Receive Telemetry ] ⚠️ Firma inválida para un dato de {device_name}.")

                # Esperar antes de la siguiente iteración (frecuencia definida globalmente)
                print(f"\nEsperando {FREQUENCY_CHECK_TELEMETRY} segundos antes de la próxima consulta...\n")
                sleep(FREQUENCY_CHECK_TELEMETRY)

    except Exception as e:
        print("[ Receive Telemetry ] ❌ Error en la monitorización:", e)

def receive_events():
    """
    Hilo que monitoriza eventos generados por los tacógrafos.
    Consulta periódicamente a ThingsBoard, verifica firma y descifra los eventos.
    """
    global active_devices, last_event_query_timestamps

    THINGSBOARD_HOST = os.getenv("THINGSBOARD_HOST")
    THINGSBOARD_PORT = os.getenv("THINGSBOARD_PORT")
    TENANT_USERNAME = os.getenv("TENANT_USERNAME")
    TENANT_PASSWORD = os.getenv("TENANT_PASSWORD")
    THINGSBOARD_URL = f"{THINGSBOARD_HOST}:{THINGSBOARD_PORT}"
    CUSTOMER_ID = os.getenv("CUSTOMER_ID")

    try:
        with RestClientCE(base_url=THINGSBOARD_URL) as rest_client:
            rest_client.login(username=TENANT_USERNAME, password=TENANT_PASSWORD)
            print("[ Receive Events ] ✅ Autenticación en ThingsBoard exitosa")

            while True:
                devices_page = rest_client.get_customer_devices(CUSTOMER_ID, page_size=10, page=0)
                devices = devices_page.data

                for device in devices:
                    device_id = device.id.id
                    device_name = device.name

                    if device_id not in active_devices:
                        continue

                    print(f"[ Receive Events ] 🔍 Consultando eventos de {device_name} (ID: {device_id})")

                    attrs = rest_client.get_attributes_by_scope(
                        EntityId(device.id, 'DEVICE'),
                        'SERVER_SCOPE',
                        keys=["lastActivityTime"]
                    )

                    # Determinar el rango de tiempo a consultar: desde la última actividad hasta ahora
                    if not attrs:
                        current_timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
                        # Si no hay atributo registrado, usar valor anterior o asumir una ventana de 1 minuto
                        last_timestamp = last_event_query_timestamps.get(device_id, current_timestamp - 60000)
                    else:
                        # Si hay atributo registrado, usarlo como último timestamp
                        # y el timestamp actual como límite superior
                        last_timestamp = int(attrs[0]["value"])
                        current_timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)

                    print(f"[ Receive Events ] Rango: {last_timestamp} - {current_timestamp}")
                    last_event_query_timestamps[device_id] = current_timestamp

                    # Obtener datos de eventos cifrados y sus firmas en el rango de tiempo especificado
                    event_data = rest_client.get_timeseries(
                        EntityId(device.id, 'DEVICE'),
                        keys='cyphered_event,signature_event',
                        start_ts=last_timestamp,
                        end_ts=current_timestamp,
                        limit=500
                    )
                    # Verificar que existen datos de eventos cifrados
                    if not event_data or 'cyphered_event' not in event_data:
                        print(f"[ Receive Events ] ⚠️ No hay eventos para {device_name}.")
                        continue

                    # Obtener la clave de sesión del dispositivo activo
                    session_key = active_devices[device_id].get("session_key")
                    if not session_key:
                        print(f"[ Receive Events ] ⚠️ No se encontró clave de sesión para {device_name}.")
                        continue
                    
                    # Iterar sobre los datos de eventos
                    for idx, value_entry in enumerate(event_data['cyphered_event']):
                        event_str = value_entry["value"]
                        timestamp = value_entry["ts"]
                        # Obtener firma correspondiente al dato de evento
                        try:
                            signature_value = event_data['signature_event'][idx]["value"]
                        except Exception as e:
                            print(f"[ Receive Events ] ❌ No se pudo obtener firma: {e}")
                            continue
                        
                        # Cargar clave pública del dispositivo desde PEM
                        device_public_key_str = active_devices[device_id]["public_key"]
                        device_public_key = serialization.load_pem_public_key(device_public_key_str.encode())

                        # Verificar la firma antes de descifrar el contenido
                        if verify_signature(device_public_key, signature_value, event_str.encode()):
                            decrypted_event = decipher_log(json.loads(event_str), session_key)
                            readable_time = datetime.datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                            print(f"[ Receive Events ] ✅ ({readable_time}) Evento válido de {device_name}: {decrypted_event}")
                            
                            decrypted_event["Timestamp"] = readable_time
                            decrypted_event["Tachograph_id"] = device_name

                            try:
                                response = register_event(decrypted_event)
                                print(f"[ Receive Events ] 🚀 Evento enviado al microservicio: {response}")
                            except Exception as e:
                                print(f"[ Receive Events ] ❌ Error al enviar al microservicio de eventos: {e}")
                        else:
                            print(f"[ Receive Events ] ⚠️ Firma inválida para un evento de {device_name}.")

                print(f"\nEsperando {FREQUENCY_CHECK_EVENTS} segundos antes de la próxima consulta de eventos...\n")
                sleep(FREQUENCY_CHECK_EVENTS)

    except Exception as e:
        print("[ Receive Events ] ❌ Error en la monitorización de eventos:", e)

def monitor_tacograph_conexions():
    THINGSBOARD_HOST = os.getenv("THINGSBOARD_HOST")
    THINGSBOARD_PORT = os.getenv("THINGSBOARD_PORT")
    TENANT_USERNAME = os.getenv("TENANT_USERNAME")
    TENANT_PASSWORD = os.getenv("TENANT_PASSWORD")
    THINGSBOARD_URL = f"{THINGSBOARD_HOST}:{THINGSBOARD_PORT}"
    CUSTOMER_ID = os.getenv("CUSTOMER_ID")

    global actice_devices
    
    try:
        with RestClientCE(base_url = THINGSBOARD_URL) as rest_client:

            # Autenticación en ThingsBoard
            rest_client.login(username=TENANT_USERNAME, password=TENANT_PASSWORD)
            print("[ monitor_tacograph_conexions ] Autenticación con ThingsBoard exitosa")
            
            # Monitoreo cada FREQUENCY_CHECK_ACTIVE_DEVICES para comprobar si hay nuevos dispositivos activos
            while True: 
                # Obtenemos los dispositivos del Customer
                devices_page = rest_client.get_customer_devices(CUSTOMER_ID, page_size=10, page=0)

                devices = devices_page.data  # Extraer la lista de dispositivos

                # Para cada dispositivo
                for device in devices:
                    device_id = device.id.id
                    device_name = device.name

                    print(f"[ monitor_tacograph_conexions ] 🔍 Consultando actividad de {device_name} (ID: {device_id})")
                    
                    # Obtener atributo del servidor "active" para verificar si está activo
                    attributes = rest_client.get_attributes_by_scope(EntityId(device.id, 'DEVICE'), 'SERVER_SCOPE', "active")

                    print(f"[ monitor_tacograph_conexions ] Atributo active del dispositivo {device_name}: {attributes}")

                    # Si no tiene atributo active
                    if not attributes:
                        continue

                    is_active = attributes[0]["value"]
                    print(f"Dispositivo activo: {is_active}")
                    

                    # Si el dispositivo está activo y NO estaba antes en la lista --> CONEXIÓN DEL TACOGRAFO
                    if is_active and device_id not in active_devices:
                        print(f"🟢 [ monitor_tacograph_conexions ] {device_name} (ID: {device_id}) se ha conectado.\n")

                        # 1. Se obtiene la clave pública del tacógrafo
                        device_public_key_attribute = rest_client.get_attributes_by_scope(EntityId(device.id, 'DEVICE'), 'SHARED_SCOPE', "public_key_tachograph")
                        if not device_public_key_attribute:
                            print(f"[ monitor_tacograph_conexions ] ⚠️ No se encontró clave pública para {device_name}.")
                            continue
                        device_public_key_str = device_public_key_attribute[0]["value"]
                        print(f"[ monitor_tacograph_conexions ] Clave publica del dispositivo {device_id}: {device_public_key_str}")

                        # 2. Se obtienen las claves publica y privada del message router
                        print("[ monitor_tacograph_conexions ] Cargando clave publica y privada del mesage router...")
                        message_router_public_key = load_public_key()
                        # Cargar clave privada del message_router
                        password = os.getenv("PRIVATE_KEY_PASSWORD")
                        message_router_private_key = load_private_key(password=password)                   
                        print("[ monitor_tacograph_conexions ] Claves publica y privada del mesage router cargadas. Generando clave de sesion...")

                        # 3. Se genera la información de la sesión (clave de sesión)
                        device_public_key = serialization.load_pem_public_key(device_public_key_str.encode())
                        # Generar configuración de sesión cifrada
                        session_config = generate_session_config(
                            device_id,
                            device_public_key,
                            message_router_private_key,
                            message_router_public_key
                        )
                        print("[ monitor_tacograph_conexions ] Información de sesión generada")

                        # 4. Se envía la información de sesión al tacógrafo por medio de atributos compartidos de Thingsboard
                        rest_client.save_device_attributes(device_id, "SHARED_SCOPE", session_config)
                        print("[ monitor_tacograph_conexions ] Informacion de sesion guardada como atributo compartido: ", session_config)

                        # 5. Guardamos el dispositivo activo con su clave publica en la lista de dispositivos activos
                        active_devices[device_id]["public_key"] = device_public_key_str
                        print("\n Active devices", active_devices)

                    # Si el dispositivo ya no está activo pero estaba en la lista
                    elif not is_active and device_id in active_devices:
                        print(f"🔴 [ monitor_tacograph_conexions ] {device_name} (ID: {device_id}) se ha desconectado.")
                        # Generar información de configuración de sesión vacía
                        session_config = {
                            "session_encrypted_key": "",
                            "session_data": {
                                "session_id": "",
                                "timestamp": 0
                            },
                            "message_router_public_key": "",
                            "signature": ""
                        }

                        # Actualizar el atributo compartido con la configuración de sesión vacía
                        rest_client.save_device_attributes(device_id, "SHARED_SCOPE", session_config)

                        # Eliminar el dispositivo de la lista de vehículos conectados
                        del active_devices[device_id]

                        print(f"🛑 [ monitor_tacograph_conexions ] {device_name} (ID: {device_id}) ha sido eliminado de la lista de dispositivos activos.")

                print(f"\n[ monitor_tacograph_conexions ] Waiting {FREQUENCY_CHECK_ACTIVE_DEVICES} seconds to check active devices again...\n")
                sleep(FREQUENCY_CHECK_ACTIVE_DEVICES)  # Esperamos FREQUENCY_CHECK_ACTIVE_DEVICES segundos antes de la próxima verificación

    except Exception as e:
        print("❌ Error inesperado", e)

def handle_sigterm(signum, frame):
    # TERMINAR SESIONES
    print("Recibida señal SIGTERM. Ejecutando limpieza de atributos de sesión...")
    THINGSBOARD_HOST = os.getenv("THINGSBOARD_HOST")
    THINGSBOARD_PORT = os.getenv("THINGSBOARD_PORT")
    TENANT_USERNAME = os.getenv("TENANT_USERNAME")
    TENANT_PASSWORD = os.getenv("TENANT_PASSWORD")
    THINGSBOARD_URL = f"{THINGSBOARD_HOST}:{THINGSBOARD_PORT}"
    CUSTOMER_ID = os.getenv("CUSTOMER_ID")
                                
    session_config = {
                            "session_encrypted_key": "",
                            "session_data": {
                                "session_id": "",
                                "timestamp": 0
                            },
                            "message_router_public_key": "",
                            "signature": ""
                        }
    try:
        with RestClientCE(base_url=THINGSBOARD_URL) as rest_client:
            # Autenticación en ThingsBoard
            rest_client.login(username=TENANT_USERNAME, password=TENANT_PASSWORD)
            print("Autenticación en ThingsBoard exitosa")

            # Obtenemos los dispositivos del Customer
            devices_page = rest_client.get_customer_devices(CUSTOMER_ID, page_size=10, page=0)
            print(f"Dispositivos obtenidos para el customer {CUSTOMER_ID}: {devices_page}")

            devices = devices_page.data  # Extraer la lista de dispositivos

            # Para cada dispositivo
            for device in devices:
                device_id = device.id.id
                # Actualizar el atributo compartido con la configuración de sesión vacía
                rest_client.save_device_attributes(device_id, "SHARED_SCOPE", session_config)

            print("\nSesiones terminadas")
            sys.exit(0)  # Termina el programa de manera controlada

    except Exception as e:
        print("Intento de establecer informacion de sesion a valores vacíos fallido")
        

if __name__ == '__main__':
    try:
        print("Generando par de claves RSA para el message_router...")
        # Generamos y guardamos la clave pública y privada del Message Router
        private_key, public_key = generate_rsa_keys()
        print("Par de claves RSA generadas.")
        password = os.getenv("PRIVATE_KEY_PASSWORD")
        if not password:
            raise ValueError("❌ Error: PRIVATE_KEY_PASSWORD no está definido en las variables de entorno.")
        save_private_key(private_key, password)
        save_public_key(public_key)
        print("Par de claves RSA guardadas.")

        # Thread que se encarga de manejar los mensajes de telemetría recibidos
        t1 = threading.Thread(target=receive_telemetry, daemon=True)
        # Thread que se encarga de manejar los mensajes de eventos recibidos
        t2 = threading.Thread(target=receive_events, daemon=True)
        # Thread que se encarga de la monitorerar conexiones de tacografos
        t3 = threading.Thread(target=monitor_tacograph_conexions, daemon=True)

        t1.start()
        t2.start()
        t3.start()

        signal.signal(signal.SIGTERM, handle_sigterm)
        
        t1.join() 
        t2.join()
        t3.join()

    except Exception as e:
        print("❌ Error inesperado: ", e)
    
    # TERMINAR SESIONES
    finally:
        THINGSBOARD_HOST = os.getenv("THINGSBOARD_HOST")
        THINGSBOARD_PORT = os.getenv("THINGSBOARD_PORT")
        TENANT_USERNAME = os.getenv("TENANT_USERNAME")
        TENANT_PASSWORD = os.getenv("TENANT_PASSWORD")
        THINGSBOARD_URL = f"{THINGSBOARD_HOST}:{THINGSBOARD_PORT}"
        CUSTOMER_ID = os.getenv("CUSTOMER_ID")

        session_config = {
                            "session_encrypted_key": "",
                            "session_data": {
                                "session_id": "",
                                "timestamp": 0
                            },
                            "message_router_public_key": "",
                            "signature": ""
                        }

        try:
            with RestClientCE(base_url=THINGSBOARD_URL) as rest_client:

                # Autenticación en ThingsBoard
                rest_client.login(username=TENANT_USERNAME, password=TENANT_PASSWORD)
                print("Autenticación en ThingsBoard exitosa")
                
                # Obtenemos los dispositivos del Customer
                devices_page = rest_client.get_customer_devices(CUSTOMER_ID, page_size=10, page=0)

                devices = devices_page.data  # Extraer la lista de dispositivos

                # Para cada dispositivo
                for device in devices:
                    device_id = device.id.id
                    device_name = device.name
                    # Actualizar el atributo compartido con la configuración de sesión vacía
                    rest_client.save_device_attributes(device_id, "SHARED_SCOPE", session_config)

                print("\nSesiones terminadas")

        except Exception as e:
            print("Intento de establecer informacion de sesion a valores vacíos fallido")
