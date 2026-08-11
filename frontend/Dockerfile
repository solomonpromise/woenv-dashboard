# Build the static bundle, then serve it from nginx. The previous compose file
# referenced this image but no Dockerfile existed, so `docker compose up` failed.
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies from the lockfile first so this layer caches.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Baked in at build time - Vite inlines env vars into the bundle.
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD wget -qO- http://localhost:3000/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
