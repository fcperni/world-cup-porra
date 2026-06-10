"""Banderas (emoji) de cada selección del Mundial 2026.

Se generan a partir del código ISO 3166-1 alfa-2 mediante los *regional
indicator symbols*; Inglaterra y Escocia usan los emojis de subdivisión
(secuencias de etiquetas), que renderizan en navegadores modernos.

Los nombres deben coincidir EXACTAMENTE con los de la tabla de equipos del Excel.
"""

from __future__ import annotations

# Selección -> código ISO alfa-2 (o None si usa emoji especial)
_ISO = {
    "México": "MX", "Sudáfrica": "ZA", "Corea del Sur": "KR", "República Checa": "CZ",
    "Canadá": "CA", "Bosnia y Herzegovina": "BA", "Catar": "QA", "Suiza": "CH",
    "Brasil": "BR", "Marruecos": "MA", "Haití": "HT",
    "Estados Unidos": "US", "Paraguay": "PY", "Australia": "AU", "Turquía": "TR",
    "Alemania": "DE", "Curazao": "CW", "Costa de Marfil": "CI", "Ecuador": "EC",
    "Países Bajos": "NL", "Japón": "JP", "Suecia": "SE", "Túnez": "TN",
    "Bélgica": "BE", "Egipto": "EG", "Irán": "IR", "Nueva Zelanda": "NZ",
    "España": "ES", "Cabo Verde": "CV", "Arabia Saudita": "SA", "Uruguay": "UY",
    "Francia": "FR", "Senegal": "SN", "Irak": "IQ", "Noruega": "NO",
    "Argentina": "AR", "Argelia": "DZ", "Austria": "AT", "Jordania": "JO",
    "Portugal": "PT", "RD Congo": "CD", "Uzbekistán": "UZ", "Colombia": "CO",
    "Croacia": "HR", "Ghana": "GH", "Panamá": "PA",
}

# Subdivisiones del Reino Unido (secuencias de etiquetas Unicode).
_SPECIAL = {
    "Inglaterra": "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F",
    "Escocia": "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F",
}


def _iso_to_emoji(code: str) -> str:
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


FLAGS: dict[str, str] = {name: _iso_to_emoji(code) for name, code in _ISO.items()}
FLAGS.update(_SPECIAL)


def flag(name: str | None) -> str:
    """Emoji de bandera de una selección, o cadena vacía si no se reconoce."""
    return FLAGS.get(name or "", "")


def with_flag(name: str | None, sep: str = " ") -> str:
    """``"Francia"`` -> ``"🇫🇷 Francia"`` (sin bandera si no se reconoce)."""
    if not name:
        return name or ""
    f = FLAGS.get(name, "")
    return f"{f}{sep}{name}" if f else name
