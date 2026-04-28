from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from dotenv import load_dotenv
from backend.routers import filmes, plataformas, projetos, stats, tmdb, images, configuracao, diario, reports, storage

load_dotenv()

app = FastAPI(title="Fiscal de Filmes API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(filmes.router,       prefix="/api/filmes",      tags=["filmes"])
app.include_router(plataformas.router,  prefix="/api/plataformas", tags=["plataformas"])
app.include_router(projetos.router,     prefix="/api/projetos",    tags=["projetos"])
app.include_router(stats.router,        prefix="/api/stats",       tags=["stats"])
app.include_router(tmdb.router,         prefix="/api/tmdb",        tags=["tmdb"])
app.include_router(images.router,       prefix="/images",          tags=["images"])
app.include_router(configuracao.router, prefix="/api/configuracao", tags=["configuracao"])
app.include_router(diario.router,       prefix="/api/diario",      tags=["diario"])
app.include_router(reports.router,      prefix="/api/reports",     tags=["reports"])
app.include_router(storage.router,      prefix="/api/storage",     tags=["storage"])

frontend_path = Path(__file__).parent.parent / "frontend"

if (frontend_path / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")
if (frontend_path / "css").exists():
    app.mount("/css", StaticFiles(directory=str(frontend_path / "css")), name="css")
if (frontend_path / "js").exists():
    app.mount("/js", StaticFiles(directory=str(frontend_path / "js")), name="js")


@app.get("/")
async def root():
    index = frontend_path / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Fiscal de Filmes API"}


@app.get("/{path:path}")
async def serve_frontend(path: str):
    file = frontend_path / path
    if file.exists() and file.suffix in (".html", ".css", ".js", ".png", ".jpg", ".svg"):
        return FileResponse(str(file))
    index = frontend_path / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Not found"}
