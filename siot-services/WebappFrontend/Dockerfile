# Usamos NGINX como base
FROM nginx:alpine

# Copiamos los archivos HTML, CSS, JS a la ubicación estática
COPY ./code/ /usr/share/nginx/html

# Copiamos la configuración personalizada de NGINX
COPY nginx.conf /etc/nginx/conf.d/default.conf