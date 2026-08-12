ARG NODE_VERSION=22.23.2

FROM node:${NODE_VERSION}-bookworm-slim AS dependencies

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci && chown -R node:node /app/node_modules

FROM dependencies AS development

COPY --chown=node:node . .

USER node

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

FROM dependencies AS build

COPY --chown=node:node . .
RUN chown node:node /app

USER node

RUN npm run build
