from flask import Flask, request
from flask_cors import CORS
import os
import requests


app = Flask(__name__)
CORS(app)

@app.route('/tachographs/active/', methods=['GET'])
def get_active_tachographs():
    """
    Obtiene la última posición de los tacógrafos activos desde el microservicio de telemetría.
    """
    telemetry_host = os.getenv('TELEMETRY_MICROSERVICE_ADDRESS')
    telemetry_port = os.getenv('TELEMETRY_MICROSERVICE_PORT')
    try:
        result = requests.get(f'http://{telemetry_host}:{telemetry_port}/telemetry/positions/')
        if result.status_code == 201:
            return result.json(), 201
        else:
            return {"result": "Error: Tachographs information is not available"}, 500
    except Exception as e:
        return {"result": f"Exception occurred: {str(e)}"}, 500

@app.route('/tachographs/telemetry/', methods=['GET'])
def get_tachograph_telemetry():
    """
    Reenvía la petición al microservicio de telemetría para obtener
    la información de las telemetrías del último minuto.
    Se espera que los parámetros vengan en la query string.
    """
    try:
        tachograph_id = request.args.get('tachograph_id')
        if not tachograph_id:
            return {"result": "Missing tachograph_id parameter"}, 400

        # Calcular el intervalo del último minuto
        from datetime import datetime, timedelta
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=1)

        params = {
            "Tachograph_id": tachograph_id,
            "init_interval": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_interval": end_time.strftime("%Y-%m-%d %H:%M:%S")
        }

        host = os.getenv('TELEMETRY_MICROSERVICE_ADDRESS')
        port = os.getenv('TELEMETRY_MICROSERVICE_PORT')
        url = f'http://{host}:{port}/telemetry/'

        result = requests.get(url, json=params)

        return result.json(), result.status_code

    except Exception as e:
        return {"result": f"Exception occurred: {str(e)}"}, 500
    

@app.route('/tachographs/events/', methods=['GET'])
def get_tachograph_events():
    """
    Reenvía la petición al microservicio de eventos para obtener
    la información de los eventos del último minuto.
    Se espera que los parámetros vengan en la query string.
    """
    try:
        tachograph_id = request.args.get('tachograph_id')
        if not tachograph_id:
            return {"result": "Missing tachograph_id parameter"}, 400

        # Calcular el intervalo del último minuto
        from datetime import datetime, timedelta
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=1)

        params = {
            "Tachograph_id": tachograph_id,
            "init_interval": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_interval": end_time.strftime("%Y-%m-%d %H:%M:%S")
        }

        host = os.getenv('EVENTS_MICROSERVICE_ADDRESS')
        port = os.getenv('EVENTS_MICROSERVICE_PORT')
        url = f'http://{host}:{port}/events'

        result = requests.get(url, json=params)

        return result.json(), result.status_code

    except Exception as e:
        return {"result": f"Exception occurred: {str(e)}"}, 500
    

HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))
app.run(HOST, PORT)