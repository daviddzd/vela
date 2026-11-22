# Stage 1: build the React app with Node. Stage 2: serve the static files with Caddy.
FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2
COPY --from=build /app/dist /srv
COPY web.Caddyfile /etc/caddy/Caddyfile
