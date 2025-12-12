from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware

from api.v1.auth import router as auth_router
from api.v1.users import router as users_router
from api.v1.tools import router as tools_router
from api.v1.subscriptions import router as subs_router
from api.v1.garden import router as garden_router
from api.v1.history import router as history_router
from api.v1.chat import router as chat_router
from api.v1.ws import router as ws_router
from api.v1.department import router as department_router
from fastapi.staticfiles import StaticFiles

from init_db import init_db, init_db_data

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = FastAPI(
    title="Bargam Backend",
    middleware=middleware
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup():
    await init_db()
    await init_db_data()


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(tools_router)
app.include_router(subs_router)
app.include_router(garden_router)
app.include_router(history_router)
app.include_router(chat_router)
app.include_router(ws_router)
app.include_router(department_router)
