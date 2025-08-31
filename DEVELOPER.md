# Developer Notes

This file contains notes for developers working on the Nachet project. It includes information about the development environment, tools, and processes used in the project.
Please refer to this document for guidance on setting up your development environment and contributing to the project.
Feel free to update this document as needed to reflect changes in the development process or environment.

## Development Environment

- The project uses Docker and Docker Compose for local development.  
- The backend is built using FastAPI and the frontend uses React with Vite.
- Environment variables are managed using `.env` files located in the respective `backend` and `frontend` directories.
- Each layer can be run independently using Docker Compose.

## Setup Instructions

### Clone the repository

### Navigate to the project directory

### Local database, blob store, and pgadmin setup

```bash
nachet$ cd db

# enter your own values in the .env.config.local file
nachet/db$ cp .env.config.template .env.config.local
nachet/db$ nano .env.config.local

# create database and pgadmin containers
nachet/db$ cd ..
nachet$ docker compose -f docker-compose.yaml up -d nachet-db nachet-pgadmin nachet-blob
nachet$ chmod +x db/dev_setup.sh

# load the dev schema
nachet$ db/./dev_setup.sh <your_schema_version> <your_db_name> <your_db_user> <your_db_password>
```  

- access pgadmin at <http://localhost:12433>  
- login with the email and password you set in the .env.config.local file  
- create a new server with the database connection details from the .env.config.local file  
- browse your database and schema using pgadmin

### Datastore setup

```bash
nachet$ cd datastore

# enter your own values in the .env.test.local file
nachet/datastore$ cp .env.test.template .env.test.local
nachet/datastore$ nano .env.test.local

# enter your own values in the .env.local file
nachet/datastore$ cp .env.template .env.local
nachet/datastore$ nano .env.local

# initialize venv
nachet/datastore$ uv sync
nachet/datastore$ source .venv/bin/activate
nachet/datastore$ ./run_tests.sh
nachet/datastore$ deactivate
```

### Backend setup

```bash
nachet$ cd backend

# enter your own values in the .env.config.local file
nachet/backend$ cp .env.config.template .env.config.local
nachet/backend$ nano .env.config.local

# enter your own values in the .env.test.local file
nachet/backend$ cp .env.test.template .env.test.local
nachet/backend$ nano .env.test.local

# initialize venv
nachet/backend$ uv sync
nachet/backend$ source .venv/bin/activate
nachet/backend$ ./run_tests.sh
nachet/backend$ deactivate
```

### Frontend setup

```bash
nachet$ cd frontend

# enter your own values in the .env.config.local file
nachet/frontend$ cp .env.template .env.config.local
nachet/frontend$ nano .env.config.local
nachet/frontend$ npm run update
nachet/frontend$ npm run test
```

### Update the compose file as needed

```bash
nachet$ nano docker-compose.yaml
```

### Start the rest of the services

```bash
nachet$ docker compose -f docker-compose.yaml up -d
```

## Useful Commands

```bash
nachet$ docker compose -f docker-compose.yaml down
nachet$ docker compose -f docker-compose.yaml logs -f
nachet$ docker compose -f docker-compose.yaml exec backend bash
nachet$ docker compose -f docker-compose.yaml exec frontend bash
nachet$ docker compose -f docker-compose.yaml exec db psql -U <your_db_user> -d <your_db_name>
nachet$ docker ps -a --format "table {{.Image}}\t{{.Names}}\t{{.RunningFor}}\t{{.Status}}\t{{.Ports}}"
nachet$ docker logs -f --tail 20 <container_id or container_name>
nachet$ docker stop <container_id or container_name>
nachet$ docker start <container_id or container_name>
nachet$ docker rm <container_id or container_name>
nachet$ docker compose -f docker-compose.yaml stop
nachet$ docker compose -f docker-compose.yaml start
nachet$ docker compose -f docker-compose.yaml restart
nachet$ docker compose -f docker-compose.yaml rm
```

## Development

At this point you will have the full stack, you will be able to test integration with all components.
