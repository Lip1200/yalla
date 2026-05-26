# syntax=docker/dockerfile:1.7
#
# Two-stage build for the doctor-web Vite SPA:
#   stage 1 (node)  — npm install + `npm run build` → produces ./dist
#   stage 2 (nginx) — serves the static dist on :80 with SPA fallback
#
# Build:  docker build -t yalla-doctor-web .
# Run:    docker run -p 8080:80 yalla-doctor-web
#
# Build-arg `VITE_API_BASE_URL` is injected at build time (Vite bakes
# env vars into the bundle; they cannot change at runtime).

# ===== Stage 1 — build =====
FROM node:20-alpine AS build

WORKDIR /app

# Copy lockfile first for layer caching.
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY . .

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# ===== Stage 2 — serve =====
FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# Drop privileges (the alpine image runs as root by default; map worker
# processes via nginx.conf's `user` directive if needed in the future).

CMD ["nginx", "-g", "daemon off;"]
