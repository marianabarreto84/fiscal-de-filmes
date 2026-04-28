from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import httpx
from pathlib import Path

router = APIRouter()

CACHE_DIR       = Path(__file__).parent.parent.parent / "data" / "images"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"

SIMPLE_CATEGORIES = {
    "posters":   "w342",
    "backdrops": "w780",
}

PROVIDER_LOGO_DIR = CACHE_DIR / "providers"


@router.get("/providers/{filename}")
async def get_provider_logo(filename: str):
    path = PROVIDER_LOGO_DIR / filename
    if path.exists():
        return FileResponse(str(path), media_type="image/jpeg")

    tmdb_url = f"{TMDB_IMAGE_BASE}/w92/{filename}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(tmdb_url)
            if r.status_code != 200:
                raise HTTPException(502, "Falha ao buscar logo do TMDB")
            PROVIDER_LOGO_DIR.mkdir(parents=True, exist_ok=True)
            path.write_bytes(r.content)
    except httpx.RequestError:
        raise HTTPException(502, "Falha ao buscar logo do TMDB")

    return FileResponse(str(path), media_type="image/jpeg")


@router.get("/{category}/{filename}")
async def get_image(category: str, filename: str):
    if category not in SIMPLE_CATEGORIES:
        raise HTTPException(404, "Categoria de imagem desconhecida")

    path = CACHE_DIR / category / filename
    if path.exists():
        return FileResponse(str(path), media_type="image/jpeg")

    size    = SIMPLE_CATEGORIES[category]
    tmdb_url = f"{TMDB_IMAGE_BASE}/{size}/{filename}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(tmdb_url)
            if r.status_code != 200:
                raise HTTPException(502, "Falha ao buscar imagem do TMDB")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(r.content)
    except httpx.RequestError:
        raise HTTPException(502, "Falha ao buscar imagem do TMDB")

    return FileResponse(str(path), media_type="image/jpeg")
