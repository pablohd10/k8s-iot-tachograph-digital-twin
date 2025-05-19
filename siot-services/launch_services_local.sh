#!/bin/bash

set -e  # Stop script if any command fails

MINIKUBE_PROFILE="siot-cluster"

echo "=============================="
echo "  🚀 Lanzando SIoT Services (LOCAL - Minikube)"
echo "=============================="

if [ "$(basename "$PWD")" != "siot-services" ]; then
  echo "❌ Este script debe ejecutarse desde el directorio 'siot-services'."
  exit 1
fi

echo "🔍 Comprobando si Docker está disponible..."
if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker no está corriendo. Por favor, abre Docker Desktop y vuelve a intentarlo."
  exit 1
fi

echo "✅ Docker está corriendo. Usaremos 'docker' como driver para Minikube."

echo "🚀 Iniciando Minikube con perfil '$MINIKUBE_PROFILE'..."
minikube start -p $MINIKUBE_PROFILE --driver=docker

# Configura el entorno Docker del cluster específico
eval $(minikube -p $MINIKUBE_PROFILE docker-env)
kubectl config use-context $MINIKUBE_PROFILE

echo -e "\n👉 Lanzando base de datos MariaDB..."
./DBService/launch_mariadb_local.sh

echo -e "\n👉 Lanzando Events Microservice..."
./Microservices/EventsMicroservice/launch_events_microservice_local.sh

echo -e "\n👉 Lanzando Telemetry Microservice..."
./Microservices/TelemetryMicroservice/launch_telemetry_microservice_local.sh

echo -e "\n👉 Lanzando Message Router..."
# ./MessageRouter/launch_message_router_local.sh

echo -e "\n👉 Lanzando Webapp Backend..."
./WebappBackend/launch_webapp_backend_local.sh

echo -e "\n✅ Todos los componentes han sido desplegados en Minikube correctamente.\n"
kubectl get pods
