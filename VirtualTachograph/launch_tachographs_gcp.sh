#!/bin/bash

# Variables de entorno
export PROJECT_ID="uc3m-inf-2025-18654-g12" # nombre del proyecto
export SCRIPT_KEY_GENERATOR="generate_tachographs_key_pair.py" # nombre del script generador de las claves de los tacografos

# Check if current directory is 'VirtualTachograph'
if [ "$(basename "$PWD")" != "VirtualTachograph" ]; then
  echo "This script must be run from within the 'VirtualTachograph' directory."
  exit 1
fi

# Establecer el proyecto correspondiente
gcloud config set project $PROJECT_ID
echo "Proyecto actual: $(gcloud config get-value project)"

# Establecer nuestra cuenta como activa
gcloud config set account 100451225@alumnos.uc3m.es

# Crear repositorio de contenedores Docker en Google Artifact Registry en GCP
# Comprobar si el repositorio ya existe
REPO_EXISTS=$(gcloud artifacts repositories list --project=$PROJECT_ID --location=europe-west1 --filter="name:siot-repo" --format="value(name)")
if [ -z "$REPO_EXISTS" ]; then
  # Si no existe, crear el repositorio
  echo "\nRepositorio de artefactos no encontrado, creando...\n"
  gcloud artifacts repositories create siot-repo \
    --project=$PROJECT_ID \
    --repository-format=docker \
    --location=europe-west1 \
    --description="Docker images repository"
  echo "\nRepositorio de artefactos creado\n"
else
  echo "\nEl repositorio 'siot-repo' ya existe.\n"
fi

echo "\nSubiendo imagenes de contenedores.\n"
# Subir imagen del ControlUnit al repositorio de contenedores 
cd ControlUnit 
gcloud builds submit --region=europe-west1 --tag europe-west1-docker.pkg.dev/$PROJECT_ID/siot-repo/seluc3m-siot-control-unit:c1 
cd .. 
# Subir imagen del CardReader al repositorio de contenedores 
cd CardReader 
gcloud builds submit --region=europe-west1 --tag europe-west1-docker.pkg.dev/$PROJECT_ID/siot-repo/seluc3m-siot-card-reader:c1 
cd ..  
# Subir imagen del Odometer al repositorio de contenedores 
cd Odometer 
gcloud builds submit --region=europe-west1 --tag europe-west1-docker.pkg.dev/$PROJECT_ID/siot-repo/seluc3m-siot-odometer:c1 
cd ..  
# Subir imagen del PositioningSystem al repositorio de contenedores 
cd PositioningSystem 
gcloud builds submit --region=europe-west1 --tag europe-west1-docker.pkg.dev/$PROJECT_ID/siot-repo/seluc3m-siot-gnss:c1 
cd ..  
# Subir imagen del RoutesGenerator al repositorio de contenedores 
cd RoutesGenerator 
gcloud builds submit --region=europe-west1 --tag europe-west1-docker.pkg.dev/$PROJECT_ID/siot-repo/seluc3m-siot-routes-generator:c1 
cd .. 

# Generar claves públicas y privadas de los tacografos
cd kubernetes 
pip install "ruamel.yaml<0.18.0"
pip install pycryptodome --user
python3 ./$SCRIPT_KEY_GENERATOR

# Crear el cluster Kubernetes
echo "Creando el cluster Kubernetes..."
gcloud container clusters create-auto tachographs-cluster --region=europe-west1

# Conectarse al cluster
echo "Conectándose al cluster Kubernetes..."
gcloud container clusters get-credentials tachographs-cluster --region=europe-west1

# Crear configmaps
echo "Aplicando configmaps..."
kubectl apply -f ./configmaps/tachograph-configuration-configmap.yml
kubectl apply -f ./configmaps/odometer-configmap.yml
kubectl apply -f ./configmaps/routesgenerator-configmap.yml
kubectl apply -f ./configmaps/controlunit-configmap.yml
kubectl apply -f ./configmaps/cardreader-configmap.yml
kubectl apply -f ./configmaps/gnss-configmap.yml

# Crear secretos
echo "Aplicando secretos..."
kubectl apply -f ./tachograph-keys.yml
kubectl apply -f ./tachograph-secrets.yml
kubectl create secret generic tachograph-tokens --from-file=./tokens.json

# Crear servicios
echo "\nAplicando servicios...\n"
kubectl apply -f ./tachograph-service.yml

# Desplegar los pods
echo "Desplegando los pods del StatefulSet..."
kubectl apply -f ./tachograph-statefulset.yml

echo -e "\n🔍 Mostrando contextos de Kubernetes disponibles:"
kubectl config get-contexts

echo -e "\n📍 Contexto de Kubernetes actualmente en uso:"
kubectl config current-context