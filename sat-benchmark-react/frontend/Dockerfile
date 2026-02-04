# Frontend Dockerfile - React + Vite
FROM node:20-alpine

WORKDIR /app

# Copiar package files
COPY package*.json ./

# Instalar dependencias (usar npm install ya que no hay package-lock.json)
RUN npm install

# Copiar código fuente
COPY . .

# Puerto de desarrollo
EXPOSE 5173

# Comando por defecto (desarrollo)
CMD ["npm", "run", "dev", "--", "--host"]

# Para producción, usar multi-stage build:
# FROM node:20-alpine AS builder
# WORKDIR /app
# COPY package*.json ./
# RUN npm ci
# COPY . .
# RUN npm run build
#
# FROM nginx:alpine
# COPY --from=builder /app/dist /usr/share/nginx/html
# EXPOSE 80
# CMD ["nginx", "-g", "daemon off;"]
