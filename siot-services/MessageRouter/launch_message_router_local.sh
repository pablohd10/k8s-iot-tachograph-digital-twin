#!/bin/bash
set -e

MINIKUBE_PROFILE="siot-cluster"

# Cambiar contexto de kubectl a minikube
kubectl config use-context $MINIKUBE_PROFILE

# Configura el entorno Docker del clúster correspondiente
eval $(minikube -p $MINIKUBE_PROFILE docker-env)

echo -e "\n🚀 Subiendo imagen de contenedor Message Router...\n"
pushd MessageRouter > /dev/null
docker build -t seluc3m-siot-message-router:c1 .
popd > /dev/null

echo -e "\n📦 Aplicando ConfigMap Message Router...\n"
kubectl apply -f MessageRouter/message-router-configmap.yml

echo -e "\n🔐 Aplicando secretos Message Router...\n"
kubectl apply -f MessageRouter/message-router-secrets.yml

echo -e "\n🌐 Aplicando servicio Message Router...\n"
kubectl apply -f MessageRouter/message-router-service.yml

echo -e "\n📤 Desplegando deployment Message Router...\n"
kubectl apply -f MessageRouter/message-router-deployment-local.yml
