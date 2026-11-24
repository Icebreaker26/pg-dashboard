# Todas las consultas SQL que usa el dashboard viven aca.
# La idea es que app.py nunca escriba SQL directamente, solo llame estas funciones
# y reciba de vuelta un DataFrame de pandas listo para graficar.

import pandas as pd
from sqlalchemy import text
from db import engine

# Rangos de tiempo que ofrece el selector del dashboard, en horas
RANGOS_HORAS = {"1h": 1, "3h": 3, "24h": 24}


def bucket_para_rango(rango):
    # Para 1h y 3h se agrupa por minuto (mas detalle), para 24h por hora
    # (si agrupara por minuto en 24h serian 1440 puntos, demasiado para una grafica)
    return "minute" if rango in ("1h", "3h") else "hour"


def minutos_por_bucket(rango):
    # Sirve para convertir "total de requests por bucket" en RPM (requests por minuto)
    return 1 if bucket_para_rango(rango) == "minute" else 60


def listar_servicios():
    # Trae los valores distintos de la columna svc, para llenar el dropdown de servicios
    sql = text("SELECT DISTINCT svc FROM logs ORDER BY svc")
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    return df["svc"].tolist()


def listar_urls_top(limite=15):
    # No traemos todas las URLs distintas porque pueden ser muchas (ej: /orders/{id}
    # con ids distintos). Mostramos solo las mas frecuentes para que el dropdown sea usable.
    sql = text("""
        SELECT url, count(*) AS total
        FROM logs
        GROUP BY url
        ORDER BY total DESC
        LIMIT :limite
    """)
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params={"limite": limite})
    return df["url"].tolist()


def filtros_comunes(servicio, url):
    # Arma el pedazo de WHERE y los parametros para filtrar por servicio y/o url.
    # Se usa tanto en consultar_serie como en consultar_errores_recientes para no
    # repetir la misma logica de filtros en los dos lados.
    condiciones = []
    params = {}

    if servicio and servicio != "todos":
        condiciones.append("svc = :servicio")
        params["servicio"] = servicio

    if url and url != "todas":
        condiciones.append("url = :url")
        params["url"] = url

    filtro_sql = ("AND " + " AND ".join(condiciones)) if condiciones else ""
    return filtro_sql, params


def consultar_serie(servicio, url, rango):
    # Consulta principal del dashboard: agrupa los logs en buckets de tiempo y calcula,
    # por cada bucket, el promedio de duracion, p95, p99 y conteo de errores 4xx/5xx.
    # De aca salen las 3 graficas (tiempo de respuesta, throughput y errores).
    horas = RANGOS_HORAS[rango]
    bucket = bucket_para_rango(rango)
    filtro_sql, params = filtros_comunes(servicio, url)

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
        {filtro_sql}
        GROUP BY momento
        ORDER BY momento
    """)

    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params=params)

    if df.empty:
        return df

    # rpm = requests por minuto. Si el bucket ya es de un minuto, rpm = total.
    # Si el bucket es de una hora, dividimos el total entre 60.
    df["rpm"] = df["total"] / minutos_por_bucket(rango)
    return df


def consultar_errores_recientes(servicio, url, rango, limite=20):
    # Trae los ultimos N logs con error (status >= 400) dentro del rango y filtros
    # seleccionados, para mostrarlos en la tabla "Ultimos errores" del dashboard.
    horas = RANGOS_HORAS[rango]
    filtro_sql, params = filtros_comunes(servicio, url)
    params["limite"] = limite

    sql = text(f"""
        SELECT ts, svc, url, http_method, status_code, duration
        FROM logs
        WHERE ts >= now() - interval '{horas} hours'
        AND status_code >= 400
        {filtro_sql}
        ORDER BY ts DESC
        LIMIT :limite
    """)

    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params=params)

    return df
