import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("Falta DATABASE_URL en el archivo .env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
