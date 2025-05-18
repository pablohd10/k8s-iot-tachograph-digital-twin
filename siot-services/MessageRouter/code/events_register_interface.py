import requests 
import os 

def register_event(data): 
    host = os.getenv('EVENTS_MICROSERVICE_ADDRESS')
    port = os.getenv('EVENTS_MICROSERVICE_PORT')
    r = requests.post('http://' + host + ':' + port + '/events', json=data) 
    print("Respuesta de la API /events: ", r.json(), r.status_code)
    return r.json()
