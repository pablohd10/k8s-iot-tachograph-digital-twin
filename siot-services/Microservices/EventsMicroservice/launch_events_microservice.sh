#!/bin/bash
set -e

# Conectarse al cluster
echo "Conectándose al cluster Kubernetes services-cluster..."
gcloud container clusters get-credentials services-cluster --region=us-central1

echo -e "\n🚀 Subiendo imagen de Events Microservice...\n"
pushd Microservices/EventsMicroservice > /dev/null
gcloud builds submit --region=us-central1 --tag us-central1-docker.pkg.dev/$PROJECT_ID/siot-repo/seluc3m-siot-events-microservice:c1
popd > /dev/null

echo -e "\n📦 Aplicando ConfigMaps de EventsMicroservice...\n"
kubectl apply -f Microservices/microservices-common-configmap.yml
kubectl apply -f Microservices/EventsMicroservice/events-microservice-configmap.yml

echo -e "\n🔐 Aplicando secretos comunes de EventsMicroservice...\n"
kubectl apply -f Microservices/microservices-common-secrets.yml

echo -e "\n🌐 Aplicando servicio Events Microservice...\n"
kubectl apply -f Microservices/EventsMicroservice/events-microservice-service.yml

echo -e "\n📤 Desplegando deployment Events Microservice...\n"
kubectl apply -f Microservices/EventsMicroservice/events-microservice-deployment.yml
