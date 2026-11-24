from dash import Dash, html, dcc, Input, Output
import plotly.graph_objects as go

from queries import listar_servicios, consultar_serie

app = Dash(__name__)
app.title = "Dashboard de logs"

try:
    servicios_disponibles = listar_servicios()
except Exception:
    servicios_disponibles = []

opciones_servicio = [{"label": "Todos los servicios", "value": "todos"}] + [
    {"label": s, "value": s} for s in servicios_disponibles
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
            ],
        ),
        dcc.Interval(id="intervalo", interval=10_000, n_intervals=0),
        dcc.Graph(id="grafico-tiempo-respuesta"),
        dcc.Graph(id="grafico-throughput"),
        dcc.Graph(id="grafico-errores"),
    ],
)


@app.callback(Output("intervalo", "interval"), Input("filtro-refresco", "value"))
def actualizar_frecuencia(valor):
    return valor


@app.callback(
    Output("grafico-tiempo-respuesta", "figure"),
    Output("grafico-throughput", "figure"),
    Output("grafico-errores", "figure"),
    Input("filtro-servicio", "value"),
    Input("filtro-rango", "value"),
    Input("intervalo", "n_intervals"),
)
def actualizar_graficos(servicio, rango, _):
    df = consultar_serie(servicio, rango)

    if df.empty:
        vacio = go.Figure()
        vacio.update_layout(title="Sin datos para el rango seleccionado")
        return vacio, vacio, vacio

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

    return fig_tiempo, fig_throughput, fig_errores


if __name__ == "__main__":
    app.run(debug=True)
