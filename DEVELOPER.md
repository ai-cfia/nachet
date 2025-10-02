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
```  

- access pgadmin at <http://localhost:12433>  
- login with the email and password you set in the .env.config.local file  
- create a new server with the database connection details from the .env.config.local file  
- browse your database and schema using pgadmin

<!-- ### Datastore setup deprecated

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
``` -->

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

# initialize the database (creates tables, runs migrations, creates initial user)
nachet/backend$ cd app/db
nachet/backend/app/db$ uv run setup_db_local.py

# run all db tests with coverage
nachet/backend/app/db$ uv run pytest tests/ -v --tb=short --cov=. --cov-report=xml --cov-report=term-missing

# run integration tests or unit tests only
nachet/backend/app/db$ uv run pytest tests/ -v --tb=short --cov=. --cov-report=xml --cov-report=term-missing -m "integration"
nachet/backend/app/db$ uv run pytest tests/ -v --tb=short --cov=. --cov-report=xml --cov-report=term-missing -m "not integration"

# run tests
nachet/backend$ ./run_tests.sh
nachet/backend$ deactivate

# lint
nachet/backend$  uv run ruff check .

# push frontend build to blob storage
nachet/backend$ uv run app/scripts/push_frontend_to_blob.py
```

### Frontend setup

```bash
nachet$ cd frontend

# enter your own values in the .env.config.local file
nachet/frontend$ cp .env.template .env.config.local
nachet/frontend$ nano .env.config.local
nachet/frontend$ npm run update
nachet/frontend$ npm run test

# run dev with env vars from .env.config.local
# nachet/frontend$ source .env.config.local # requires export keyword in the file
nachet/frontend$ export $(grep -v '^#' .env.config.local | xargs)
nachet/frontend$ npm run dev -- --port 12438

# unset env vars
nachet/frontend$ unset $(grep -v '^#' .env.config.local | grep -v '^$' | cut -d= -f1)
```

### Update the compose file as needed

```bash
nachet$ nano docker-compose.yaml
```

### Start the rest of the services

```bash
nachet$ docker compose -f docker-compose.yaml up -d
nachet$ $ docker ps -a --format "table {{.Image}}\t{{.Names}}\t{{.RunningFor}}\t{{.Status}}\t{{.Ports}}"
IMAGE                                                                       NAMES                      CREATED             STATUS                      PORTS
ghcr.io/ai-cfia/nachet-backend:29-azureml-swin-classifier                   nachet-15-spp-classifier   2 minutes ago       Up 2 minutes                0.0.0.0:12390->5001/tcp, [::]:12390->5001/tcp, 0.0.0.0:12391->8883/tcp, [::]:12391->8883/tcp, 0.0.0.0:12392->8888/tcp, [::]:12392->8888/tcp
ghcr.io/ai-cfia/nachet-model-ccds/gpu-classifier-27spp-model-1:2025030321   nachet-27-spp-classifier   2 minutes ago       Up 3 seconds                7070-7071/tcp, 8081-8082/tcp, 0.0.0.0:12360->8080/tcp, [::]:12360->8080/tcp
ghcr.io/ai-cfia/nachet-backend:1.0.4                                        nachet-backend             42 minutes ago      Up 2 minutes                0.0.0.0:12435->5174/tcp, [::]:12435->5174/tcp
dpage/pgadmin4:latest                                                       nachet-pgadmin             53 minutes ago      Up 53 minutes               443/tcp, 0.0.0.0:12433->80/tcp, [::]:12433->80/tcp
postgres:15-bookworm                                                        nachet-db                  53 minutes ago      Up 53 minutes               0.0.0.0:12432->5432/tcp, [::]:12432->5432/tcp
ghcr.io/ai-cfia/nachet-frontend:0.9.31                                      nachet-frontend            About an hour ago   Up About an hour            3000/tcp, 0.0.0.0:12436->5173/tcp, [::]:12436->5173/tcp
ghcr.io/ai-cfia/nachet-backend:29-azureml-seed-detector                     nachet-detector            About an hour ago   Up About an hour            0.0.0.0:12380->5001/tcp, [::]:12380->5001/tcp, 0.0.0.0:12381->8883/tcp, [::]:12381->8883/tcp, 0.0.0.0:12382->8888/tcp, [::]:12382->8888/tcp
mcr.microsoft.com/azure-storage/azurite:3.35.0                              nachet-blob                4 hours ago         Up 4 hours                  10001-10002/tcp, 0.0.0.0:12434->10000/tcp, [::]:12434->10000/tcp
```

## Useful Commands

```bash
nachet$ docker compose -f docker-compose.yaml down
nachet$ docker compose -f docker-compose.yaml logs -f
nachet$ docker compose -f docker-compose.yaml exec backend bash
nachet$ docker compose -f docker-compose.yaml exec frontend bash
nachet$ docker compose -f docker-compose.yaml exec db psql -U <your_db_user> -d <your_db_name>
nachet$ docker ps -a --format "table {{.Image}}\t{{.Names}}\t{{.RunningFor}}\t{{.Status}}\t{{.Ports}}"
nachet$ docker logs -f --tail 20 nachet-backend
nachet$ docker stop <container_id or container_name>
nachet$ docker start <container_id or container_name>
nachet$ docker rm <container_id or container_name>
nachet$ docker compose -f docker-compose.yaml stop
nachet$ docker compose -f docker-compose.yaml start
nachet$ docker compose -f docker-compose.yaml restart
nachet$ docker compose -f docker-compose.yaml rm
nachet$ docker compose -f docker-compose.yaml pull
# create a first migration file
nachet/backend/app/db $ uv run alembic revision --autogenerate -m "First migration 0.2.0"

# create a new migration file
nachet/backend/app/db $ uv run alembic revision --autogenerate -m "Add new_field to MyTable"

# apply migrations
nachet/backend/app/db $ uv run alembic upgrade head

# downgrade to a previous migration
nachet/backend/app/db $ uv run alembic downgrade <revision_id>

# check current migration version
nachet/backend/app/db $ uv run alembic current

# show the history of migrations
nachet/backend/app/db $ uv run alembic history

# check if your orm models are valid
nachet/backend/app/db $ uv run validate_orm_offline.py
nachet/backend/app/db $ uv run validate_orm_online.py

# check if you need to generate a new migration
nachet/backend/app/db $ uv run validate_orm_alembic.py

# check if your database is synchronized with the alembic head
nachet/backend/app/db $ uv run validate_db_synchronized.py
```

## Development

At this point you will have the full stack, you will be able to test integration with all components.

## Backend changes

- When making changes to the backend, ensure that you update the database schema if necessary. Use Alembic for managing database migrations.
- the first step should be to bump the version in the `backend/pyproject.toml` file.
- build your changes locally `nachet $ docker compose -f docker-compose.yaml build nachet-backend --no-cache`
- deploy your changes locally `nachet $ docker compose -f docker-compose.yaml up -d nachet-backend --force-recreate`
- quick check module imports are good `nachet/backend $  python -c "import app.main"`
