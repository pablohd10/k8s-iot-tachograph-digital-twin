from flask import Flask, request
from flask_cors import CORS
from events_db_manager import *
import requests
import os

app = Flask(__name__)
CORS(app)

@app.route('/events/', methods=['POST'])
def register_event():
    """
    Endpoint POST /event/

    Recibe datos de eventos enviados por el message router.
    Formato de entrada esperado:
    {
        "Tachograph_id":"tachograph_control_unit-4",
        "Position": {
            "latitude": 40.28908,
            "longitude": -4.01197
            },
        "Warning": "Warning Message",
        "Timestamp": "2023-11-27 17:48:52"
    }
    """
    try:
        data = request.get_json()

         # Validación de campos obligatorios
        required_keys = ["Tachograph_id", "Position", "Warning", "Timestamp"]
        for key in required_keys:
            if key not in data:
                return {"result": f"Missing field: {key}"}, 400
        
        if data["Position"] == "None":
            data["Position"] = {"latitude": None, "longitude": None}
        if "latitude" not in data["Position"] or "longitude" not in data["Position"]:
            return {"result": "Missing latitude or longitude in position"}, 400

        # Validación de tipos
        if not isinstance(data["Tachograph_id"], str):
            return {"result": "Tachograph_id must be a string"}, 400
        if not isinstance(data["Warning"], str):
            return {"result": "Warning must be a string"}, 400
        if data["Position"]["latitude"] is not None and not isinstance(data["Position"]["latitude"], (int, float)):
            return {"result": "latitude must be a number or null"}, 400
        if data["Position"]["longitude"] is not None and not isinstance(data["Position"]["longitude"], (int, float)):
            return {"result": "longitude must be a number or null"}, 400

        # Validación del timestamp
        try:
            datetime.strptime(data["Timestamp"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return {"result": "Timestamp must be in format 'YYYY-MM-DD HH:MM:SS'"}, 400

        error_message = register_event_db(data)
        
        if error_message == "":
            return {"result": "Event registered"}, 201
        else:
            return {"result": f"Error registering an event: {error_message}"}, 500

    except Exception as e:
        return {"result": f"Exception occurred: {str(e)}"}, 500

@app.route('/events', methods=['GET'])
def get_events():
    """
    Endpoint GET /events

    Este método recibe como parámetros de entrada un objeto JSON con el ID
    del tacógrafo y el intervalo temporal a consultar. Devuelve una lista de eventos
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
                "events": [ ... ]  # Lista con los eventos encontrados
            }
        - En caso de error (400/500): 
            {
                "result": "<mensaje de error>"
            }

    Nota:
        El acceso a los datos se realiza a través del método get_events_db()
        definido en el módulo events_db_manager.py.
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
        
        results = get_events_db(tachograph_id, init_interval, end_interval)

        return {"events": results}, 200
    
    except Exception as e:
        return {"result": f"Exception occurred: {str(e)}"}, 500


HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))
app.run(HOST, PORT)