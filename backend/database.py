import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()


def get_db():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        dbname=os.getenv("DB_NAME", "fiscal"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        options="-c search_path=filmes",
    )
    conn.autocommit = False
    return conn


def dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
