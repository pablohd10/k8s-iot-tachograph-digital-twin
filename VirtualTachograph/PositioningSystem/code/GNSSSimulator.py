import threading
import socket
import os
import subprocess
import datetime
import time
import json
import math

# Constantes
FREQUENCY = 5.0

# Variables globales
position_inputs = [] # Lista de posiciones recibidas. Cada posición es un diccionario con los campos "Origin", "Destination", "Speed" y "Time". Ejemplo: [{'Origin': {'latitude': 40.31044, 'longitude': -3.73683}, 'Destination': {'latitude': 40.31031, 'longitude': -3.73678}, 'Speed': 4.870503597122302, 'Time': 3.092955604015298}]
lock = threading.Lock()  # Mutex para sincronizar acceso a position_inputs

def get_host_name():
    """ Get the host name of the machine executing the script """
    bashCommandName = 'echo $HOSTNAME'
    host = subprocess \
        .check_output(['sh', '-c', bashCommandName]) \
        .decode("utf-8")[0:-1]
    return host

def receive_position_inputs():
    """ Función que se encarga de recibir los mensajes de posición desde el generador de rutas """
    global position_inputs
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", 5002))

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((HOST, PORT))
                s.listen()
                print(f"\n[ Recibir posiciones ] - Listening on {HOST}:{PORT}")

                conn, addr = s.accept()
                with conn:
                    print(f"[ Recibir posiciones ] - Connected by {addr}. Receiving position inputs")
                    # Bucle infinito para recibir mensajes de posición
                    while True:
                        try:
                            data = conn.recv(1024) # Recibimos mensajes de 1024 bytes
                            if not data:
                                break
                            
                            data = data.decode("utf-8") 

                            with lock:
                                position_inputs.append(json.loads(data)) # Añadimos el mensaje a la lista de velocidades

                            conn.sendall(bytes("ok-" + str(time.time()), "utf-8")) # Enviamos un mensaje de confirmación: ok-timestamp

                        except (socket.timeout, json.JSONDecodeError) as e:
                            print(f"\n[ Recibir posiciones ] - Error recibiendo datos: {e}")
                        except Exception as e:
                            print(f"\n[ Recibir posiciones ] - Error inesperado: {e}")
        except ValueError as ve:
            print(f"\n[ Recibir posiciones ] - Error en configuración: {ve}")
        except OSError as oe:
            print(f"\n[ Recibir posiciones ] - Error de socket al iniciar el servidor: {oe}")
        except Exception as e:
            print(f"\n[ Recibir posiciones ] - Error inesperado: {e}")
        finally:
            print("\n[ Recibir posiciones ] - Finalizando recepción de posiciones.\n")

def simulate_positioning():
    """ Función que se encarga de simular la posición actual """
    UC_SIMULATOR_HOST = os.getenv("UC_SIMULATOR_HOST") 
    UC_SIMULATOR_PORT = int(os.getenv("UC_SIMULATOR_PORT", 5000))
    
    global FREQUENCY
    
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((UC_SIMULATOR_HOST, UC_SIMULATOR_PORT))
                print("\n[ Simular posiciones ] - Connected to Control Unit. Simulating positioning...")

                print_empty_warning = True  # Variable para controlar el mensaje de lista vacía
                posiciones_simuladas = False # Variable para controlar si ya han sido simuladas todas las posiciones
                last_position = None  # Variable para almacenar la última posición simulada

                while True:
                    # Copiamos la lista de posiciones para evitar problemas de concurrencia
                    with lock:
                        local_position_inputs = list(position_inputs)  

                    # Mientras haya posiciones en la lista, simulamos la posición actual
                    if local_position_inputs:
                        print("\n[ Simular posiciones ] - Posiciones a simular: ", position_inputs, "\n")
                        for position in local_position_inputs:
                            # Simulamos la posición actual. La posición actual es la posición de origen
                            times = max(1, math.trunc(position["Time"] / FREQUENCY)) # Número de veces que se enviará la posición. Al menos una vez
                            print("[ Simular posiciones ] - Simulating position: ", position, " times: ", times)
                            while times-1 > 0: 
                                simulated_position = {
                                                    "Type": "GPS",
                                                    "Position": position["Origin"], 
                                                    "Speed": position["Speed"],
                                                    "Timestamp": datetime.datetime.timestamp(datetime.datetime.now())
                                                    }
                                print("[ Simular posiciones ] - Sending position: ", simulated_position)
                                s.sendall(bytes(json.dumps(simulated_position), "utf-8"))

                                data = s.recv(1024)
                                if data:
                                    response = json.loads(data.decode("utf-8"))
                                    print("[ Simular posiciones ] - Response received: ", response)
                                    if "SamplingFrequency" in response:
                                        if FREQUENCY != float(response["SamplingFrequency"]):
                                            FREQUENCY = float(response["SamplingFrequency"])
                                            print(f"\n[ Simular posiciones ] - New frequency: {FREQUENCY}\n")
                                
                                print("[ Simular posiciones ] - Waiting ", FREQUENCY, " seconds")
                                time.sleep(FREQUENCY)
                                times -= 1

                            # Se envía la última posición (posición de destino)
                            #Estructura de position: {'Origin':{'latitude': 20.2, 'longitude': 54.1}, 'Destination':{'latitude': 29.2, 'longitude': 74.1}, 'Speed':12.5, 'Time':1.56}
                            last_position = position["Destination"]
                            simulated_position = {
                                                "Type": "GPS", 
                                                "Position": last_position, 
                                                "Speed": position["Speed"],
                                                "Timestamp": datetime.datetime.timestamp(datetime.datetime.now())
                                                }
                            
                            print("[ Simular posiciones ] - Sending destination position: ", simulated_position)
                            s.sendall(bytes(json.dumps(simulated_position), "utf-8"))
                            data = s.recv(1024)
                            if data:
                                response = json.loads(data.decode("utf-8"))
                                if "SamplingFrequency" in response:
                                    if FREQUENCY != float(response["SamplingFrequency"]):
                                        FREQUENCY = response["SamplingFrequency"]
                                        print(f"\n[ Simular posiciones ] - New frequency: {FREQUENCY}\n")
                            print("[ Simular posiciones ] - Waiting ", FREQUENCY, " seconds")
                            time.sleep(FREQUENCY)

                        posiciones_simuladas = True # Marcamos como simuladas todas las posiciones
                        print_empty_warning = True # Variable para controlar el mensaje de lista vacía
                    else:
                        if print_empty_warning:  # Solo imprimimos si no se ha mostrado antes
                            print("\n[ Simular posiciones ] - Lista de posiciones vacía. No hay ruta")
                            print_empty_warning = False  # Marcamos como impreso para no repetirlo
                        if posiciones_simuladas:
                            # Enviamos la última posición. FIN DE LA RUTA. La velocidad es 0
                            simulated_position = {
                                                "Type": "GPS", 
                                                "Position": last_position, 
                                                "Speed": 0.0,
                                                "Timestamp": datetime.datetime.timestamp(datetime.datetime.now())
                                                }
                            s.sendall(bytes(json.dumps(simulated_position), "utf-8"))
                            print("\n[ Simular posiciones ] - Enviada posición final de la ruta. Speed = 0")
                            data = s.recv(1024)
                            if data:
                                response = json.loads(data.decode("utf-8"))
                                if "SamplingFrequency" in response:
                                    if FREQUENCY != response["SamplingFrequency"]:
                                        FREQUENCY = response["SamplingFrequency"]
                                        print(f"\n[ Simular posiciones ] - New frequency: {FREQUENCY}\n")

        except (socket.error, ValueError) as e:
            print(f"\n[ Simular posiciones ] - Error connecting to UC: {e}")
            time.sleep(1)
        except Exception as e:
            print(f"\n[ Simular posiciones ] - Unexpected error: {e}")

if __name__ == '__main__':
    try:
        # Thread que se encarga de recibir los mensajes del generador de rutas
        t1 = threading.Thread(target=receive_position_inputs, daemon=True)
        # Thread que se encarga de simular la posicion actual
        t2 = threading.Thread(target=simulate_positioning, daemon=True)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

    except Exception as e:
        print(e)
