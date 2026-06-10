"""Persistencia de resultados en una tabla de Snowflake (Streamlit in Snowflake).

En SiS la app corre desde un *stage* de solo lectura, así que no puede guardar
``results.json`` en disco. Guardamos el estado completo (mismo formato que el
JSON) como un único VARIANT en la tabla ``PORRA_RESULTS`` (fila ``id = 1``),
leyéndola/escribiéndola con la sesión de Snowpark activa.

Monousuario: una sola fila basta. El nombre de tabla se resuelve en el esquema
actual de la app (donde se crea el objeto STREAMLIT).
"""

from __future__ import annotations

import json

from .results_store import HONOR_KEYS, Results, from_dict, to_dict

TABLE = "PORRA_RESULTS"


def ensure_table(session) -> None:
    session.sql(f"CREATE TABLE IF NOT EXISTS {TABLE} (id INT PRIMARY KEY, payload VARIANT)").collect()


def load_results_sf(session) -> Results:
    """Lee el estado desde Snowflake; vacío si no hay fila aún."""
    ensure_table(session)
    rows = session.sql(f"SELECT payload FROM {TABLE} WHERE id = 1").collect()
    if not rows or rows[0][0] is None:
        return Results(honor={k: None for k in HONOR_KEYS})
    payload = rows[0][0]
    raw = json.loads(payload) if isinstance(payload, str) else payload
    return from_dict(raw)


def save_results_sf(session, results: Results) -> None:
    """Escribe (upsert) el estado completo en la fila id = 1."""
    ensure_table(session)
    payload = json.dumps(to_dict(results), ensure_ascii=False).replace("'", "''")
    session.sql(
        f"MERGE INTO {TABLE} t USING (SELECT 1 AS id) s ON t.id = s.id "
        f"WHEN MATCHED THEN UPDATE SET payload = PARSE_JSON('{payload}') "
        f"WHEN NOT MATCHED THEN INSERT (id, payload) VALUES (1, PARSE_JSON('{payload}'))"
    ).collect()
