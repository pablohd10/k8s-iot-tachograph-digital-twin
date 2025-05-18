from ruamel.yaml import YAML 
from pathlib import Path 
from collections import defaultdict 
from ruamel.yaml.comments import CommentedMap as OrderedDict 
import base64 
from Crypto.PublicKey import RSA

def generate_rsa_keys(size=2048):
    """ Función que se encarga de generar las claves RSA """
    """
    Genera un par de claves RSA (privada y pública).
    
    :param size: Tamaño de la clave en bits (por defecto 2048).
    :return: Tupla (clave_privada_pem, clave_publica_pem)
    """

    clave = RSA.generate(size) 
    clave_privada = clave.export_key().decode()
    clave_publica = clave.publickey().export_key().decode() 
    
    return clave_privada, clave_publica # Formato PEM

# Tacografos a generar --> obtener desde configmap?????
tachographs_to_generate = ["tachograph-simulator-0",
                           "tachograph-simulator-1",
                           "tachograph-simulator-2",
                           "tachograph-simulator-3",
                           "tachograph-simulator-4"]

# Estructura del YAML
secret = OrderedDict({
    'apiVersion': 'v1',
    'kind': 'Secret',
    'metadata': OrderedDict({
        'name': 'tachograph-keys'
    }),
    'type': 'Opaque',
    'data': OrderedDict({})
})

for tachograph in tachographs_to_generate:
    private_key, public_key = generate_rsa_keys()

    encoded_private = base64.b64encode(private_key.encode('utf-8')).decode('utf-8')
    encoded_public = base64.b64encode(public_key.encode('utf-8')).decode('utf-8')

    secret['data'][f"{tachograph}-private-key"] = encoded_private
    secret['data'][f"{tachograph}-public-key"] = encoded_public


# Escribir el YAML
yaml = YAML()
yaml.indent(mapping=4, sequence=4, offset=2)

with open("tachograph-keys.yml", "w") as outfile:
    yaml.dump(secret, outfile)

print("✅ Se ha generado tachograph-keys.yml con las claves de los tacografos.")
    
