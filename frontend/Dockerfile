FROM node:18

WORKDIR /nachet-frontend

# Copy package files and install dependencies
COPY package*.json ./
COPY tsconfig.json ./

RUN npm install -g npm@9.8.1
# RUN npm install --include=dev

# Copy the rest of the application
COPY . .
RUN rm -rf .git

# Make the startup script executable
RUN chmod +x ./startup.sh

ARG ARG_PUBLIC_URL
ARG ARG_VITE_BACKEND_URL

# Default values for environment variables
ENV PUBLIC_URL=${ARG_PUBLIC_URL:-.}
ENV VITE_BACKEND_URL=${ARG_VITE_BACKEND_URL:-/api}

EXPOSE 3000

# Use the startup script as the entrypoint
ENTRYPOINT ["./startup.sh"]
