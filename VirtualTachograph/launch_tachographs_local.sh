#!/bin/bash

set -e
MINIKUBE_PROFILE="tachographs-cluster"
export SCRIPT_KEY_GENERATOR="generate_tachographs_key_pair.py"

if [ "$(basename "$PWD")" != "VirtualTachograph" ]; then
  echo "Este script debe ejecutarse desde el directorio 'VirtualTachograph'."
  exit 1
fi

echo "🔍 Comprobando si Docker está disponible..."
if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker no está corriendo. Por favor, abre Docker Desktop y vuelve a intentarlo."
  exit 1
fi

echo "✅ Docker está corriendo. Usaremos 'docker' como driver para Minikube."

echo "🚀 Iniciando Minikube con perfil '$MINIKUBE_PROFILE'..."
minikube start -p $MINIKUBE_PROFILE --driver=docker

# Configura el entorno Docker del cluster específico
eval $(minikube -p $MINIKUBE_PROFILE docker-env)
kubectl config use-context $MINIKUBE_PROFILE

# Construir imágenes Docker localmente
build_image() {
  local service=$1
  local tag=$2
  echo "🔧 Construyendo imagen para $service..."
  cd "$service" || exit
  docker build -t "$tag" .
  cd ..
}

build_image "ControlUnit" "seluc3m-siot-control-unit:c1"
build_image "CardReader" "seluc3m-siot-card-reader:c1"
build_image "Odometer" "seluc3m-siot-odometer:c1"
build_image "PositioningSystem" "seluc3m-siot-gnss:c1"
build_image "RoutesGenerator" "seluc3m-siot-routes-generator:c1"

echo "🔐 Generando claves de tacógrafos..."
cd kubernetes || exit
pip install "ruamel.yaml<0.18.0"
pip install pycryptodome --user
python3 ./$SCRIPT_KEY_GENERATOR

echo "⚙️ Aplicando ConfigMaps..."
kubectl apply -f ./configmaps/tachograph-configuration-configmap.yml
kubectl apply -f ./configmaps/odometer-configmap.yml
kubectl apply -f ./configmaps/routesgenerator-configmap.yml
kubectl apply -f ./configmaps/controlunit-configmap.yml
kubectl apply -f ./configmaps/cardreader-configmap.yml
kubectl apply -f ./configmaps/gnss-configmap.yml

echo "🔒 Aplicando Secrets..."
kubectl apply -f ./tachograph-keys.yml
kubectl apply -f ./tachograph-secrets.yml
kubectl create secret generic tachograph-tokens --from-file=./tokens.json

echo "📡 Aplicando servicios..."
kubectl apply -f ./tachograph-service.yml

echo "🚀 Desplegando pods..."
kubectl apply -f ./tachograph-statefulset.yml

cd ..
echo "✅ Despliegue local completado."
echo "Usa 'kubectl get pods' y 'kubectl get services' para verificar el estado."