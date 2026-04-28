from fastapi import APIRouter, HTTPException, Query
import httpx
import os

router = APIRouter()

TMDB_BASE  = "https://api.themoviedb.org/3"
TMDB_IMAGE = "https://image.tmdb.org/t/p"


def get_token():
    token = os.getenv("TMDB_API_KEY")
    if not token:
        raise HTTPException(500, "TMDB_API_KEY não configurada no .env")
    return token


@router.get("/search")
async def search_filmes(q: str = Query(..., min_length=1)):
    token = get_token()
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{TMDB_BASE}/search/movie",
            params={"api_key": token, "query": q, "language": "pt-BR"},
            timeout=10,
        )
    if r.status_code != 200:
        raise HTTPException(r.status_code, "Erro TMDB")

    results = []
    for m in r.json().get("results", [])[:10]:
        results.append({
            "tmdb_id":         str(m["id"]),
            "titulo":          m.get("title", ""),
            "titulo_original": m.get("original_title", ""),
            "sinopse":         m.get("overview", ""),
            "ano":             int(m["release_date"][:4]) if m.get("release_date") else None,
            "poster_url":      f"{TMDB_IMAGE}/w342{m['poster_path']}" if m.get("poster_path") else None,
            "backdrop_url":    f"{TMDB_IMAGE}/w780{m['backdrop_path']}" if m.get("backdrop_path") else None,
        })
    return results


@router.get("/movie/{tmdb_id}")
async def get_movie_detail(tmdb_id: str):
    token = get_token()
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{TMDB_BASE}/movie/{tmdb_id}",
            params={"api_key": token, "language": "pt-BR"},
            timeout=10,
        )
    if r.status_code != 200:
        raise HTTPException(r.status_code, "Erro TMDB")

    m = r.json()
    return {
        "tmdb_id":         str(m["id"]),
        "titulo":          m.get("title", ""),
        "titulo_original": m.get("original_title", ""),
        "sinopse":         m.get("overview", ""),
        "ano":             int(m["release_date"][:4]) if m.get("release_date") else None,
        "duracao_min":     m.get("runtime"),
        "nota_tmdb":       m.get("vote_average"),
        "generos":         [g["name"] for g in m.get("genres", [])],
        "poster_url":      f"{TMDB_IMAGE}/w342{m['poster_path']}" if m.get("poster_path") else None,
        "backdrop_url":    f"{TMDB_IMAGE}/w780{m['backdrop_path']}" if m.get("backdrop_path") else None,
    }


@router.get("/movie/{tmdb_id}/providers")
async def get_movie_providers(tmdb_id: str):
    token = get_token()
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{TMDB_BASE}/movie/{tmdb_id}/watch/providers",
            params={"api_key": token},
            timeout=10,
        )
    if r.status_code == 404:
        return {}
    if r.status_code != 200:
        raise HTTPException(r.status_code, "Erro TMDB")
    return r.json().get("results", {})
