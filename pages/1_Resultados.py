"""Resultados — se actualizan AUTOMÁTICAMENTE desde ESPN (Wikipedia de reserva).

La sincronización es app-wide: ocurre al abrir cualquier página (ver
``ui_common.get_results``). Aquí se muestra el estado y se permite forzar una
actualización inmediata.
"""

from __future__ import annotations

import streamlit as st

from ui_common import configure_page, force_resync, get_data, get_results

configure_page()
st.title("📝 Resultados")

data = get_data()
results = get_results()  # dispara la sincronización automática (cacheada 15 min)

played = sum(1 for m in data.matches if results.has(m.number))
c1, c2 = st.columns(2)
c1.metric("Partidos con resultado", f"{played} / 104")
c2.metric("Pendientes", 104 - played)

st.caption(
    "Los resultados se actualizan **automáticamente** desde ESPN (y Wikipedia como "
    "reserva) al abrir cualquier sección de la app, con caché de 15 minutos. No hay "
    "que introducir ni sincronizar nada a mano."
)

if st.button("🔄 Forzar actualización ahora"):
    force_resync()
    st.rerun()

if played == 0:
    st.info("Aún no hay partidos disputados. Se recogerán automáticamente en cuanto se jueguen.",
            icon="🗓️")
