from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from app.config import settings
from app.routes import academics, auth, records


@asynccontextmanager
async def lifespan(_: FastAPI):
    if len(settings.jwt_secret) < 32 or "replace-with-a-long-random-secret" in settings.jwt_secret:
        raise RuntimeError("Set JWT_SECRET to a unique random value of at least 32 characters in backend/.env.")
    yield


app = FastAPI(title="College ERP Management System", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip().rstrip("/") for origin in settings.frontend_origin.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(auth.user_router)
app.include_router(academics.router)
app.include_router(records.router)


@app.exception_handler(PyMongoError)
async def database_error_handler(_: Request, exc: PyMongoError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": f"Database operation failed: {exc.__class__.__name__}"})


@app.get("/")
def root() -> dict:
    return {"name": "College ERP Management System API", "docs": "/docs"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
