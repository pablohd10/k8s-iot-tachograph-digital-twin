#!/bin/bash
set -e

MINIKUBE_PROFILE="siot-cluster"  

# Cambiar contexto de kubectl a minikube
kubectl config use-context $MINIKUBE_PROFILE

# Configura el entorno Docker del clúster correspondiente
eval $(minikube -p $MINIKUBE_PROFILE docker-env)

echo -e "\n🚀 Subiendo imagen de Telemetry Microservice...\n"
pushd Microservices/TelemetryMicroservice > /dev/null
docker build -t seluc3m-siot-telemetry-microservice:c1 .
popd > /dev/null

echo -e "\n📦 Aplicando ConfigMaps...\n"
kubectl apply -f Microservices/microservices-common-configmap.yml
kubectl apply -f Microservices/TelemetryMicroservice/telemetry-microservice-configmap.yml

echo -e "\n🔐 Aplicando secretos comunes...\n"
kubectl apply -f Microservices/microservices-common-secrets.yml

echo -e "\n🌐 Aplicando servicio Telemetry Microservice...\n"
kubectl apply -f Microservices/TelemetryMicroservice/telemetry-microservice-service-local.yml

echo -e "\n📤 Desplegando deployment Telemetry Microservice...\n"
kubectl apply -f Microservices/TelemetryMicroservice/telemetry-microservice-deployment-local.yml
