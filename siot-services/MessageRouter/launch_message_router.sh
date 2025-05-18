#!/bin/bash
set -e

# Conectarse al cluster
echo "Conectándose al cluster Kubernetes services-cluster..."
gcloud container clusters get-credentials services-cluster --region=us-central1

echo -e "\n🚀 Subiendo imagen de contenedor Message Router...\n"
pushd MessageRouter > /dev/null
gcloud builds submit --region=us-central1 --tag us-central1-docker.pkg.dev/$PROJECT_ID/siot-repo/seluc3m-siot-message-router:c1 
popd > /dev/null

echo -e "\n📦 Aplicando ConfigMap Message Router...\n"
kubectl apply -f MessageRouter/message-router-configmap.yml

echo -e "\n🔐 Aplicando secretos Message Router...\n"
kubectl apply -f MessageRouter/message-router-secrets.yml

echo -e "\n🌐 Aplicando servicio Message Router...\n"
# kubectl apply -f MessageRouter/message-router-service.yml

echo -e "\n📤 Desplegando deployment Message Router...\n"
kubectl apply -f MessageRouter/message-router-deployment.yml
