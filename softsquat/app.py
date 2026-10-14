from http import HTTPStatus

from fastapi import FastAPI

from softsquat.routers import users
from softsquat.schemas import Message

app = FastAPI()

app.include_router(users.router)


@app.get('/', status_code=HTTPStatus.OK, response_model=Message)
def read_root():
    return {'message': 'olá mundo'}
