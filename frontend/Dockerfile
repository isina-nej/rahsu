FROM node:22-alpine AS build
WORKDIR /src
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY . .
ARG VITE_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty
ENV VITE_MAP_STYLE_URL=$VITE_MAP_STYLE_URL
RUN npm run build
FROM nginx:1.27-alpine
COPY --from=build /src/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
