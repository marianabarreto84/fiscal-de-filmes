from fastapi import APIRouter
from pydantic import BaseModel
from backend.database import get_db, dict_cursor

router = APIRouter()


class ConfigSet(BaseModel):
    valor: str


@router.get("/{chave}")
def get_config(chave: str):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute(
                "SELECT valor, atualizado_em FROM configuracao WHERE chave = %s", (chave,)
            )
            row = cur.fetchone()
        if not row:
            return {"chave": chave, "valor": None, "atualizado_em": None}
        return {"chave": chave, "valor": row["valor"], "atualizado_em": row["atualizado_em"]}
    finally:
        conn.close()


@router.put("/{chave}")
def set_config(chave: str, body: ConfigSet):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                INSERT INTO configuracao (chave, valor, atualizado_em)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (chave) DO UPDATE SET
                    valor         = EXCLUDED.valor,
                    atualizado_em = CURRENT_TIMESTAMP
            """, (chave, body.valor))
        conn.commit()
        return {"chave": chave, "valor": body.valor}
    finally:
        conn.close()
