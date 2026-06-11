"""Ejecuta el cuerpo de una página Streamlit de forma resiliente.

Envuelve la carga de dependencias y el render de cada página en un único
``with safe_page(): ...``. Si algo falla —un ``ImportError`` por una dependencia
que no instaló bien en Streamlit Cloud, un fallo al leer el Excel, un error de
scraping, etc.— la app no muestra el "stack trace rojo" críptico (que además
Cloud **redacta**), sino un mensaje amigable.

Detalle clave: Streamlit oculta el texto de las excepciones **no capturadas**
para no filtrar datos, pero NO censura el contenido que renderizamos nosotros.
Al capturar la excepción y pintar el traceback con ``st.code`` dentro de un
desplegable, recuperamos el error real para poder diagnosticar la causa de
fondo desde la propia interfaz.

Este módulo solo depende de ``streamlit`` (nada de ``porra``), de modo que
sigue funcionando aunque el resto de la app no se pueda importar.
"""

from __future__ import annotations

import contextlib
import traceback

import streamlit as st

APP_TITLE = "Pa porra la mía"
APP_ICON = "🍆"


@contextlib.contextmanager
def safe_page():
    """Context manager que blinda el cuerpo de una página.

    Uso::

        import streamlit as st
        from page_guard import safe_page

        with safe_page():
            from ui_common import configure_page, get_data, get_results
            configure_page()
            ...  # resto de la página
    """
    # Aseguramos una configuración de página mínima incluso si los imports de la
    # app fallan (``configure_page`` no llegará a ejecutarse en ese caso).
    try:
        st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
    except Exception:
        pass  # ya configurada, o se reconfigurará dentro del bloque

    # Nota: ``st.stop()`` y ``st.rerun()`` lanzan excepciones de control de flujo
    # que heredan de ``BaseException`` (no de ``Exception``), así que el ``except``
    # de abajo no las captura y se propagan correctamente.
    try:
        yield
    except Exception as exc:  # noqa: BLE001 — cualquier fallo de carga/render
        st.error(
            "⚠️ No se ha podido cargar esta sección. Suele ser algo temporal "
            "(el despliegue o una fuente externa); prueba a **recargar** en unos "
            "segundos. Si persiste, revisa los detalles técnicos.",
            icon="⚠️",
        )
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        with st.expander("Detalles técnicos"):
            st.code(tb, language="text")
        st.stop()
