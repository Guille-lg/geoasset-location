# ---- Build stage ----
FROM oven/bun:1.1.0-alpine AS build
ARG VITE_APP_BACKEND_HOST
ARG VITE_APP_BACKEND_PORT
ARG VITE_APP_BACKEND_API_BASE

WORKDIR /app
COPY . .
RUN bun install
RUN bun run build

# ---- Production stage ----
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]

