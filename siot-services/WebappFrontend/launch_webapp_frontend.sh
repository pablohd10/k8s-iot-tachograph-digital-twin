#!/bin/bash
set -e

# Conectarse al cluster
echo "Conectándose al cluster Kubernetes services-cluster..."
gcloud container clusters get-credentials services-cluster --region=us-central1

echo -e "\n🚀 Subiendo imagen de Webapp Frontend...\n"
pushd WebappFrontend > /dev/null
gcloud builds submit --region=us-central1 --tag us-central1-docker.pkg.dev/$PROJECT_ID/siot-repo/seluc3m-siot-webapp-frontend:c1
popd > /dev/null

echo -e "\n📦 Aplicando ConfigMaps Webapp Frontend...\n"
kubectl apply -f WebappFrontend/webapp-frontend-configmap.yml

echo -e "\n🌐 Aplicando servicio Webapp Frontend...\n"
kubectl apply -f WebappFrontend/webapp-frontend-service.yml

echo -e "\n📤 Desplegando deployment Webapp Frontend...\n"
kubectl apply -f WebappFronten/webapp-frontend-deployment.yml
