#!/bin/bash
set -e

# Conectarse al cluster
echo "Conectándose al cluster Kubernetes services-cluster..."
gcloud container clusters get-credentials services-cluster --region=us-central1

echo -e "\n🚀 Subiendo imagen de contenedor MariaDB...\n"
pushd DBService > /dev/null
gcloud builds submit --region=us-central1 --tag us-central1-docker.pkg.dev/$PROJECT_ID/siot-repo/seluc3m-siot-mariadb:c1 
popd > /dev/null

echo -e "\n📦 Aplicando StorageClass MariaDB...\n"
kubectl apply -f DBService/mariadb-storage-class.yml
kubectl get storageclass

echo -e "\n💾 Creando PVC MariaDB...\n"
kubectl apply -f DBService/mariadb-pvc.yml
kubectl get pvc

echo -e "\n🔐 Creando secretos MariaDB...\n"
kubectl apply -f DBService/mariadb-secrets.yml

echo -e "\n📤 Desplegando deployment MariaDB...\n"
kubectl apply -f DBService/mariadb-deployment.yml
kubectl get deployments

echo -e "\n🌐 Creando servicio MariaDB...\n"
kubectl apply -f DBService/mariadb-service.yml
