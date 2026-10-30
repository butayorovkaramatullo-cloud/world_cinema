from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import settings
from .database import Base, SessionLocal, engine
from .routers import admin, auth, films, me, payments
from .seed import seed

STATIC = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Oddiy boshlanish: jadvallar yoʻq boʻlsa yaratiladi.
    # Keyinchalik sxema oʻzgarganda Alembic migratsiyalariga oʻtish tavsiya etiladi.
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="World Cinema film sayti uchun API: katalog, hisoblar, saqlanganlar, Premium va admin.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

for r in (auth.router, films.router, me.router, payments.router, admin.router):
    app.include_router(r)


@app.get("/api/health", tags=["tizim"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/admin", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(STATIC / "admin.html")
