#!/bin/bash
set -e

MINIKUBE_PROFILE="siot-cluster"  

# Cambiar contexto de kubectl a minikube
kubectl config use-context $MINIKUBE_PROFILE

# Configura el entorno Docker del clúster correspondiente
eval $(minikube -p $MINIKUBE_PROFILE docker-env)

echo -e "\n🚀 Subiendo imagen de Events Microservice...\n"
pushd Microservices/EventsMicroservice > /dev/null
docker build -t seluc3m-siot-events-microservice:c1 .
popd > /dev/null

echo -e "\n📦 Aplicando ConfigMaps de EventsMicroservice...\n"
kubectl apply -f Microservices/microservices-common-configmap.yml
kubectl apply -f Microservices/EventsMicroservice/events-microservice-configmap.yml

echo -e "\n🔐 Aplicando secretos comunes de EventsMicroservice...\n"
kubectl apply -f Microservices/microservices-common-secrets.yml

echo -e "\n🌐 Aplicando servicio Events Microservice...\n"
kubectl apply -f Microservices/EventsMicroservice/events-microservice-service-local.yml

echo -e "\n📤 Desplegando deployment Events Microservice...\n"
kubectl apply -f Microservices/EventsMicroservice/events-microservice-deployment-local.yml
