# ---------- Builder ----------
ARG NODE_BASE_IMAGE=node:22-alpine
ARG NGINX_BASE_IMAGE=nginx:alpine

FROM ${NODE_BASE_IMAGE} AS builder

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ---------- Production ----------
FROM ${NGINX_BASE_IMAGE}

COPY --from=builder /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]