import threading
import os
import requests
import time
import json
import socket
from math import cos, sin, radians, acos

def generate_route_simulations(origin, destination):
    """ Función que se encarga de generar las simulaciones de ruta """
    try:
        url = "https://maps.googleapis.com/maps/api/directions/json?origin=" + origin + "&destination=" + destination + "&key=" + os.getenv("GOOGLE_MAPS_API_KEY")
        payload = {}
        headers = {}
        response = requests.request("GET", url, headers=headers, data=payload)
        print("\n [ Generar ruta ] - Petición a Google Maps realizada")
        current_route = response.json() 
        #print("La ruta es:\n", current_route)

        # Se obtienen los steps
        steps = current_route["routes"][0]["legs"][0]["steps"]
        
        print("\n [ Generar ruta ] - Generando posiciones y velocidades a simular...")
        # Se generan las posiciones y velocidades
        positions_to_simulate, speeds_to_simulate = generate_positions_speeds(steps)

        return positions_to_simulate, speeds_to_simulate
    
    except requests.RequestException as e:
        print("\n [ Generar ruta ] - Error en la petición a Google Maps: ", e)
        return [], []
    except Exception as e:
        print("Error inesperado: ", e)
        return [], []

def generate_positions_speeds(steps):
    """ Función que se encarga de generar las posiciones y velocidades a simular """
    positions_to_simulate = []
    speeds_to_simulate = []

    for step in steps:
        # La API de Google Maps nos devuelve la distancia en metros y el tiempo en segundos
        step_speed = (step["distance"]["value"]) / (step["duration"]["value"]) # m/s
        substeps = decode_polyline(step["polyline"]["points"]) # Decodificamos la polyline. Nos devuelve una lista de tuplas con las coordenadas. Ejemplo: [(40.712, -74.227), (40.774, -74.125)]
        p_inicial = 0.0 

        # Recorremos los subpasos
        for index in range(len(substeps)-1):
            # Si es la primera posición, la guardamos como posición inicial
            if p_inicial == 0.0:
                p_inicial = {"latitude": substeps[index][0], "longitude": substeps[index][1]}

            p2 = {"latitude": substeps[index + 1][0], "longitude": substeps[index + 1][1]}

            # Se calcula la distancia en metros entre las 2 coordenadas
            points_distance = distance(p_inicial, p2) * 1000.0 # km * 1000 = m

            # Si la distancia entre dos puntos es mayor que 10 metros, se añade una nueva posición a simular
            if points_distance > 10:
                # Se calcula el tiempo que se tarda en recorrer esa distancia
                subStepDuration = points_distance / step_speed # m / (m/s) = s

                new_position = {
                    "Origin": p_inicial, 
                    "Destination": p2, 
                    "Speed": step_speed, 
                    "Time": subStepDuration}
                positions_to_simulate.append(new_position)

                new_speed = {"Speed": step_speed, 
                             "Time": subStepDuration}
            
                speeds_to_simulate.append(new_speed)
                
                p_inicial = 0.0 # Se reinicia la posición inicial

    return positions_to_simulate, speeds_to_simulate

def distance(p1, p2):
    """ Función que se encarga de calcular la distancia entre dos puntos.
    @param p1: Diccionario con las coordenadas del punto 1. Ejemplo: {"latitude": 40.712, "longitude": -74.227}
    @param p2: Diccionario con las coordenadas del punto 2. Ejemplo: {"latitude": 40.774, "longitude": -74.125}
    @return: Distancia entre los dos puntos  """

    p1Latitude = p1["latitude"]
    p1Longitude = p1["longitude"]
    p2Latitude = p2["latitude"]
    p2Longitude = p2["longitude"]

    # print("Calculando la distancia entre ({},{}) y ({},{})".format(p1["latitude"], p1["longitude"], p2["latitude"], p2["longitude"]))
    
    earth_radius = {"km": 6371.0087714, "mile": 3959}
    
    result = earth_radius["km"] * acos(
        cos((radians(p1Latitude))) * cos(radians(p2Latitude)) * cos(radians(p2Longitude) - radians(p1Longitude)) + 
        sin(radians(p1Latitude)) * sin(radians(p2Latitude))
    )
    
    # print ("La distancia calculada es:{}".format(result))
    
    return result # En kilómetros

def decode_polyline(polyline_str):
    '''Pass a Google Maps encoded polyLine string; returns list of lat/lon pairs'''

    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'latitude': 0, 'longitude': 0}

    # Coordinates have variable length when encoded, so just keep
    # track of whether we've hit the end of the string. In each
    # while loop iteration, a single coordinate is decoded.
    while index < len(polyline_str):
        # Gather lat/lon changes, store them in a dictionary to apply them later
        for unit in ['latitude', 'longitude']:
            shift, result = 0, 0

            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if not byte >= 0x20:
                    break

            if (result & 1):
                changes[unit] = ~(result >> 1)
            else:
                changes[unit] = (result >> 1)

        lat += changes['latitude']
        lng += changes['longitude']

        coordinates.append((lat / 100000.0, lng / 100000.0))

    return coordinates

def send_positions_to_gps_simulator(positions_to_simulate):
    """ Función que se encarga de enviar las posiciones al simulador de GNSS """
    GPS_SIMULATOR_HOST = os.getenv("GPS_SIMULATOR_HOST")
    GPS_SIMULATOR_PORT = int(os.getenv("GPS_SIMULATOR_PORT", 5002))

    while True:
        try:
            with socket.create_connection((GPS_SIMULATOR_HOST, GPS_SIMULATOR_PORT)) as s:
                print("\n [ Enviar GNSS ] - Conectado al GNSS. Mandando posiciones...\n")
                print("\n [ Enviar GNSS ] - Posiciones a simular: ", positions_to_simulate)
                for position in positions_to_simulate:
                    s.sendall(json.dumps(position).encode("utf-8"))
                    data = s.recv(1024)
                print("Posiciones enviadas al GNSS")
                break  # Salir del bucle si todo fue bien
        except socket.error as e:
            print(f"Error en la conexión con el GPS: {e}. Reintentando en 1 segundo...")
            time.sleep(1)

def send_speeds_to_odometer_simulator(speeds_to_simulate):
    """ Función que se encarga de enviar las velocidades al simulador de odómetro """
    ODOMETER_SIMULATOR_HOST = os.getenv("ODOMETER_SIMULATOR_HOST")
    ODOMETER_SIMULATOR_PORT = int(os.getenv("ODOMETER_SIMULATOR_PORT", 5003))

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ODOMETER_SIMULATOR_HOST, ODOMETER_SIMULATOR_PORT))
                print("\n [ Enviar Odometro ] - Conectado al Odometro. Mandando velocidades...\n")
                print("\n [ Enviar Odometro ] - Velocidades a simular: ", speeds_to_simulate)
                for speed in speeds_to_simulate:
                    s.sendall(bytes(json.dumps(speed), "utf-8"))
                    data = s.recv(1024)
                print("Posiciones enviadas al Odometro")
                break  # Salir del bucle si todo fue bien
        except socket.error as e:
            print(f"Error en la conexión con el Odómetro: {e}")
            time.sleep(1)

if __name__ == '__main__':
    print("Vamos a generar una ruta")
    try:
        my_route = {"Origin": "Ayuntamiento de Leganes", "Destination": "Ayuntamiento de Getafe"}
        print("\nRuta a simular: ", my_route)
        positions_to_simulate, speeds_to_simulate = generate_route_simulations(my_route["Origin"], my_route["Destination"])
        print("\nPosiciones y velocidades generadas")

        # Thread que se encarga de enviar las posiciones al simulador del GNSS
        t1 = threading.Thread(target=send_positions_to_gps_simulator, daemon=True, args=(positions_to_simulate,))
        # Thread que se encarga de enviar las velocidades al simulador del odómetro
        t2 = threading.Thread(target=send_speeds_to_odometer_simulator, daemon=True, args=(speeds_to_simulate,))

        t1.start()
        t2.start()
        
        t1.join() 
        t2.join()

        while True:
            time.sleep(3600)

    except Exception as e:
        print(e)