"""Banderas de cada selección como **imágenes** (no emoji).

Windows no renderiza los emoji de bandera de país (muestra el código ISO de dos
letras), así que servimos imágenes de https://flagcdn.com por código ISO 3166-1
alfa-2; Inglaterra y Escocia usan los códigos de subdivisión ``gb-eng``/``gb-sct``.

Uso:
* :func:`flag_url` → URL de la imagen (para ``st.column_config.ImageColumn``).
* :func:`flag_img` → etiqueta ``<img>`` lista para HTML (``st.markdown``).

Los nombres deben coincidir EXACTAMENTE con los de la tabla de equipos del Excel.
"""

from __future__ import annotations

# Selección -> código de flagcdn (ISO alfa-2 en minúsculas; subdivisiones para UK)
_CODE = {
    "México": "mx", "Sudáfrica": "za", "Corea del Sur": "kr", "República Checa": "cz",
    "Canadá": "ca", "Bosnia y Herzegovina": "ba", "Catar": "qa", "Suiza": "ch",
    "Brasil": "br", "Marruecos": "ma", "Haití": "ht", "Escocia": "gb-sct",
    "Estados Unidos": "us", "Paraguay": "py", "Australia": "au", "Turquía": "tr",
    "Alemania": "de", "Curazao": "cw", "Costa de Marfil": "ci", "Ecuador": "ec",
    "Países Bajos": "nl", "Japón": "jp", "Suecia": "se", "Túnez": "tn",
    "Bélgica": "be", "Egipto": "eg", "Irán": "ir", "Nueva Zelanda": "nz",
    "España": "es", "Cabo Verde": "cv", "Arabia Saudita": "sa", "Uruguay": "uy",
    "Francia": "fr", "Senegal": "sn", "Irak": "iq", "Noruega": "no",
    "Argentina": "ar", "Argelia": "dz", "Austria": "at", "Jordania": "jo",
    "Portugal": "pt", "RD Congo": "cd", "Uzbekistán": "uz", "Colombia": "co",
    "Inglaterra": "gb-eng", "Croacia": "hr", "Ghana": "gh", "Panamá": "pa",
}


def flag_url(name: str | None, width: int = 40) -> str:
    """URL de la imagen de bandera (``""`` si no se reconoce la selección)."""
    code = _CODE.get(name or "")
    return f"https://flagcdn.com/w{width}/{code}.png" if code else ""


def flag_img(name: str | None, height: int = 13) -> str:
    """Etiqueta ``<img>`` de la bandera para incrustar en HTML.

    Fija ancho y alto (relación 4:3) para que TODAS las banderas ocupen el mismo
    espacio; el recorte uniforme lo aplica ``object-fit: cover`` en el CSS.
    """
    url = flag_url(name)
    if not url:
        return ""
    width = round(height * 4 / 3)
    return (f'<img class="fl-img" src="{url}" width="{width}" height="{height}" '
            f'alt="{name}" loading="lazy">')
