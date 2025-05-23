import os
import socket
import random
import datetime
import time
import json

FREQUENCY = 5.0

def simulate_current_driver():
    global FREQUENCY

    UC_SIMULATOR_HOST = os.getenv("UC_SIMULATOR_HOST") 
    UC_SIMULATOR_PORT = int(os.getenv("UC_SIMULATOR_PORT"))

    if not UC_SIMULATOR_HOST or not UC_SIMULATOR_PORT:
        raise ValueError("UC_SIMULATOR_HOST or UC_SIMULATOR_PORT are not set.")
    
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((UC_SIMULATOR_HOST, UC_SIMULATOR_PORT))
                print("Connected to Control Unit. Simulating drivers...")
                
                # Bucle infinito para simular la presencia de un conductor (conexion o desconexión)
                while True:
                    try:
                        is_driver = random.choice([0, 1])  # 0 = Desconexión del conductor, 1 = Conexión del conductor
                        driver_present = f"Driver{random.choice([1, 2, 3])}" if is_driver else "None" # Si el conductor se ha conectado, elegimos un conductor aleatorio

                        simulated_driver = {
                            "Type": "CardReader",
                            "is_driver": is_driver,
                            "driver_present": driver_present,
                            "Timestamp": int(datetime.datetime.utcnow().timestamp() * 1000)
                        }

                        print("Sending simulated driver: ", simulated_driver)
                        s.sendall(bytes(json.dumps(simulated_driver), "utf-8"))

                        data = s.recv(1024)
                        if data:
                            # Convertimos los datos recibidos de bytes a un diccionario (JSON)
                            response = json.loads(data.decode("utf-8"))
                            print("Response received: ", response)
                            
                            # Si contiene el campo "SamplingFrequency", actualizamos la frecuencia de muestreo
                            if "SamplingFrequency" in response:
                                if FREQUENCY != float(response["SamplingFrequency"]):
                                    FREQUENCY = float(response["SamplingFrequency"])
                                    print(f"New frequency: {FREQUENCY}")
                        else:
                            print("No data received from Control Unit")
                        
                        print(f"Waiting {FREQUENCY} seconds")
                        time.sleep(FREQUENCY) # Esperamos un tiempo aleatorio antes de enviar el siguiente mensaje (simulación)

                    except (socket.error, json.JSONDecodeError) as e:
                        print(f"Error during simulation: {e}")
                        time.sleep(FREQUENCY)
                    except Exception as e:
                        print(f"Unexpected error: {e}")
                        time.sleep(FREQUENCY)

        except (socket.error, ValueError) as e:
            print(f"Error connecting to Control Unit: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            print("Esperando para reintentar conexion...")
            time.sleep(0.1)


if __name__ == '__main__':
    try:
        simulate_current_driver()
    except Exception as e:
        print(f"Unexpected error: {e}")
    
