# syntax=docker/dockerfile:1
# Copyright 2026 Aaron John Schlosser, PhD.
FROM node:22-alpine AS build

WORKDIR /app
COPY package.json .
RUN npm install

COPY . .
ARG GIT_COMMIT=
RUN --mount=type=bind,from=gitmeta,target=/tmp/git \
    apk add --no-cache git \
    && export GIT_COMMIT="${GIT_COMMIT:-$(git --git-dir=/tmp/git rev-parse --short HEAD 2>/dev/null || true)}" \
    && npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
