import pandas as pd
from sqlalchemy import text
from db import engine

RANGOS_HORAS = {"1h": 1, "3h": 3, "24h": 24}


def bucket_para_rango(rango):
    return "minute" if rango in ("1h", "3h") else "hour"


def minutos_por_bucket(rango):
    return 1 if bucket_para_rango(rango) == "minute" else 60


def listar_servicios():
    sql = text("SELECT DISTINCT svc FROM logs ORDER BY svc")
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    return df["svc"].tolist()


def consultar_serie(servicio, rango):
    horas = RANGOS_HORAS[rango]
    bucket = bucket_para_rango(rango)

    filtro_servicio = "AND svc = :servicio" if servicio and servicio != "todos" else ""

    sql = text(f"""
        SELECT
            date_trunc('{bucket}', ts) AS momento,
            count(*) AS total,
            avg(duration) AS duracion_prom,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY duration) AS p95,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY duration) AS p99,
            count(*) FILTER (WHERE status_code BETWEEN 400 AND 499) AS errores_4xx,
            count(*) FILTER (WHERE status_code >= 500) AS errores_5xx
        FROM logs
        WHERE ts >= now() - interval '{horas} hours'
        {filtro_servicio}
        GROUP BY momento
        ORDER BY momento
    """)

    params = {"servicio": servicio} if filtro_servicio else {}

    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params=params)

    if df.empty:
        return df

    df["rpm"] = df["total"] / minutos_por_bucket(rango)
    return df
