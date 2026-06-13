FROM node:20-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# A Railway injeta as variaveis do servico como build args (docs/09);
# o Vite so embute VITE_API_BASE_URL no bundle se ela existir em build time.
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM node:20-slim

WORKDIR /app

COPY --from=build /app/dist ./dist
RUN npm install -g serve

# A Railway injeta a porta via $PORT (docs/09, seção 11.2).
CMD serve -s dist -l $PORT
