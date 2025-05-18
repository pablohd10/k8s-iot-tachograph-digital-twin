#!/bin/bash
set -e

MINIKUBE_PROFILE="siot-cluster"  

# Cambiar contexto de kubectl a minikube
kubectl config use-context $MINIKUBE_PROFILE

# Configura el entorno Docker del clúster correspondiente
eval $(minikube -p $MINIKUBE_PROFILE docker-env)

echo -e "\n🚀 Creando imagen de contenedor MariaDB...\n"
pushd DBService > /dev/null
docker build -t seluc3m-siot-mariadb:c1 .
popd > /dev/null

echo -e "\n💾 Creando PVC MariaDB...\n"
kubectl apply -f DBService/mariadb-pvc-local.yml
kubectl get pvc

echo -e "\n🔐 Aplicando secretos MariaDB...\n"
kubectl apply -f DBService/mariadb-secrets.yml

echo -e "\n📤 Desplegando deployment MariaDB...\n"
kubectl apply -f DBService/mariadb-deployment-local.yml
kubectl get deployments

echo -e "\n🌐 Creando servicio MariaDB...\n"
kubectl apply -f DBService/mariadb-service.yml
