# Node 22: the version the client was built and tested on.
FROM node:22-alpine

WORKDIR /app

# Copied first so the dependency layer is cached across code changes.
# package-lock.json pins every transitive version.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
