"""Admin — analítica de uso **privada** (solo el propietario).

Oculta del menú lateral (ver CSS en ``theme.py``) y protegida por contraseña
(``st.secrets['admin']['password']``). Lee los eventos que registra
:mod:`analytics` en Postgres y los resume en métricas y gráficas.
"""

from __future__ import annotations

import streamlit as st

from page_guard import safe_page

with safe_page():
    import pandas as pd

    import analytics
    from ui_common import configure_page, get_data, proper_name

    configure_page()
    st.title("🔒 Admin · Analítica de uso")

    # ----------------------------------------------------------------- gate
    def _password():
        try:
            return st.secrets["admin"]["password"]
        except Exception:  # noqa: BLE001
            return None

    pw = _password()
    if pw is None:
        st.warning("Configura `st.secrets['admin']['password']` para habilitar esta página.")
        st.stop()

    if not st.session_state.get("_admin_ok"):
        with st.form("login"):
            entered = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                if entered == pw:
                    st.session_state["_admin_ok"] = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
        st.stop()

    conn = analytics.connection()
    if conn is None:
        st.warning("No hay base de datos de analítica configurada "
                   "(`[connections.analytics]` en secrets).")
        st.stop()

    # crea la tabla si aún no existe (primera visita) para que las consultas no fallen
    analytics.ensure_schema(conn)

    c_refresh, _ = st.columns([1, 4])
    if c_refresh.button("🔄 Actualizar"):
        st.cache_data.clear()

    T = analytics.TABLE
    TTL = 60

    # ----------------------------------------------------------------- métricas
    tot = conn.query(
        f"SELECT count(*) AS visitas, count(DISTINCT session_id) AS sesiones, "
        f"count(*) FILTER (WHERE ts >= now() - interval '7 days') AS visitas_7d, "
        f"count(DISTINCT session_id) FILTER (WHERE ts::date = current_date) AS sesiones_hoy "
        f"FROM {T}", ttl=TTL)
    r = tot.iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Visitas totales", int(r.visitas))
    m2.metric("Sesiones únicas", int(r.sesiones))
    m3.metric("Visitas (7 días)", int(r.visitas_7d))
    m4.metric("Sesiones hoy", int(r.sesiones_hoy))

    if int(r.visitas) == 0:
        st.info("Aún no hay visitas registradas.", icon="📊")
        st.stop()

    # ----------------------------------------------------------------- por día
    st.subheader("Actividad por día")
    by_day = conn.query(
        f"SELECT ts::date AS día, count(*) AS visitas, "
        f"count(DISTINCT session_id) AS sesiones FROM {T} GROUP BY 1 ORDER BY 1", ttl=TTL)
    st.line_chart(by_day.set_index("día"))

    # ----------------------------------------------------------------- por página
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Páginas más vistas")
        by_page = conn.query(
            f"SELECT page AS página, count(*) AS visitas FROM {T} "
            f"GROUP BY 1 ORDER BY 2 DESC", ttl=TTL)
        st.bar_chart(by_page.set_index("página"))

    with col_b:
        st.subheader("Jugadores más consultados")
        players = conn.query(
            f"SELECT detail AS jugador, count(*) AS visitas FROM {T} "
            f"WHERE page = 'Jugador' AND detail IS NOT NULL "
            f"GROUP BY 1 ORDER BY 2 DESC LIMIT 15", ttl=TTL)
        if players.empty:
            st.caption("Sin datos todavía.")
        else:
            players["jugador"] = players["jugador"].map(proper_name)
            st.dataframe(players, hide_index=True, width="stretch")

    # ----------------------------------------------------------------- partidos
    st.subheader("Partidos más consultados")
    matches = conn.query(
        f"SELECT detail AS num, count(*) AS visitas FROM {T} "
        f"WHERE page = 'Predicciones del partido' AND detail IS NOT NULL "
        f"GROUP BY 1 ORDER BY 2 DESC LIMIT 15", ttl=TTL)
    if matches.empty:
        st.caption("Sin datos todavía.")
    else:
        data = get_data()
        names = {str(m.number): f"{m.home} – {m.away}" if m.home else f"Partido {m.number}"
                 for m in data.matches}
        matches["partido"] = matches["num"].map(lambda n: names.get(str(n), f"Partido {n}"))
        st.dataframe(matches[["partido", "visitas"]], hide_index=True, width="stretch")

    # ----------------------------------------------------------------- recientes
    with st.expander("Últimos eventos"):
        recent = conn.query(
            f"SELECT ts AS cuándo, page AS página, detail AS detalle FROM {T} "
            f"ORDER BY ts DESC LIMIT 50", ttl=TTL)
        st.dataframe(recent, hide_index=True, width="stretch")

    st.caption("Privado: solo se registra un id de sesión aleatorio, la página y un "
               "detalle opcional. Sin IP ni datos personales.")
