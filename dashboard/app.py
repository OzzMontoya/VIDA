"""Dashboard de VIDA: observación visual de las vidas simuladas.

    streamlit run dashboard/app.py

Lee las bases SQLite de ``data/runs/`` y muestra cuatro vistas: la corrida en
conjunto, un agente (su vida completa), la sociedad (relaciones, ocupación,
recursos, engaño) y la tabla de eventos filtrable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from dashboard import charts  # noqa: E402
from dashboard.data import (  # noqa: E402
    ACTION_GROUP_ORDER, MEMORY_KIND_LABELS, NEED_ORDER, RunData, alive_per_tick, deception_summary, lineage_frame, list_runs,
    load_run, occupancy_by_type,
)
from vida.database.repository import RunRepository  # noqa: E402
from vida.evaluation.biography import build_biography, render  # noqa: E402

st.set_page_config(page_title="VIDA · dashboard", page_icon="🌱", layout="wide")


@st.cache_data(show_spinner="Cargando corrida…")
def _load(db_path: str, mtime: float) -> RunData:
    return load_run(Path(db_path))


@st.cache_data(show_spinner=False)
def _biography_text(db_path: str, mtime: float, run_id: str, agent_id: str) -> str:
    repo = RunRepository(Path(db_path))
    try:
        return render(build_biography(repo, run_id, agent_id))
    finally:
        repo.close()


def show(fig) -> None:
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "displayModeBar": False})


NEED_COLS = [f"need_{n}" for n in NEED_ORDER]


def per_day_needs(events: pd.DataFrame, tpd: int) -> pd.DataFrame:
    """Media diaria de cada necesidad sobre todos los agentes vivos."""
    ev = events[events["event_type"] == "action"]
    df = ev.groupby("day")[NEED_COLS].mean().reset_index()
    df["day"] = df["day"] + 0.5
    return df


def smoothed_agent_needs(ev: pd.DataFrame, tpd: int) -> pd.DataFrame:
    """Media móvil de un día para que se vea la tendencia y no el ciclo comer/dormir."""
    window = max(2, tpd)
    df = ev.sort_values("tick")[["tick"] + NEED_COLS].reset_index(drop=True)
    df[NEED_COLS] = df[NEED_COLS].rolling(window, min_periods=1).mean()
    df["day"] = df["tick"] / tpd
    return df


# --- barra lateral -----------------------------------------------------------
st.sidebar.title("🌱 VIDA")
data_dir = Path(st.sidebar.text_input("Directorio de corridas", value=str(ROOT / "data" / "runs")))
runs = list_runs(data_dir)
if not runs:
    st.title("VIDA · dashboard")
    st.warning(f"No hay corridas en `{data_dir}`. Genera una con `python -m vida run --config config/default.yaml`.")
    st.stop()

run_id = st.sidebar.selectbox("Corrida", [r[0] for r in runs])
db_path = dict(runs)[run_id]
data = _load(str(db_path), db_path.stat().st_mtime)
names = data.names
ids = list(data.agents["agent_id"])
agent_options = [f"{names[a]} ({a})" for a in data.agents["agent_id"]]
agent_pick = st.sidebar.selectbox("Agente", agent_options)
agent_id = agent_pick.split("(")[-1].rstrip(")")
st.sidebar.caption(
    f"Semilla {data.meta['seed']} · {data.n_days} días · hash `{(data.meta.get('events_sha256') or '')[:12]}`\n\n"
    f"Config `{data.meta['config_hash'][:12]}` · código `{data.meta['git_sha'][:8]}`"
)

# --- cabecera ------------------------------------------------------------------
st.title(f"VIDA · corrida {run_id}")
deaths = data.agents.dropna(subset=["death_tick"])
alive_now = len(data.agents) - len(deaths)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Agentes", len(data.agents))
c2.metric("Vivos al final", alive_now, delta=None if deaths.empty else f"-{len(deaths)}", delta_color="inverse")
c3.metric("Días simulados", data.n_days)
c4.metric("Eventos", f"{int(data.meta.get('n_events') or len(data.events)):,}")
c5.metric("Memorias", f"{len(data.memories):,}")

VIEWS = ["🌍 Corrida", "🧍 Agente", "🤝 Sociedad", "🌳 Linaje", "📋 Eventos"]
# Un selector en lugar de pestañas: Streamlit renderiza todas las pestañas a la vez y la página se vuelve pesada.
view = st.sidebar.radio("Vista", VIEWS, key="view")
st.sidebar.caption("El agente elegido arriba se usa en la vista Agente y como filtro inicial en Eventos.")

# --- corrida -------------------------------------------------------------------
if view == VIEWS[0]:
    left, right = st.columns([1, 2])
    with left:
        show(charts.alive_chart(alive_per_tick(data), data))
        if not deaths.empty:
            st.markdown("**Muertes**")
            st.dataframe(
                deaths.assign(día=(deaths["death_tick"] // data.ticks_per_day), nombre=deaths["agent_id"].map(names))
                [["nombre", "agent_id", "día", "death_reason"]].rename(columns={"death_reason": "causa"}),
                hide_index=True, width="stretch",
            )
    with right:
        show(charts.needs_lines(per_day_needs(data.events, data.ticks_per_day), data, "Necesidades medias de la población"))

    actions = data.events[data.events["event_type"] == "action"]
    counts = actions.groupby(["agent_id", "action_group"]).size().unstack(fill_value=0)
    counts.index = [f"{names[a]} ({a})" for a in counts.index]
    show(charts.stacked_actions(counts.reindex(columns=[g for g in ACTION_GROUP_ORDER if g in counts]),
                                "Qué hizo cada agente durante la corrida", horizontal=True, height=420, x_title="acciones"))

    world_events = data.events[data.events["event_type"] == "world_event"]
    if not world_events.empty:
        with st.expander("Eventos del mundo (reposiciones y escaseces)"):
            st.dataframe(world_events[["day", "hour", "note", "world_delta"]].rename(
                columns={"day": "día", "hour": "hora", "note": "tipo", "world_delta": "detalle"}),
                hide_index=True, width="stretch")

# --- agente --------------------------------------------------------------------
if view == VIEWS[1]:
    final = data.final_states[agent_id]
    initial = data.initial_states[agent_id]
    ev = data.events[(data.events["agent_id"] == agent_id) & (data.events["event_type"] == "action")].copy()
    ev["day_f"] = ev["tick"] / data.ticks_per_day
    meta = data.agents.set_index("agent_id").loc[agent_id]

    st.subheader(f"{final.name} ({agent_id})")
    tags = ", ".join(final.identity.self_description_tags) or "sin rasgos destacados aún"
    death_txt = f" · murió el día {int(meta['death_tick']) // data.ticks_per_day} ({meta['death_reason']})" if pd.notna(meta["death_tick"]) else ""
    st.caption(f"Identidad observada: **{tags}** · etapa final: {final.life_stage}{death_txt}")
    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    m1.metric("Edad (días)", final.age_days(data.ticks_per_day), delta=final.age_days(data.ticks_per_day) - initial.age_days(data.ticks_per_day))
    m2.metric("Dinero", f"{final.money:.2f}", delta=f"{final.money - initial.money:+.2f}")
    m3.metric("Reputación", f"{final.reputation:.2f}")
    m4.metric("Honestidad (valor)", f"{final.identity.core_values.get('honesty', 0.5):.2f}")
    m5.metric("Memorias", len(data.memories[data.memories["agent_id"] == agent_id]))
    sm = getattr(final, "self_model", None)
    if sm is not None and sm.n:
        m6.metric("Calibración automodelo", f"{sm.calibration():.2f}", help="1 − error medio al predecir el éxito de sus propias acciones")
        m7.metric("Ventaja vs. modelo externo", f"{sm.advantage():+.3f}", help="error del modelo poblacional − error propio; positivo = se predice mejor a sí mismo")

    show(charts.needs_lines(smoothed_agent_needs(ev, data.ticks_per_day), data, f"Necesidades de {final.name} (media móvil de un día)"))

    col_a, col_b = st.columns(2)
    with col_a:
        per_day = ev.groupby(["day", "action_group"]).size().unstack(fill_value=0)
        show(charts.stacked_actions(per_day, "Acciones por día", x_title="día", y_title="acciones"))
    with col_b:
        show(charts.money_line(ev[["day_f", "money"]].rename(columns={"day_f": "day"}), final.name))

    rels = pd.DataFrame({o: r.model_dump() for o, r in final.relationships.items()}).T
    if not rels.empty:
        rels = rels[(rels["familiarity"] > 0) | (rels["trust"] != 0.5) | (rels["affection"] != 0.5)]
        rels = rels.sort_values("familiarity", ascending=False)
    col_c, col_d = st.columns(2)
    with col_c:
        if rels.empty:
            st.info("Todavía no conoce a nadie.")
        else:
            show(charts.relationship_bars(rels, names))
    with col_d:
        hist = data.relationships[data.relationships["from_id"] == agent_id]
        if not rels.empty and not hist.empty:
            show(charts.trust_over_time(hist, list(rels.index[:3]), names, data))

    col_e, col_f = st.columns(2)
    with col_e:
        prefs = pd.DataFrame([p.model_dump() for p in final.preferences.values()])
        if not prefs.empty:
            prefs = prefs[prefs["strength"] >= 0.1].sort_values("valence", ascending=False).head(14)
            show(charts.preference_bars(prefs))
    with col_f:
        show(charts.knowledge_bars({k: v.level for k, v in initial.knowledge.items()},
                                   {k: v.level for k, v in final.knowledge.items()}))
        st.markdown("**Valores (derivan con la conducta)**")
        st.dataframe(pd.DataFrame({"valor": list(final.identity.core_values), "inicio": [initial.identity.core_values.get(k, 0.5) for k in final.identity.core_values],
                                   "final": list(final.identity.core_values.values())}).round(3), hide_index=True, width="stretch")

    st.markdown("### Memoria")
    mem = data.memories[data.memories["agent_id"] == agent_id].copy()
    col_g, col_h = st.columns([1, 2])
    with col_g:
        if not mem.empty:
            show(charts.memory_kind_bars(mem))
    with col_h:
        kinds = st.multiselect("Tipos", list(MEMORY_KIND_LABELS), default=list(MEMORY_KIND_LABELS),
                               format_func=lambda k: MEMORY_KIND_LABELS[k], key="mem_kinds")
        include_forgotten = st.checkbox("Incluir olvidadas", value=False)
        mem_view = mem[mem["kind"].isin(kinds)]
        if not include_forgotten:
            mem_view = mem_view[~mem_view["forgotten"]]
        mem_view = mem_view.assign(día=mem_view["tick"] // data.ticks_per_day, tipo=mem_view["kind"].map(MEMORY_KIND_LABELS))
        st.dataframe(mem_view.sort_values(["importance", "tick"], ascending=[False, True])
                     [["día", "tipo", "content", "importance", "valence", "access_count", "forgotten"]]
                     .rename(columns={"content": "contenido", "importance": "importancia", "valence": "valencia",
                                      "access_count": "accesos", "forgotten": "olvidada"}).round(2),
                     hide_index=True, width="stretch", height=360)

    with st.expander("📜 Biografía completa (las siete preguntas de VIDA-0.1)"):
        st.code(_biography_text(str(db_path), db_path.stat().st_mtime, run_id, agent_id), language=None)

# --- sociedad ------------------------------------------------------------------
if view == VIEWS[2]:
    last_tick = data.relationships["tick"].max() if not data.relationships.empty else None
    if last_tick is not None:
        snap = data.relationships[data.relationships["tick"] == last_tick]
        col_i, col_j = st.columns(2)
        for col, metric, title in ((col_i, "trust", "Confianza (fila → columna)"), (col_j, "familiarity", "Familiaridad (fila → columna)")):
            matrix = snap.pivot(index="from_id", columns="to_id", values=metric).reindex(index=ids, columns=ids)
            with col:
                show(charts.matrix_heatmap(matrix, names, title))
    show(charts.occupancy_area(occupancy_by_type(data)))
    col_k, col_l = st.columns(2)
    with col_k:
        show(charts.resources_lines(data.resources, data))
    with col_l:
        summary = deception_summary(data)
        if summary.empty:
            st.info("Nadie pidió ni compartió información en esta corrida.")
        else:
            show(charts.deception_bars(summary, names))
            st.caption("Intención registrada por el mundo (libro de información). Los agentes no la conocen: "
                       "sólo descubren un engaño cuando actúan sobre la información y fracasan.")

# --- linaje --------------------------------------------------------------------
if view == VIEWS[3]:
    st.subheader("Generaciones y transmisión")
    show(charts.generation_bars(data.agents, data.final_states))
    births = data.events[data.events["event_type"] == "birth"]
    if births.empty:
        st.info("No hubo nacimientos en esta corrida.")
    else:
        lin = lineage_frame(data)
        if not lin.empty:
            closer = int((lin["ici_parent"] > lin["ici_others"].fillna(0)).sum())
            st.caption(f"{len(lin)} hijos · {closer} más parecidos a su progenitor que a los demás adultos de la generación anterior · "
                       f"ICI medio con progenitor {lin['ici_parent'].mean():.3f}, con otros {lin['ici_others'].mean():.3f}. "
                       "El ICI es una semejanza entre estados; no mide conciencia. Aquí no se compara la dimensión de decisiones (requiere los eventos completos: usa `vida lineage`).")
            show(charts.lineage_similarity(lin))
            st.dataframe(lin[["child_name", "parent_name", "generation", "alive", "ici_parent", "ici_others",
                              "personality_parent", "preferences_parent", "beliefs_from_parent_remaining", "trust_in_parent"]]
                         .rename(columns={"child_name": "hijo", "parent_name": "progenitor", "generation": "generación", "alive": "vivo",
                                          "ici_parent": "ICI progenitor", "ici_others": "ICI otros", "personality_parent": "personalidad",
                                          "preferences_parent": "preferencias",
                                          "beliefs_from_parent_remaining": "creencias heredadas", "trust_in_parent": "confianza en progenitor"}).round(3),
                         hide_index=True, width="stretch")
        st.markdown("**Nacimientos**")
        st.dataframe(births[["day", "agent_id", "note"]].assign(nombre=births["agent_id"].map(names))
                     .rename(columns={"day": "día", "agent_id": "id", "note": "detalle"}), hide_index=True, width="stretch")

# --- eventos -------------------------------------------------------------------
if view == VIEWS[4]:
    f1, f2, f3, f4 = st.columns([2, 2, 2, 3])
    sel_agents = f1.multiselect("Agentes", ids, default=[agent_id], format_func=lambda a: f"{names[a]} ({a})")
    sel_actions = f2.multiselect("Acciones", sorted(data.events["action"].dropna().unique()))
    sel_outcomes = f3.multiselect("Resultados", sorted(data.events["outcome_kind"].dropna().unique()))
    day_range = f4.slider("Días", 0, max(data.n_days, 1), (0, max(data.n_days, 1)))
    table = data.events[data.events["event_type"] != "world_event"]
    if sel_agents:
        table = table[table["agent_id"].isin(sel_agents)]
    if sel_actions:
        table = table[table["action"].isin(sel_actions)]
    if sel_outcomes:
        table = table[table["outcome_kind"].isin(sel_outcomes)]
    table = table[(table["day"] >= day_range[0]) & (table["day"] <= day_range[1])]
    st.caption(f"{len(table):,} eventos")
    st.dataframe(
        table[["day", "hour", "agent_id", "action", "outcome_kind", "success", "location", "target_agent", "resource",
               "valence", "money", "decision_key", "n_candidates", "note"]]
        .rename(columns={"day": "día", "hour": "hora", "agent_id": "agente", "action": "acción", "outcome_kind": "resultado",
                         "success": "éxito", "location": "lugar", "target_agent": "con", "resource": "recurso",
                         "valence": "valencia", "money": "dinero", "decision_key": "elección", "n_candidates": "opciones", "note": "nota"})
        .round(2),
        hide_index=True, width="stretch", height=520,
    )
