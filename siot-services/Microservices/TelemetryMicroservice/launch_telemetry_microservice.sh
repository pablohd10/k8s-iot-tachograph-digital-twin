#!/bin/bash
set -e

# Conectarse al cluster
echo "Conectándose al cluster Kubernetes services-cluster..."
gcloud container clusters get-credentials services-cluster --region=us-central1

echo -e "\n🚀 Subiendo imagen de Telemetry Microservice...\n"
pushd Microservices/TelemetryMicroservice > /dev/null
gcloud builds submit --region=us-central1 --tag us-central1-docker.pkg.dev/$PROJECT_ID/siot-repo/seluc3m-siot-telemetry-microservice:c1
popd > /dev/null

echo -e "\n📦 Aplicando ConfigMaps...\n"
kubectl apply -f Microservices/microservices-common-configmap.yml
kubectl apply -f Microservices/TelemetryMicroservice/telemetry-microservice-configmap.yml

echo -e "\n🔐 Aplicando secretos comunes...\n"
kubectl apply -f Microservices/microservices-common-secrets.yml

echo -e "\n🌐 Aplicando servicio Telemetry Microservice...\n"
kubectl apply -f Microservices/TelemetryMicroservice/telemetry-microservice-service.yml

echo -e "\n📤 Desplegando deployment Telemetry Microservice...\n"
kubectl apply -f Microservices/TelemetryMicroservice/telemetry-microservice-deployment.yml
