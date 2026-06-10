FROM node:20-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-slim

WORKDIR /app

COPY --from=build /app/dist ./dist
RUN npm install -g serve

# A Railway injeta a porta via $PORT (docs/09, seção 11.2).
CMD serve -s dist -l $PORT
