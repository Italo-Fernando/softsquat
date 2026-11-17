<p align="center">
  <img src="assets/gorilla_emblem.svg" alt="Softsquat Logo" width="150" />
</p>

# Softsquat
## <img src="assets/stack_icon.svg" width="24" height="24" style="vertical-align: middle; margin-right: 4px;"> Stacks

**Back-end**

<img src="https://skillicons.dev/icons?i=py,fastapi,postgres&theme=dark&perline=3" alt="Back-end" />

**DevOps**

<img src="https://skillicons.dev/icons?i=linux,docker,github&theme=dark&perline=3" alt="DevOps" />

## <img src="assets/terminal.svg" width="24" height="24" style="vertical-align: middle; margin-right: 4px;"> Quickstart

### Pré-requisitos

Configure as variáveis exigidas pela aplicação em um arquivo `.env` na raiz:

```dotenv
DATABASE_URL=postgresql+psycopg://app_user:app_password@localhost:5432/app_db
EMAIL_CHECK_DELIVERABILITY=false
SECRET_KEY=defina-uma-chave-local
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256
```

### Executar localmente com Poetry

Inicie o PostgreSQL definido no Compose:

```bash
docker compose up -d softsquat_database
```

Instale as dependências do projeto, incluindo as de desenvolvimento, aplique as
migrações e inicie a API:

```bash
poetry install --with dev
poetry run alembic upgrade head
poetry run task run
```

### Executar com containers

O Compose inicia o PostgreSQL e a aplicação. O entrypoint da aplicação aplica as
migrações antes de iniciar o servidor:

```bash
docker compose up --build
```

Nos dois modos, a documentação interativa da API fica em
<http://localhost:8000/docs>. Para parar os containers, use `Ctrl+C` e depois:

```bash
docker compose down
```
