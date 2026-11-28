FROM node:22.23.5-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build && chown -R node:node /app
USER node
EXPOSE 5173
CMD ["npm", "run", "dev"]
