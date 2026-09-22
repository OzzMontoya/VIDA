"""Gráficas Plotly del dashboard con una paleta validada y marcas consistentes.

Reglas aplicadas (guía de visualización): tonos categóricos en orden fijo por
entidad (nunca por rango), un solo eje Y por gráfica, secuencial de un solo tono,
divergente azul/rojo con gris neutro, marcas finas, rejilla recesiva, leyenda
siempre que haya 2+ series y etiquetas directas selectivas.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from dashboard.data import (
    ACTION_GROUP_ORDER, LOCATION_TYPE_LABELS, MEMORY_KIND_LABELS, NEED_LABELS, NEED_ORDER, RunData,
)

# Paleta categórica validada (referencia de la guía, modo claro), en orden fijo.
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING_NEG, DIVERGING_MID, DIVERGING_POS = "#e34948", "#f0efec", "#2a78d6"
SURFACE, TEXT, TEXT_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
STATUS_CRITICAL = "#d03b3b"

NEED_COLORS = {need: CATEGORICAL[i] for i, need in enumerate(NEED_ORDER)}
ACTION_COLORS = {group: CATEGORICAL[i] for i, group in enumerate(ACTION_GROUP_ORDER)}
LOCATION_COLORS = {label: CATEGORICAL[i] for i, label in enumerate(LOCATION_TYPE_LABELS.values())}
MEMORY_COLORS = {label: CATEGORICAL[i] for i, label in enumerate(MEMORY_KIND_LABELS.values())}
INTENT_ORDER = ["truth", "partial", "omit", "lie"]
INTENT_LABELS = {"truth": "verdad", "partial": "parcial", "omit": "omisión", "lie": "mentira"}
INTENT_COLORS = {"truth": CATEGORICAL[0], "partial": CATEGORICAL[3], "omit": CATEGORICAL[4], "lie": CATEGORICAL[7]}


def base_layout(fig: go.Figure, title: str, *, height: int = 340, x_title: str = "", y_title: str = "", legend: bool = True) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.0, "xanchor": "left", "font": {"size": 15, "color": TEXT}},
        height=height, margin={"l": 8, "r": 16, "t": 56, "b": 8},
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font={"family": "system-ui, -apple-system, Segoe UI, Roboto, sans-serif", "size": 12, "color": TEXT_2},
        hovermode="x unified", hoverlabel={"bgcolor": "#ffffff", "font": {"color": TEXT}},
        showlegend=legend,
        legend={"orientation": "h", "yanchor": "top", "y": -0.34 if x_title else -0.18, "xanchor": "left", "x": 0.0,
                "font": {"color": TEXT_2}},
        bargap=0.25,
    )
    fig.update_xaxes(title_text=x_title, showgrid=False, zeroline=False, linecolor=GRID, ticks="outside", tickcolor=GRID)
    fig.update_yaxes(title_text=y_title, gridcolor=GRID, zeroline=False, showline=False)
    return fig


def _shortage_markers(fig: go.Figure, data: RunData) -> None:
    ev = data.events
    shortages = ev[(ev["event_type"] == "world_event") & (ev["note"] == "shortage")]
    for tick in sorted(shortages["tick"].unique()):
        x = tick / data.ticks_per_day
        fig.add_vline(x=x, line={"color": TEXT_2, "width": 1, "dash": "dot"})
        fig.add_annotation(x=x, y=1.0, yref="paper", text="escasez", showarrow=False, yanchor="bottom",
                           font={"size": 10, "color": TEXT_2})


def alive_chart(alive: pd.DataFrame, data: RunData) -> go.Figure:
    fig = go.Figure(go.Scatter(x=alive["day"], y=alive["vivos"], mode="lines", line={"color": CATEGORICAL[0], "width": 2},
                               name="vivos", hovertemplate="día %{x:.1f}: %{y} vivos<extra></extra>"))
    _shortage_markers(fig, data)
    base_layout(fig, "Agentes vivos", height=260, x_title="día simulado", legend=False)
    fig.update_yaxes(range=[0, len(data.agents) + 0.5], dtick=2)
    return fig


def needs_lines(df: pd.DataFrame, data: RunData, title: str, *, mark_shortages: bool = True) -> go.Figure:
    """``df`` con columnas ``day`` y ``need_<name>`` (niveles 0..1)."""
    fig = go.Figure()
    for need in NEED_ORDER:
        col = f"need_{need}"
        if col not in df:
            continue
        label = NEED_LABELS[need]
        fig.add_trace(go.Scatter(x=df["day"], y=df[col], mode="lines", name=label,
                                 line={"color": NEED_COLORS[need], "width": 2, "shape": "spline", "smoothing": 0.6},
                                 hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>"))
    # Seis series: la identidad la lleva la leyenda (las etiquetas directas se reservan para ≤4 series).
    if mark_shortages:
        _shortage_markers(fig, data)
    base_layout(fig, title, height=380, x_title="día simulado", y_title="nivel (1 = satisfecha)")
    fig.update_yaxes(range=[0, 1.05])
    fig.add_hline(y=0.1, line={"color": STATUS_CRITICAL, "width": 1, "dash": "dash"},
                  annotation_text="⚠ umbral crítico", annotation_position="bottom right",
                  annotation_font={"size": 10, "color": STATUS_CRITICAL})
    return fig


def stacked_actions(counts: pd.DataFrame, title: str, *, horizontal: bool = False, height: int = 340, x_title: str = "", y_title: str = "") -> go.Figure:
    """``counts``: índice = categoría (agente o día), columnas = grupos de acción."""
    fig = go.Figure()
    for group in ACTION_GROUP_ORDER:
        if group not in counts:
            continue
        values = counts[group]
        args = {"y": counts.index.astype(str), "x": values, "orientation": "h"} if horizontal else {"x": counts.index.astype(str), "y": values}
        fig.add_trace(go.Bar(name=group, marker={"color": ACTION_COLORS[group], "line": {"color": SURFACE, "width": 2}},
                             hovertemplate=f"{group}: %{{{'x' if horizontal else 'y'}}}<extra></extra>", **args))
    fig.update_layout(barmode="stack")
    base_layout(fig, title, height=height, x_title=x_title, y_title=y_title)
    fig.update_layout(hovermode="y unified" if horizontal else "x unified")
    if horizontal:
        fig.update_yaxes(showgrid=False, autorange="reversed")
        fig.update_xaxes(showgrid=True, gridcolor=GRID)
    return fig


def money_line(df: pd.DataFrame, name: str) -> go.Figure:
    fig = go.Figure(go.Scatter(x=df["day"], y=df["money"], mode="lines", line={"color": CATEGORICAL[0], "width": 2},
                               name="dinero", hovertemplate="día %{x:.1f}: %{y:.2f}<extra></extra>"))
    base_layout(fig, f"Dinero de {name}", height=260, x_title="día simulado", legend=False)
    return fig


def relationship_bars(rel: pd.DataFrame, names: dict[str, str]) -> go.Figure:
    """``rel``: filas por otro agente con columnas trust, affection, familiarity."""
    fig = go.Figure()
    series = [("familiarity", "familiaridad", CATEGORICAL[0]), ("trust", "confianza", CATEGORICAL[1]), ("affection", "afecto", CATEGORICAL[2])]
    labels = [names.get(o, o) for o in rel.index]
    for col, label, color in series:
        fig.add_trace(go.Bar(name=label, x=labels, y=rel[col], marker={"color": color, "line": {"color": SURFACE, "width": 2}},
                             hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>"))
    fig.update_layout(barmode="group", bargroupgap=0.05)
    base_layout(fig, "Relaciones al final de la corrida", y_title="0 a 1")
    fig.update_yaxes(range=[0, 1.05])
    return fig


def trust_over_time(rel_history: pd.DataFrame, others: list[str], names: dict[str, str], data: RunData) -> go.Figure:
    fig = go.Figure()
    for i, other in enumerate(others[:3]):
        sub = rel_history[rel_history["to_id"] == other]
        fig.add_trace(go.Scatter(x=sub["tick"] / data.ticks_per_day, y=sub["trust"], mode="lines+markers", name=names.get(other, other),
                                 line={"color": CATEGORICAL[i], "width": 2}, marker={"size": 6},
                                 hovertemplate=f"{names.get(other, other)}: %{{y:.2f}}<extra></extra>"))
    base_layout(fig, "Confianza hacia las personas más cercanas", x_title="día simulado", y_title="confianza")
    fig.update_yaxes(range=[0, 1.05])
    return fig


def preference_bars(prefs: pd.DataFrame) -> go.Figure:
    """``prefs``: columnas subject, valence, strength (ordenadas por valencia)."""
    colors = [DIVERGING_POS if v >= 0 else DIVERGING_NEG for v in prefs["valence"]]
    fig = go.Figure(go.Bar(x=prefs["valence"], y=prefs["subject"], orientation="h",
                           marker={"color": colors, "line": {"color": SURFACE, "width": 2}},
                           customdata=prefs["strength"],
                           hovertemplate="%{y}: valencia %{x:+.2f}, fuerza %{customdata:.2f}<extra></extra>"))
    fig.add_vline(x=0, line={"color": TEXT_2, "width": 1})
    base_layout(fig, "Preferencias aprendidas (azul: busca · rojo: evita)", height=max(260, 24 * len(prefs) + 80),
                x_title="valencia", legend=False)
    fig.update_layout(hovermode="closest")
    fig.update_yaxes(showgrid=False, autorange="reversed")
    fig.update_xaxes(range=[-1.05, 1.05], showgrid=True, gridcolor=GRID)
    return fig


def knowledge_bars(initial: dict[str, float], final: dict[str, float]) -> go.Figure:
    skills = sorted(set(initial) | set(final))
    fig = go.Figure()
    fig.add_trace(go.Bar(name="inicio", x=skills, y=[initial.get(s, 0.0) for s in skills],
                         marker={"color": SEQUENTIAL_BLUE[1], "line": {"color": SURFACE, "width": 2}}, hovertemplate="inicio: %{y:.2f}<extra></extra>"))
    fig.add_trace(go.Bar(name="final", x=skills, y=[final.get(s, 0.0) for s in skills],
                         marker={"color": SEQUENTIAL_BLUE[4], "line": {"color": SURFACE, "width": 2}}, hovertemplate="final: %{y:.2f}<extra></extra>"))
    fig.update_layout(barmode="group")
    base_layout(fig, "Habilidades: inicio y final", height=260, y_title="nivel")
    fig.update_yaxes(range=[0, 1.05])
    return fig


def memory_kind_bars(memories: pd.DataFrame) -> go.Figure:
    counts = memories.groupby(["kind", "forgotten"]).size().unstack(fill_value=0)
    kinds = [k for k in MEMORY_KIND_LABELS if k in counts.index]
    labels = [MEMORY_KIND_LABELS[k] for k in kinds]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="conservadas", y=labels, x=[counts.loc[k].get(False, 0) for k in kinds], orientation="h",
                         marker={"color": SEQUENTIAL_BLUE[4], "line": {"color": SURFACE, "width": 2}}, hovertemplate="conservadas: %{x}<extra></extra>"))
    if True in counts.columns:
        fig.add_trace(go.Bar(name="olvidadas", y=labels, x=[counts.loc[k].get(True, 0) for k in kinds], orientation="h",
                             marker={"color": SEQUENTIAL_BLUE[1], "line": {"color": SURFACE, "width": 2}}, hovertemplate="olvidadas: %{x}<extra></extra>"))
    fig.update_layout(barmode="stack")
    base_layout(fig, "Memorias por tipo", height=300, x_title="registros")
    fig.update_layout(hovermode="y unified")
    fig.update_yaxes(showgrid=False, autorange="reversed")
    fig.update_xaxes(showgrid=True, gridcolor=GRID)
    return fig


def matrix_heatmap(matrix: pd.DataFrame, names: dict[str, str], title: str) -> go.Figure:
    labels = [names.get(a, a) for a in matrix.index]
    text = [[f"{v:.2f}" if pd.notna(v) else "" for v in row] for row in matrix.values]
    fig = go.Figure(go.Heatmap(
        z=matrix.values, x=labels, y=labels, text=text, texttemplate="%{text}",
        colorscale=[[0, SEQUENTIAL_BLUE[0]], [1, SEQUENTIAL_BLUE[6]]], zmin=0, zmax=1,
        xgap=2, ygap=2, colorbar={"thickness": 10, "len": 0.8, "outlinewidth": 0},
        hovertemplate="%{y} → %{x}: %{z:.2f}<extra></extra>",
    ))
    base_layout(fig, title, height=420, legend=False)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(title_text="hacia")
    fig.update_yaxes(autorange="reversed", showgrid=False, title_text="desde")
    return fig


def occupancy_area(occ: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for label in LOCATION_TYPE_LABELS.values():
        if label not in occ:
            continue
        fig.add_trace(go.Scatter(x=occ.index, y=occ[label], mode="lines", stackgroup="one", name=label,
                                 line={"width": 0.5, "color": LOCATION_COLORS[label]}, fillcolor=LOCATION_COLORS[label],
                                 hovertemplate=f"{label}: %{{y}}<extra></extra>"))
    base_layout(fig, "Dónde pasan el día los agentes (media diaria)", x_title="día simulado", y_title="agentes")
    return fig


def resources_lines(resources: pd.DataFrame, data: RunData) -> go.Figure:
    fig = go.Figure()
    series = resources.assign(key=resources["location_id"] + " · " + resources["resource"])
    for i, (key, sub) in enumerate(sorted(series.groupby("key"), key=lambda kv: kv[0])):
        if i >= 8:
            break
        fig.add_trace(go.Scatter(x=sub["tick"] / data.ticks_per_day, y=sub["stock"], mode="lines", name=key,
                                 line={"color": CATEGORICAL[i], "width": 2, "shape": "hv"},
                                 hovertemplate=f"{key}: %{{y}}<extra></extra>"))
    _shortage_markers(fig, data)
    base_layout(fig, "Existencias reales en el mundo", x_title="día simulado", y_title="unidades")
    return fig


def deception_bars(summary: pd.DataFrame, names: dict[str, str]) -> go.Figure:
    pivot = summary.pivot(index="agent_id", columns="intent", values="n").fillna(0)
    fig = go.Figure()
    for intent in INTENT_ORDER:
        if intent not in pivot:
            continue
        fig.add_trace(go.Bar(name=INTENT_LABELS[intent], x=[names.get(a, a) for a in pivot.index], y=pivot[intent],
                             marker={"color": INTENT_COLORS[intent], "line": {"color": SURFACE, "width": 2}},
                             hovertemplate=f"{INTENT_LABELS[intent]}: %{{y}}<extra></extra>"))
    fig.update_layout(barmode="stack")
    base_layout(fig, "Respuestas e información compartida, por agente", y_title="mensajes")
    return fig
