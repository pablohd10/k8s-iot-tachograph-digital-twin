#!/bin/bash
set -e

MINIKUBE_PROFILE="siot-cluster"  

# Cambiar contexto de kubectl a minikube
kubectl config use-context $MINIKUBE_PROFILE

# Configura el entorno Docker del clúster correspondiente
eval $(minikube -p $MINIKUBE_PROFILE docker-env)

echo -e "\n🚀 Subiendo imagen de Webapp Backend...\n"
pushd Microservices/TelemetryMicroservice > /dev/null
docker build -t seluc3m-siot-webapp-backend:c1 .
popd > /dev/null

echo -e "\n📦 Aplicando ConfigMaps...\n"
kubectl apply -f WebappBackend/webapp-backend-configmap.yml

echo -e "\n🌐 Aplicando servicio Webapp Backend...\n"
kubectl apply -f WebappBackend/webapp-backend-service-local.yml

echo -e "\n📤 Desplegando deployment Webapp Backend...\n"
kubectl apply -f WebappBackend/webapp-backend-deployment-local.yml
