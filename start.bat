@echo off
echo Iniciando Fiscal de Filmes...
echo Servidor: http://localhost:8001
echo.
poetry run uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
