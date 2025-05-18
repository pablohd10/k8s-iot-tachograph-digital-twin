import math
import datetime
import random
import time
import json
import socket
import os
import threading
import subprocess

# Constantes
FREQUENCY = 5.0

# Variables globales
speed_inputs = [] # Lista de velocidades recibidas. Cada velocidad es un diccionario con los campos "Speed" y "Time". Ejemplo: [{"Speed": 50.0, "Time": 10.0}, {"Speed": 60.0, "Time": 20.0}]
lock = threading.Lock()  # Mutex para sincronizar acceso a speed_inputs

def get_host_name():
    """ Get the host name of the machine executing the script """
    bashCommandName = 'echo $HOSTNAME'
    host = subprocess \
        .check_output(['sh', '-c', bashCommandName]) \
        .decode("utf-8")[0:-1]
    print("Host: ", host)
    return host

def receive_speed_inputs():
    """ Función que se encarga de recibir los mensajes de velocidad desde el generador de rutas """
    global speed_inputs # Variable global para almacenar las velocidades recibidas
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5003"))

    while True:
        try:
            # Inicializamos el socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((HOST, PORT))
                s.listen()
                print(f"[ Recibir velocidades ] - Listening on {HOST}:{PORT}")

                # Aceptamos la conexión entrante
                conn, addr = s.accept()
                with conn:
                    print(f"\n [ Recibir velocidades ] - Connected by {addr} Routes Generator. Receiving speeds...")
                    
                    # Bucle infinito para recibir mensajes de velocidad
                    while True:
                        try:
                            # Recibimos mensajes de 1024 bytes y los decodificamos a utf-8
                            data = conn.recv(1024)
                            if not data:
                                break
                            data = data.decode("utf-8")

                            # Añadimos el mensaje a la lista de velocidades. Utilizamos un mutex para evitar problemas de concurrencia
                            with lock:
                                speed_inputs.append(json.loads(data))

                            # Enviamos un mensaje de confirmación: ok-timestamp
                            conn.sendall(bytes("ok-" + str(), "utf-8"))

                        except (socket.timeout, json.JSONDecodeError) as e:
                            print(f"\n [ Recibir velocidades ] - Error recibiendo datos: {e}")
                            break
                        except Exception as e:
                            print(f"\n [ Recibir velocidades ] - Error inesperado: {e}")
                            break
        except ValueError as ve:
            print(f"\n [ Recibir velocidades ] - Error en configuración: {ve}")
        except OSError as oe:
            print(f"\n [ Recibir velocidades ] - Error de socket al iniciar el servidor: {oe}")
        except Exception as e:
            print(f"\n [ Recibir velocidades ] - Error inesperado: {e}")
        finally:
            print("\n [ Recibir velocidades ] - Finalizando recepción de velocidades.")
            time.sleep(0.1)


def simulate_current_speed():
    UC_SIMULATOR_HOST = os.getenv("UC_SIMULATOR_HOST") 
    UC_SIMULATOR_PORT = int(os.getenv("UC_SIMULATOR_PORT", 5000))

    global FREQUENCY

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((UC_SIMULATOR_HOST, UC_SIMULATOR_PORT))
                print("\n [ Simular velocidades ] - Connected to Control Unit. Simulating speed...\n")

                print_empty_warning = True  # Variable para controlar el log de lista vacía
        
                while True:
                    with lock:
                        local_speed_inputs = list(speed_inputs)  # Copia segura de la lista

                    if local_speed_inputs:
                        print("\n[ Simular velocidades ] - Velocidades a simular: ", speed_inputs)
                        
                        for speed in local_speed_inputs:
                            times = max(1, math.trunc(speed["Time"] / FREQUENCY)) # Número de veces que se enviará la velocidad 
                            print(f"[ Simular velocidades ] - Enviando velocidad {speed['Speed']} durante {speed['Time']} segundos ({times} veces)")

                            # Determinamos si es la primera vez
                            first_time = True

                            for i in range(times):
                                if first_time:  # Si es la primera vez que enviamos la velocidad
                                    random_speed = speed["Speed"] + random.uniform(-5.0, 5.0)
                                    first_time = False  # Cambiar la bandera a False para las siguientes iteraciones

                                else:  # Si no es la primera vez
                                    random_speed += random.uniform(-5.0, 5.0)

                                # Nos aseguramos que la velocidad no sea negativa
                                random_speed = max(0, random_speed)

                                simulated_speed = {
                                            "Type": "Odometer", 
                                            "Speed": random_speed, 
                                            "Timestamp": datetime.datetime.timestamp(datetime.datetime.now())
                                            }   
                                try:
                                    print("[ Simular velocidades ] - sending speed: ", simulated_speed)
                                    s.sendall(bytes(json.dumps(simulated_speed), "utf-8"))

                                    # Esperamos la respuesta de la unidad de control. Si contiene el campo "SamplingFrequency", actualizamos la frecuencia de muestreo
                                    data = s.recv(1024)
                                    if data:
                                        response = json.loads(data.decode("utf-8"))
                                        print("[ Simular velocidades ] - Response received: ", response)
                                        if "SamplingFrequency" in response:
                                            if FREQUENCY != float(response["SamplingFrequency"]):
                                                FREQUENCY = float(response["SamplingFrequency"])
                                                print(f"\n[ Simular velocidades ] - New frequency: {FREQUENCY}\n")
                                    else:
                                        print("[ Simular velocidades ] - No data received from Control Unit")

                                    print(f"[ Simular velocidades ] - Waiting {FREQUENCY} seconds for next speed...")
                                    time.sleep(FREQUENCY)
                                    times -= 1 

                                except BrokenPipeError:
                                    print("\n [ Simular velocidades ] - Conexión cerrada por la unidad de control. Saliendo...")
                                    break  # Salimos del bucle si la conexión se cierra

                        print_empty_warning = True # Reiniciamos la variable para mostrar el log de lista vacía
                    else:
                        if print_empty_warning:  # Solo imprimimos si no se ha mostrado antes
                            print("\n [ Simular velocidades ] - Lista de velocidades vacía\n")
                            print_empty_warning = False  # Marcamos como impreso para no repetirlo

        except (socket.error, ValueError) as e:
            print(f"\n [ Simular velocidades ] - Error connecting to Control Unit: {e}\n")
            time.sleep(0.1)
        except Exception as e:
            print(f"\n [ Simular velocidades ] - Unexpected error: {e}\n")
        
if __name__ == '__main__':
    try:
        # Thread que se encarga de recibir los mensajes de velocidad
        t1 = threading.Thread(target=receive_speed_inputs, daemon=True)
         # Thread que se encarga de simular la velocidad actual
        t2 = threading.Thread(target=simulate_current_speed, daemon=True)

        t1.start()
        t2.start()
        
        t1.join()
        t2.join()

    except Exception as e:
        print(e)
