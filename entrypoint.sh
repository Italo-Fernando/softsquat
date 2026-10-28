#!/bin/sh

# Executa as migrações do banco de dados
alembic upgrade head

uvicorn --host 0.0.0.0 --port 8000 softsquat.app:app