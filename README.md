# Dashboard de logs

Dashboard hecho en Dash (Python) para visualizar los logs guardados en PostgreSQL:
tiempo de respuesta (promedio, p95, p99), throughput (RPM) y conteo de errores 4xx/5xx.

## Requisitos

- Python 3.10+
- Acceso a la base de datos PostgreSQL con la tabla `logs`

## Instalación

```bash
python -m venv venv
venv\Scripts\activate      # en Windows
pip install -r requirements.txt
```

Crear un archivo `.env` en la raíz del proyecto (usar `.env.example` como base) con:

```
DATABASE_URL=postgresql://usuario:password@host:5432/nombre_db?sslmode=require
```

## Correr el dashboard

```bash
python app.py
```

Esto levanta el servidor en `http://127.0.0.1:8050`.

## Funcionalidad

- Selector de servicio (`svc`)
- Selector de rango de tiempo: última hora, 3 horas o 24 horas
- Selector de frecuencia de actualización automática: cada 10s o cada 60s
- Gráficas de tiempo de respuesta, throughput (RPM) y errores 4xx/5xx
