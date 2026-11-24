from dash import Dash, html, dcc, dash_table, Input, Output, State
import plotly.graph_objects as go

from queries import (
    listar_servicios,
    listar_urls_top,
    consultar_serie,
    consultar_errores_recientes,
)

app = Dash(__name__)
app.title = "Dashboard de logs"

try:
    servicios_disponibles = listar_servicios()
    urls_disponibles = listar_urls_top()
except Exception:
    servicios_disponibles = []
    urls_disponibles = []

opciones_servicio = [{"label": "Todos los servicios", "value": "todos"}] + [
    {"label": s, "value": s} for s in servicios_disponibles
]

opciones_url = [{"label": "Todas las URLs", "value": "todas"}] + [
    {"label": u, "value": u} for u in urls_disponibles
]

opciones_rango = [
    {"label": "Última hora", "value": "1h"},
    {"label": "Últimas 3 horas", "value": "3h"},
    {"label": "Últimas 24 horas", "value": "24h"},
]

opciones_refresco = [
    {"label": "Cada 10 segundos", "value": 10_000},
    {"label": "Cada 60 segundos", "value": 60_000},
]


def tarjeta_kpi(id_valor, titulo):
    return html.Div(
        className="kpi",
        children=[
            html.Div(titulo, className="kpi-titulo"),
            html.Div("-", id=id_valor, className="kpi-valor"),
        ],
    )


app.layout = html.Div(
    className="contenedor",
    children=[
        html.H2("Dashboard de logs"),
        html.Div(
            className="controles",
            children=[
                dcc.Dropdown(
                    id="filtro-servicio",
                    options=opciones_servicio,
                    value="todos",
                    clearable=False,
                    style={"width": "220px"},
                ),
                dcc.Dropdown(
                    id="filtro-url",
                    options=opciones_url,
                    value="todas",
                    clearable=False,
                    style={"width": "260px"},
                ),
                dcc.Dropdown(
                    id="filtro-rango",
                    options=opciones_rango,
                    value="1h",
                    clearable=False,
                    style={"width": "180px"},
                ),
                dcc.Dropdown(
                    id="filtro-refresco",
                    options=opciones_refresco,
                    value=10_000,
                    clearable=False,
                    style={"width": "180px"},
                ),
                html.Button("Descargar CSV", id="boton-descargar"),
                dcc.Download(id="descarga-csv"),
            ],
        ),
        dcc.Interval(id="intervalo", interval=10_000, n_intervals=0),
        html.Div(
            className="kpis",
            children=[
                tarjeta_kpi("kpi-total", "Requests en el rango"),
                tarjeta_kpi("kpi-error-rate", "% de errores"),
                tarjeta_kpi("kpi-p95", "p95 actual (ms)"),
                tarjeta_kpi("kpi-rpm", "RPM actual"),
            ],
        ),
        dcc.Graph(id="grafico-tiempo-respuesta"),
        dcc.Graph(id="grafico-throughput"),
        dcc.Graph(id="grafico-errores"),
        html.H4("Últimos errores"),
        dash_table.DataTable(
            id="tabla-errores",
            columns=[
                {"name": "Hora", "id": "ts"},
                {"name": "Servicio", "id": "svc"},
                {"name": "URL", "id": "url"},
                {"name": "Método", "id": "http_method"},
                {"name": "Status", "id": "status_code"},
                {"name": "Duración (ms)", "id": "duration"},
            ],
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px"},
        ),
    ],
)


@app.callback(Output("intervalo", "interval"), Input("filtro-refresco", "value"))
def actualizar_frecuencia(valor):
    return valor


@app.callback(
    Output("grafico-tiempo-respuesta", "figure"),
    Output("grafico-throughput", "figure"),
    Output("grafico-errores", "figure"),
    Output("kpi-total", "children"),
    Output("kpi-error-rate", "children"),
    Output("kpi-p95", "children"),
    Output("kpi-rpm", "children"),
    Output("tabla-errores", "data"),
    Input("filtro-servicio", "value"),
    Input("filtro-url", "value"),
    Input("filtro-rango", "value"),
    Input("intervalo", "n_intervals"),
)
def actualizar_dashboard(servicio, url, rango, _):
    df = consultar_serie(servicio, url, rango)
    errores = consultar_errores_recientes(servicio, url, rango)
    datos_tabla = errores.to_dict("records")

    if df.empty:
        vacio = go.Figure()
        vacio.update_layout(title="Sin datos para el rango seleccionado")
        return vacio, vacio, vacio, "0", "0%", "-", "-", datos_tabla

    fig_tiempo = go.Figure()
    fig_tiempo.add_trace(go.Scatter(x=df["momento"], y=df["duracion_prom"], name="Promedio"))
    fig_tiempo.add_trace(go.Scatter(x=df["momento"], y=df["p95"], name="p95"))
    fig_tiempo.add_trace(go.Scatter(x=df["momento"], y=df["p99"], name="p99"))
    fig_tiempo.update_layout(title="Tiempo de respuesta (ms)", margin=dict(t=40))

    fig_throughput = go.Figure()
    fig_throughput.add_trace(go.Bar(x=df["momento"], y=df["rpm"], name="RPM"))
    fig_throughput.update_layout(title="Throughput (requests por minuto)", margin=dict(t=40))

    fig_errores = go.Figure()
    fig_errores.add_trace(go.Bar(x=df["momento"], y=df["errores_4xx"], name="4xx"))
    fig_errores.add_trace(go.Bar(x=df["momento"], y=df["errores_5xx"], name="5xx"))
    fig_errores.update_layout(barmode="stack", title="Errores", margin=dict(t=40))

    total_requests = int(df["total"].sum())
    total_errores = int((df["errores_4xx"] + df["errores_5xx"]).sum())
    tasa_error = (total_errores / total_requests * 100) if total_requests else 0
    p95_actual = round(df["p95"].iloc[-1], 1)
    rpm_actual = round(df["rpm"].iloc[-1], 1)

    return (
        fig_tiempo,
        fig_throughput,
        fig_errores,
        f"{total_requests}",
        f"{tasa_error:.1f}%",
        f"{p95_actual}",
        f"{rpm_actual}",
        datos_tabla,
    )


@app.callback(
    Output("descarga-csv", "data"),
    Input("boton-descargar", "n_clicks"),
    State("filtro-servicio", "value"),
    State("filtro-url", "value"),
    State("filtro-rango", "value"),
    prevent_initial_call=True,
)
def descargar_csv(n_clicks, servicio, url, rango):
    df = consultar_serie(servicio, url, rango)
    return dcc.send_data_frame(df.to_csv, "metricas_logs.csv", index=False)


if __name__ == "__main__":
    app.run(debug=True)
