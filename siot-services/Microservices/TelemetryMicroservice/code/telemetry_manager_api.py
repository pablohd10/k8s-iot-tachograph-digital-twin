from flask import Flask, request, jsonify
from flask_cors import CORS
from telemetry_db_manager import *
import requests
import os

app = Flask(__name__)
CORS(app)

@app.route('/telemetry', methods=['POST'])
def register_telemetry():
    """
    This function registers a new telemetry in the tachograph database.
    :parameter Tachograph_id:
    :parameter Position:
    :parameter GPSSpeed: 
    :parameter Speed:
    :parameter Driver:
    :parameter time_stamp:
    Example:
    { "Tachograph_id":"1234BBC", 
      "Position": {"Latitude":40.28908, "Longitude":-4.01197}, 
      "GPSSpeed":0.0, 
      "Speed":0.0, 
      "Driver":"Driver 1", 
      "Timestamp":"2023-11-27 17:48:52" 
    } 
    :return: A JSON object with the result of the operation.
    """
    try:
        params = request.get_json()

        # Verificar que params sea un diccionario
        if not isinstance(params, dict):
            return {"result": "Invalid input format, expected JSON object"}, 400

        # Validar campos obligatorios
        required_fields = ["Tachograph_id", "Position", "GPSSpeed", "Speed", "Driver", "Timestamp"]
        for field in required_fields:
            if field not in params:
                return {"result": f"Missing required field: {field}"}, 400

        # Validar el campo position
        if not isinstance(params["Position"], dict):
            return {"result": "Invalid Position format"}, 400
        if "latitude" not in params["Position"] or "longitude" not in params["Position"]:
            return {"result": "Missing latitude or longitude in position"}, 400

        # Procesar la telemetría (guardarlo en la base de datos)
        if register_telemetry_db(params):
            print("Telemetry registered")
            return {"result": "Telemetry registered"}, 201
        else:
            return {"result": "Error registering telemetry"}, 500

    except Exception as e:
        # Captura errores inesperados y devuelve error 500
        return {"result": f"Exception occurred: {str(e)}"}, 500
    

@app.route('/telemetry', methods=['GET'])
def get_telemetry():
    """
    Endpoint GET /telemetry

    Este método recibe como parámetros de entrada un objeto JSON con la información
    del tacógrafo y el intervalo temporal a consultar. Devuelve una lista de telemetrías
    registradas para el tacógrafo indicado dentro del intervalo especificado.

    Entrada (en el body de la petición GET como JSON):
        {
            "Tachograph_id": "<Tachograph_id>",
            "init_interval": "YYYY-MM-DD HH:MM:SS",
            "end_interval": "YYYY-MM-DD HH:MM:SS"
        }

    Validaciones:
        - El JSON debe tener los campos 'Tachograph_id', 'init_interval' y 'end_interval'.
        - Las fechas deben tener el formato "YYYY-MM-DD HH:MM:SS".
        - init_interval debe ser anterior a end_interval.

    Salida:
        - En caso de éxito (200): 
            {
                "telemetries": [ ... ]  # Lista con las telemetrías encontradas
            }
        - En caso de error (400/500): 
            {
                "result": "<mensaje de error>"
            }

    Nota:
        El acceso a los datos se realiza a través del método get_telemetry_db()
        definido en el módulo telemetry_db_manager.py.
    """
    try:
        # Obtener los parámetros desde un JSON en el body de la petición GET
        params = request.get_json()

        # Verificar que params sea un diccionario válido
        if not isinstance(params, dict):
            return {"result": "Invalid input format, expected JSON object"}, 400
        
        # Validar campos requeridos
        required_fields = ["Tachograph_id", "init_interval", "end_interval"]
        for field in required_fields:
            if field not in params:
                return {"result": f"Missing required field: {field}"}, 400
            
        # Extraer valores
        tachograph_id = params["Tachograph_id"]
        init_interval = params["init_interval"]
        end_interval = params["end_interval"]

        # Validar formato de fechas
        try:
            init_dt = datetime.strptime(init_interval, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(end_interval, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return {"result": "Invalid date format. Use YYYY-MM-DD HH:MM:SS"}, 400

        # Validar que el intervalo tenga sentido
        if init_dt > end_dt:
            return {"result": "init_interval must be earlier than end_interval"}, 400
        
        results = get_telemetry_db(tachograph_id, init_interval, end_interval)

        return {"telemetries": results}, 200
    
    except Exception as e:
        return {"result": f"Exception occurred: {str(e)}"}, 500

@app.route('/telemetry/positions/', methods=['GET'])
def get_last_positions():
    """
    Endpoint GET /telemetry/positions/

    Este método no recibe parámetros de entrada. Devuelve una lista en formato JSON
    que incluye, para cada uno de los vehículos activos, el id, latitud y longitud 
    de su última posición conocida.

    Salida:
        - En caso de éxito (201):
            [
                {
                    "Tachograph_id": "<Tachograph_id>",
                    "latitude": <float>,
                    "longitude": <float>
                },
                ...
            ]
        - En caso de error (500):
            {
                "Error Message": "<mensaje de error>"
            }

    Nota:
        Se utiliza la función get_vehicles_last_position() para consultar los datos.
    """
    try:
        error_message, result = get_vehicles_last_position()

        if error_message == "":
            return jsonify(result), 201
        else:
            return {"Error Message": error_message}, 500

    except Exception as e:
        return {"Error Message": f"Exception occurred: {str(e)}"}, 500
    

HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))
app.run(HOST, PORT)