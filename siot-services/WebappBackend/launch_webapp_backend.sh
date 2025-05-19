#!/bin/bash
set -e

# Conectarse al cluster
echo "Conectándose al cluster Kubernetes services-cluster..."
gcloud container clusters get-credentials services-cluster --region=us-central1

echo -e "\n🚀 Subiendo imagen de Webapp Backend...\n"
pushd WebappBackend > /dev/null
gcloud builds submit --region=us-central1 --tag us-central1-docker.pkg.dev/$PROJECT_ID/siot-repo/seluc3m-siot-webapp-backend:c1
popd > /dev/null

echo -e "\n📦 Aplicando ConfigMaps Webapp Backend...\n"
kubectl apply -f WebappBackend/webapp-backend-configmap.yml

echo -e "\n🌐 Aplicando servicio Webapp Backend...\n"
kubectl apply -f WebappBackend/webapp-backend-service.yml

echo -e "\n📤 Desplegando deployment Webapp Backend...\n"
kubectl apply -f WebappBackend/webapp-backend-deployment.yml
