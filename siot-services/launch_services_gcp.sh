#!/bin/bash

set -e  # Hace que el script se detenga si algún comando falla

echo "=============================="
echo "  🚀 Lanzando SIoT Services"
echo "=============================="

# Variables de entorno
export PROJECT_ID="uc3m-inf-2025-18654-g12" # nombre del proyecto

# Check if current directory is 'siot-services'
if [ "$(basename "$PWD")" != "siot-services" ]; then
  echo "This script must be run from within the 'siot-services' directory."
  exit 1
fi

# Establecer el proyecto correspondiente
gcloud config set project $PROJECT_ID
echo "Proyecto actual: $(gcloud config get-value project)"

# Establecer nuestra cuenta como activa
gcloud config set account 100451225@alumnos.uc3m.es

# Crear repositorio de contenedores Docker en Google Artifact Registry en GCP
# Comprobar si el repositorio ya existe
REPO_EXISTS=$(gcloud artifacts repositories list --project=$PROJECT_ID --location=us-central1 --filter="name:siot-repo" --format="value(name)")
if [ -z "$REPO_EXISTS" ]; then
  # Si no existe, crear el repositorio
  echo "\nRepositorio de artefactos no encontrado, creando...\n"
  gcloud artifacts repositories create siot-repo \
    --project=$PROJECT_ID \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker images repository"
  echo "\nRepositorio de artefactos creado\n"
else
  echo "\nEl repositorio 'siot-repo' ya existe.\n"
fi

# Crear el cluster Kubernetes
echo "Creando el cluster Kubernetes services-cluster..."
gcloud container clusters create-auto services-cluster --region=us-central1

# Conectarse al cluster
echo "Conectándose al cluster Kubernetes services-cluster..."
gcloud container clusters get-credentials services-cluster --region=us-central1

# Asegurar permisos de ejecución para los scripts
chmod +x ./DBService/launch_mariadb.sh
chmod +x ./Microservices/EventsMicroservice/launch_events_microservice.sh
chmod +x ./Microservices/TelemetryMicroservice/launch_telemetry_microservice.sh
chmod +x ./MessageRouter/launch_message_router.sh
chmod +x ./WebappBackend/launch_webapp_backend.sh

# Lanzar los servicios
echo -e "\n👉 Lanzando base de datos MariaDB..."
./DBService/launch_mariadb.sh

echo -e "\n👉 Lanzando Events Microservice..."
./Microservices/EventsMicroservice/launch_events_microservice.sh

echo -e "\n👉 Lanzando Telemetry Microservice..."
./Microservices/TelemetryMicroservice/launch_telemetry_microservice.sh

echo -e "\n👉 Lanzando Message Router..."
./MessageRouter/launch_message_router.sh

echo -e "\n👉 Lanzando Webapp Backend..."
./WebappBackend/launch_webapp_backend.sh

echo -e "\n👉 Lanzando Webapp Frontend..."
./WebappFrontend/launch_webapp_frontend.sh

echo -e "\n✅ Todos los componentes han sido desplegados correctamente."

echo -e "\n🔍 Mostrando contextos de Kubernetes disponibles:"
kubectl config get-contexts

echo -e "\n📍 Contexto de Kubernetes actualmente en uso:"
kubectl config current-context