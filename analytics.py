"""Analítica de uso propia y **privada**.

Registra visitas en una base de datos Postgres y se consulta desde la página
``Admin`` (protegida por contraseña). Se activa solo si hay una conexión
configurada en ``st.secrets`` (``[connections.analytics]``); **sin** esa config,
todas las funciones son no-op y la app funciona igual, sin analítica.

Privacidad: solo se guarda un id de sesión **aleatorio** (no identifica a nadie),
la página vista y un detalle opcional (nº de partido o jugador consultado). No se
registra IP, user-agent ni dato personal alguno.

Diseño: una fila por *(sesión, página, detalle)* la primera vez que ocurre en la
sesión (deduplicado en ``st.session_state``), de modo que los múltiples reruns de
Streamlit —incluido el autorrefresco del directo— no inflan las cifras.
"""

from __future__ import annotations

import uuid

import streamlit as st

TABLE = "app_events"


def _enabled() -> bool:
    """True si hay una conexión de analítica configurada en secrets."""
    try:
        return "analytics" in st.secrets["connections"]
    except Exception:  # noqa: BLE001 — sin secrets.toml o sin sección [connections]
        return False


def connection():
    """Devuelve la conexión SQL de analítica, o ``None`` si no está configurada."""
    if not _enabled():
        return None
    try:
        return st.connection("analytics", type="sql")
    except Exception:  # noqa: BLE001
        return None


def session_id() -> str:
    """Id aleatorio y estable durante la sesión del navegador."""
    if "_sid" not in st.session_state:
        st.session_state["_sid"] = uuid.uuid4().hex
    return st.session_state["_sid"]


def ensure_schema(conn) -> None:
    """Crea la tabla de eventos si no existe (una vez por sesión)."""
    if st.session_state.get("_schema_ok"):
        return
    from sqlalchemy import text

    with conn.session as s:
        s.execute(text(
            f"CREATE TABLE IF NOT EXISTS {TABLE} ("
            "  id BIGSERIAL PRIMARY KEY,"
            "  ts TIMESTAMPTZ NOT NULL DEFAULT now(),"
            "  session_id TEXT NOT NULL,"
            "  page TEXT NOT NULL,"
            "  detail TEXT"
            ")"
        ))
        s.commit()
    st.session_state["_schema_ok"] = True


def track(page: str, detail: str | None = None) -> None:
    """Registra una visita a ``page`` (con ``detail`` opcional). No-op si no hay BD.

    Deduplica por *(página, detalle)* dentro de la sesión: solo cuenta la primera
    vez que se ve cada cosa, así los reruns no disparan las cifras. Cualquier fallo
    se traga en silencio: la analítica nunca debe romper la app.
    """
    conn = connection()
    if conn is None:
        return
    key = (page, detail)
    seen = st.session_state.setdefault("_tracked", set())
    if key in seen:
        return
    seen.add(key)
    try:
        from sqlalchemy import text

        ensure_schema(conn)
        with conn.session as s:
            s.execute(
                text(f"INSERT INTO {TABLE} (session_id, page, detail) "
                     "VALUES (:sid, :page, :detail)"),
                {"sid": session_id(), "page": page, "detail": detail},
            )
            s.commit()
    except Exception:  # noqa: BLE001 — si falla, permite reintentar más tarde
        seen.discard(key)
