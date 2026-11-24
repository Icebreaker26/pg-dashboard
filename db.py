# Conexion a la base de datos de Postgres.
# El resto del proyecto importa "engine" desde aqui para correr consultas,
# asi solo hay un lugar donde se arma la conexion.

import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Lee el archivo .env (si existe) y carga sus variables como variables de entorno
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("Falta DATABASE_URL en el archivo .env")

# pool_pre_ping=True hace que SQLAlchemy chequee la conexion antes de usarla,
# util porque esta DB esta en Render y se puede desconectar por inactividad
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
