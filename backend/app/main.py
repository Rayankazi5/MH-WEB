from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.jobs import start_scheduler, stop_scheduler
from app.routers import auth, clinician, internal, patient, privacy

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Insight Navigator API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_V1 = "/api/v1"
app.include_router(auth.router,      prefix=_V1)
app.include_router(clinician.router, prefix=_V1)
app.include_router(patient.router,   prefix=_V1)
app.include_router(privacy.router,   prefix=_V1)
app.include_router(internal.router,  prefix=_V1)


@app.get("/health")
def health():
    return {"status": "ok"}
