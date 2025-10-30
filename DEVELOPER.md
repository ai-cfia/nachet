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
nachet/db$ cd ..

# create required folders
nachet$ mkdir -p db/postgres-data
nachet$ mkdir -p db/pgadmin-data
nachet$ mkdir -p blob/azurite
# optional ozone, only if you need s3 api call implemented in ozone but missing from garage
nachet$ mkdir -p blob/ozone

# create database and pgadmin containers
nachet$ docker compose -f docker-compose.yaml up -d nachet-db nachet-pgadmin 

# azurite blob storage
# you can use azure storage explorer to view the blobs https://azure.microsoft.com/en-us/products/storage/storage-explorer#Download-4
nachet$ docker compose -f docker-compose.yaml up -d nachet-blob --force-recreate

# ozone s3 compatible storage (optional)
# nachet$ docker compose -f docker-compose.yaml up -d datanode om scm recon s3g httpfs

# garage s3 compatible storage (preferred, single container)
nachet$ docker compose -f docker-compose.yaml up -d nachet-op-blob nachet-op-blob-webui --force-recreate

# check garage status
nachet$ docker exec -ti nachet-op-blob /garage status
|  ==== HEALTHY NODES ====
|  ID                Hostname      Address          Tags  Zone  Capacity          DataAvail  Version
|  63a9650ddf005cc6  c8cdccadde8e  127.0.0.1:12441              NO ROLE ASSIGNED             v2.1.0

# setup zone and capacity , replace 63a9 with your node ID
nachet$ docker exec -ti nachet-op-blob /garage layout assign -z dc1 -c 1G 63a9
|  Role changes are staged but not yet committed.
|  Use `garage layout show` to view staged role changes,
|  and `garage layout apply` to enact staged changes.

nachet$ docker exec -ti nachet-op-blob /garage layout apply --version 1 
|  ==== COMPUTATION OF A NEW PARTITION ASSIGNATION ====
|
|  Partitions are replicated 1 times on at least 1 distinct zones.
|
|  Optimal partition size:                     3.9 MB
|  Usable capacity / total cluster capacity:   1000.0 MB / 1000.0 MB (100.0 %)
|  Effective capacity (replication factor 1):  1000.0 MB
|
|  dc1                 Tags  Partitions        Capacity   Usable capacity
|    63a9650ddf005cc6  []    256 (256 new)     1000.0 MB  1000.0 MB (100.0%)
|    TOTAL                   256 (256 unique)  1000.0 MB  1000.0 MB (100.0%)
|
|
|  New cluster layout with updated role assignment has been applied in cluster.
|  Data will now be moved around between nodes accordingly.

# create access keys . put these in your env files
nachet$ docker exec -ti nachet-op-blob /garage key create nachet-local-dev-key
| ==== ACCESS KEY INFORMATION ====
| Key ID:              <your access key id>
| Key name:            nachet-local-dev-key
| Secret key:          <your secret access key>
| Created:             2025-10-19 03:58:46.375 +00:00
| Validity:            valid
| Expiration:          never
|
| Can create buckets:  false
|
| ==== BUCKETS FOR THIS KEY ====
| Permissions  ID  Global aliases  Local aliases

# create a bucket / container . put this in your env files
nachet$ docker exec -ti nachet-op-blob /garage bucket create nachet-local-dev-bucket
| ==== BUCKET INFORMATION ====
| Bucket:          7a89fed6e3b655390dc7a9e2dda7d6903a903226a0755844274b078c4bede739
| Created:         2025-10-19 04:19:45.339 +00:00
|
| Size:            0 B (0 B)
| Objects:         0
|
| Website access:  false
|
| Global alias:    nachet-local-dev-bucket
|
| ==== KEYS FOR THIS BUCKET ====
| Permissions  Access key    Local aliases

# assign permissions to the key for this bucket
nachet$ docker exec -ti nachet-op-blob /garage bucket allow --read --write --owner nachet-local-dev-bucket --key nachet-local-dev-key

| ==== BUCKET INFORMATION ====
| Bucket:          7a89fed6e3b655390dc7a9e2dda7d6903a903226a0755844274b078c4bede739
| Created:         2025-10-19 04:19:45.339 +00:00
| 
| Size:            0 B (0 B)
| Objects:         0
| 
| Website access:  false
| 
| Global alias:    nachet-local-dev-bucket
| 
| ==== KEYS FOR THIS BUCKET ====
| Permissions  Access key                                        Local aliases
| RWO          <your access key id>  nachet-local-dev-key  

# allow the key to create buckets
nachet$ docker exec -ti nachet-op-blob /garage key allow --create-bucket nachet-local-dev-key
| ==== ACCESS KEY INFORMATION ====
| Key ID:              <your access key id>
| Key name:            nachet-local-dev-key
| Secret key:          (redacted)
| Created:             2025-10-19 03:58:46.375 +00:00
| Validity:            valid
| Expiration:          never
|
| Can create buckets:  true
|
| ==== BUCKETS FOR THIS KEY ====
| Permissions  ID                Global aliases           Local aliases
| RWO          7a89fed6e3b65539  nachet-local-dev-bucket 
```  

- access pgadmin at <http://localhost:12433>  
- login with the email and password you set in the .env.config.local file  
- create a new server with the database connection details from the .env.config.local file  
- browse your database and schema using pgadmin

### observability setup grafana alloy loki

```bash
# enter your own values in the .env.local file
nachet$ cd observability
nachet/observability$ cp .env.template .env.local
nachet/observability$ nano .env.local
nachet$ cd ..
nachet$ docker compose -f docker-compose.yaml up -d grafana loki alloy
```

### Backend setup

```bash
nachet$ cd backend

# enter your own values in the .env.local file
nachet/backend$ cp .env.template .env.local
nachet/backend$ nano .env.local

# enter your own values in the .env.container.local file
nachet/backend$ cp .env.template .env.container.local
nachet/backend$ nano .env.container.local

# enter your own values in the .env.test.local file
nachet/backend$ cp .env.test.template .env.test.local
nachet/backend$ nano .env.test.local

# initialize venv
nachet/backend$ uv sync
nachet/backend$ source .venv/bin/activate

# initialize the database (creates tables, runs migrations, creates initial user)
nachet/backend$ cd app/db
nachet/backend/app/db$ export $(grep -v '^#' ../../.env.local | xargs)
nachet/backend/app/db$ uv run db_setup_local.py
nachet/backend/app/db$ export $(grep -v '^#' ../../.env.test.local | xargs)
nachet/backend/app/db$ uv run db_setup_test.py
nachet/backend/app/db$ export $(grep -v '^#' ../../.env.test.local | xargs) && uv run alembic upgrade head
nachet/backend/app/db$ export $(grep -v '^#' ../../.env.local | xargs) && uv run alembic upgrade head

# run all db tests with coverage
nachet/backend/app/db$ uv run pytest tests/ -v --tb=short --cov=. --cov-report=xml --cov-report=term-missing

# run integration tests or unit tests only
nachet/backend/app/db$ uv run pytest tests/ -v --tb=short --cov=. --cov-report=xml --cov-report=term-missing -m "integration"
nachet/backend/app/db$ uv run pytest tests/ -v --tb=short --cov=. --cov-report=xml --cov-report=term-missing -m "not integration"

# run tests
nachet/backend$ uv run pytest tests/ -v --tb=short
nachet/backend$ deactivate

# lint
nachet/backend$  uv run ruff check --fix

# push frontend build to blob storage
nachet/backend$ uv run app/scripts/push_frontend_to_blob.py

nachet$ docker compose -f docker-compose.yaml.local build nachet-backend --no-cache && docker compose -f docker-compose.yaml.local up -d nachet-backend --force-recreate
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

# UML and diagram
nachet/backend $ for module in annotation auth base_crud change_log constants device directory frontend image image_objects logs model organization pipeline rbac seed user; do \
  echo "Generating UML for service/$module..." && \
  uv run pyreverse -o puml -A -s 1 -p "service_$module" "app/service/$module" -d eac/ && \
  uv run pyreverse -o png -A -s 1 --colorized -p "service_$module" "app/service/$module" -d eac/; \
done && \
echo "UML diagrams generated successfully" && \
ls -lh eac/

nachet/backend $ for module in annotation base_crud change_log device directory image image_objects model organization pending_registration pipeline rbac seed user; do \
  echo "Generating UML for datastore/$module..." && \
  uv run pyreverse -o puml -A -s 1 -p "datastore_$module" "app/datastore/$module" -d eac/ && \
  uv run pyreverse -o png -A -s 1 --colorized -p "datastore_$module" "app/datastore/$module" -d eac/; \
done && \
echo "UML diagrams generated successfully" && \
ls -lh eac/

nachet/backend $ uv run pyreverse -o puml -A -s 1 -p "api" "app/api/" -d eac/ && \
uv run pyreverse -o png -A -s 1 --colorized -p "api" "app/api/" -d eac/ && \
echo "UML diagrams generated successfully" && \
ls -lh eac/

nachet/backend $ uv run pyreverse -o puml -A -s 1 -p "middleware" "app/middleware/" -d eac/ && \
uv run pyreverse -o png -A -s 1 --colorized -p "middleware" "app/middleware/" -d eac/ && \
echo "UML diagrams generated successfully" && \
ls -lh eac/

# Core blob layer (interface, manager, models, exceptions)
nachet/backend $ uv run pyreverse -o puml -A -s 1 -p "blob_core" "app/blob/interface.py" "app/blob/manager.py" "app/blob/models.py" "app/blob/exceptions.py" -d eac/ && \
uv run pyreverse -o png -A -s 1 --colorized -p "blob_core" "app/blob/interface.py" "app/blob/manager.py" "app/blob/models.py" "app/blob/exceptions.py" -d eac/ && \
echo "UML diagrams generated successfully" && \
ls -lh eac/

# Blob interface only
nachet/backend $ mkdir -p eac && \
echo "Generating UML for blob interface..." && \
uv run pyreverse -o puml -A -s 1 -p "blob_interface" "app/blob/interface.py" -d eac/ && \
uv run pyreverse -o png -A -s 1 --colorized -p "blob_interface" "app/blob/interface.py" -d eac/ && \
echo "UML diagrams generated successfully" && \
ls -lh eac/

# Blob manager only
nachet/backend $ mkdir -p eac && \
echo "Generating UML for blob manager..." && \
uv run pyreverse -o puml -A -s 1 -p "blob_manager" "app/blob/manager.py" -d eac/ && \
uv run pyreverse -o png -A -s 1 --colorized -p "blob_manager" "app/blob/manager.py" -d eac/ && \
echo "UML diagrams generated successfully" && \
ls -lh eac/

# Blob models (BaseModel classes)
nachet/backend $ mkdir -p eac && \
echo "Generating UML for blob models..." && \
uv run pyreverse -o puml -A -s 1 -p "blob_models" "app/blob/models.py" -d eac/ && \
uv run pyreverse -o png -A -s 1 --colorized -p "blob_models" "app/blob/models.py" -d eac/ && \
echo "UML diagrams generated successfully" && \
ls -lh eac/

# Blob exceptions (BlobStorageError classes)
nachet/backend $ mkdir -p eac && \
echo "Generating UML for blob exceptions..." && \
uv run pyreverse -o puml -A -s 1 -p "blob_exceptions" "app/blob/exceptions.py" -d eac/ && \
uv run pyreverse -o png -A -s 1 --colorized -p "blob_exceptions" "app/blob/exceptions.py" -d eac/ && \
echo "UML diagrams generated successfully" && \
ls -lh eac/

# Azure blob client
nachet/backend $ uv run pyreverse -o puml -A -s 1 -p "blob_azure_client" "app/blob/azure/client.py" -d eac/ && \
uv run pyreverse -o png -A -s 1 --colorized -p "blob_azure_client" "app/blob/azure/client.py" -d eac/ && \
echo "UML diagrams generated successfully" && \
ls -lh eac/

# Azure blob storage
nachet/backend $ uv run pyreverse -o puml -A -s 1 -p "blob_azure_storage" "app/blob/azure/storage.py" -d eac/ && \
uv run pyreverse -o png -A -s 1 --colorized -p "blob_azure_storage" "app/blob/azure/storage.py" -d eac/ && \
echo "UML diagrams generated successfully" && \
ls -lh eac/

# Azure blob operations (each operation type separately)
nachet/backend $ for operation in blob_operations container_operations metadata_operations security_operations tier_operations advanced_operations; do \
  echo "Generating UML for blob azure operations/$operation..." && \
  uv run pyreverse -o puml -A -s 1 -p "blob_azure_${operation}" "app/blob/azure/operations/${operation}.py" -d eac/ && \
  uv run pyreverse -o png -A -s 1 --colorized -p "blob_azure_${operation}" "app/blob/azure/operations/${operation}.py" -d eac/; \
done && \
echo "UML diagrams generated successfully" && \
ls -lh eac/

# Azure blob utilities
nachet/backend $ uv run pyreverse -o puml -A -s 1 -p "blob_azure_utils" "app/blob/azure/utils/" -d eac/ && \
uv run pyreverse -o png -A -s 1 --colorized -p "blob_azure_utils" "app/blob/azure/utils/" -d eac/ && \
echo "UML diagrams generated successfully" && \
ls -lh eac/

```

## Development

At this point you will have the full stack, you will be able to test integration with all components.

## Backend changes

- When making changes to the backend, ensure that you update the database schema if necessary. Use Alembic for managing database migrations.
- the first step should be to bump the version in the `backend/pyproject.toml` file.
- run the sbom generation script to update the software bill of materials `nachet $ ./generate_sbom.sh backend`
- build your changes locally `nachet $ docker compose -f docker-compose.yaml build nachet-backend --no-cache`
- deploy your changes locally `nachet $ docker compose -f docker-compose.yaml up -d nachet-backend --force-recreate`
- quick check module imports are good `nachet/backend $  python -c "import app.main"`

## Frontend changes

- When making changes to the frontend, ensure that you test the application in different browsers for compatibility.
- the first step should be to bump the version in the `frontend/package.json` file.
- run the sbom generation script to update the software bill of materials `nachet $ ./generate_sbom.sh frontend`
- run `npm run prestart`
- build your changes locally `nachet/frontend $ npm run build`
- push the new build to blob storage `nachet/backend $ uv run app/scripts/push_frontend_to_blob.py --clean`
- you can also debug by running the frontend in dev mode and connecting to the backend `nachet/frontend $ npm run dev -- --port 12438`
- you can also run the frontend in a container `nachet $ docker compose -f docker-compose.yaml build nachet-frontend --no-cache && docker compose -f docker-compose.yaml up -d nachet-frontend --force-recreate`
