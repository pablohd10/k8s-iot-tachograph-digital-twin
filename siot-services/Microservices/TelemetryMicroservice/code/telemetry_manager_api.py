from flask import Flask, request, jsonify
from flask_cors import CORS
from telemetry_db_manager import *
import requests
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

@app.route('/telemetry', methods=['POST'])
def register_telemetry():
    """
    Endpoint POST /telemetry

    Recibe datos de telemetría enviados por el message router.
    Formato de entrada esperado:
    {
        "Tachograph_id": "1234BBC",
        "Position": {
            "latitude": 40.28908,
            "longitude": -4.01197
        },
        "GPSSpeed": 0.0,
        "Speed": 0.0,
        "Driver": "Driver 1",
        "Timestamp": "2023-11-27 17:48:52"
    }
    """
    try:
        data = request.get_json()

        # Validación de campos obligatorios
        required_keys = ["Tachograph_id", "Position", "GPSSpeed", "Speed", "Driver", "Timestamp"]
        for key in required_keys:
            if key not in data:
                return {"result": f"Missing field: {key}"}, 400

        # Validación de posición
        if data["Position"] == "None":
            data["Position"] = {"latitude": None, "longitude": None}
        if "latitude" not in data["Position"] or "longitude" not in data["Position"]:
            return {"result": "Missing latitude or longitude in position"}, 400

        # Validación de tipos
        if not isinstance(data["Tachograph_id"], str):
            return {"result": "Tachograph_id must be a string"}, 400
        if not isinstance(data["Driver"], str):
            return {"result": "Driver must be a string"}, 400
        if not isinstance(data["GPSSpeed"], (int, float)):
            return {"result": "GPSSpeed must be a number"}, 400
        if not isinstance(data["Speed"], (int, float)):
            return {"result": "Speed must be a number"}, 400
        if data["Position"]["latitude"] is not None and not isinstance(data["Position"]["latitude"], (int, float)):
            return {"result": "latitude must be a number or null"}, 400
        if data["Position"]["longitude"] is not None and not isinstance(data["Position"]["longitude"], (int, float)):
            return {"result": "longitude must be a number or null"}, 400

        try:
            # Intenta con microsegundos, si no, sin ellos
            try:
                datetime.strptime(data["Timestamp"], "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                datetime.strptime(data["Timestamp"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return {"result": "Timestamp must be in format 'YYYY-MM-DD HH:MM:SS[.ffffff]'"}, 400

        print("Timestamp: ", data["Timestamp"])

        if register_telemetry_db(data):
            return {"result": "Telemetry registered"}, 201
        else:
            return {"result": "Error registering telemetry"}, 500

    except Exception as e:
        return {"result": f"Exception occurred: {str(e)}"}, 500


@app.route('/telemetry', methods=['GET'])
def get_telemetry():
    """
    GET /telemetry

    Input JSON format:
    {
        "Tachograph_id": "<Tachograph_id>",
        "init_interval": "YYYY-MM-DD HH:MM:SS",
        "end_interval": "YYYY-MM-DD HH:MM:SS"
    }

    Dates are converted to UNIX timestamps in milliseconds internally.

    Returns:
        - 200 with telemetry list
        - 400/500 with error message
    """
    try:
        params = request.get_json()
        if not isinstance(params, dict):
            return {"result": "Invalid input format, expected JSON object"}, 400
        
        required_fields = ["Tachograph_id", "init_interval", "end_interval"]
        for field in required_fields:
            if field not in params:
                return {"result": f"Missing required field: {field}"}, 400

        # Extraer valores
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

        results = get_telemetry_db(params["Tachograph_id"], init_interval, end_interval)
        
        return results, 200

    except Exception as e:
        return {"result": f"Exception occurred: {str(e)}"}, 500

@app.route('/telemetry/positions', methods=['GET'])
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
        print("Result:", result)
        if error_message == "":
            return jsonify(result), 201
        else:
            return {"Error Message": error_message}, 500

    except Exception as e:
        return {"Error Message": f"Exception occurred: {str(e)}"}, 500
    

HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))
app.run(HOST, PORT)