# fiscal-de-filmes

App de tracking de filmes do ecossistema fiscal.

Veja as regras compartilhadas em `../CLAUDE.md`.

## Contexto

Tracker pessoal de filmes com integração Letterboxd (scraping) e TMDB (metadados). Permite registrar filmes assistidos, avaliações e watchlist.

## Stack específica

- Frontend: HTML/CSS/JS estático em `/frontend/`
- TMDB API: metadados de filmes (poster, sinopse, elenco)
- Letterboxd: scraping de histórico via BeautifulSoup4 + requests
- psycopg2 (síncrono)

## Banco

A conexão deve ser padronizada para `DATABASE_URL` (meta de refatoração):
```
DATABASE_URL=postgresql://postgres:postgres@localhost/fiscal
```
Atualmente usa variáveis separadas `DB_USER / DB_PASSWORD / DB_HOST / DB_NAME`.

## Desenvolvimento

```bash
poetry run python run.py  # porta 8001
```

## Regras específicas

- O scraping do Letterboxd pode quebrar se o site mudar o HTML — encapsule seletores em constantes
- Nunca armazene dados que já existem no TMDB localmente se puderem ser buscados on-demand
- `db.py` na raiz é legado SQLite — não adicione código novo lá
