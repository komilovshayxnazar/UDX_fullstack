# syntax=docker/dockerfile:1.7

# ── Stage 1 · Vite build ────────────────────────────────────────────────
FROM node:20-alpine AS builder

ENV CI=1

WORKDIR /app

# Copy manifests first so `npm ci` is cached across source-only rebuilds.
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

# Everything else the Vite build needs.
COPY tsconfig*.json vite.config.ts index.html ./
COPY src ./src

# Same-origin default: Nginx below proxies /api/* → backend:8000, so
# building with VITE_API_URL=/api keeps everything on one host.
ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build


# ── Stage 2 · nginx runtime ─────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Drop the stock default and replace with our reverse-proxy config.
RUN rm /etc/nginx/conf.d/default.conf
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Vite's outDir is `build/` (see vite.config.ts).
COPY --from=builder /app/build /usr/share/nginx/html

EXPOSE 80

# The stock nginx CMD is fine; keep it explicit for grep-ability.
CMD ["nginx", "-g", "daemon off;"]
