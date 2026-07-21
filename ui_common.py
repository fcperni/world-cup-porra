"""Utilidades compartidas por las páginas Streamlit de "Pa porra la mía".

Mantiene el paquete ``porra`` libre de dependencias de Streamlit: aquí viven
los envoltorios cacheados y el estado de sesión.
"""

from __future__ import annotations

import streamlit as st

from porra.competitions import Competition, DEFAULT_ID, get_competition
from porra.github_sync import commit_file
from porra.models import Phase, TournamentData
from porra.results_store import Results, load_results, save_results, to_dict

import json

APP_TITLE = "Pa porra la mía"
# No existe un emoji fiel a la porra del as de bastos (la maza nudosa de la baraja
# española), así que usamos la berenjena como pidió el usuario.
APP_ICON = "🍆"

PHASE_LABELS = {
    Phase.GROUPS: "Fase de grupos",
    Phase.R32: "Dieciseisavos",
    Phase.R16: "Octavos",
    Phase.QF: "Cuartos",
    Phase.SF: "Semifinales",
    Phase.THIRD: "3er y 4º puesto",
    Phase.FINAL: "Final",
}

# Etiquetas legibles del cuadro de honor (clave interna -> texto a mostrar).
HONOR_LABELS = {
    "campeon": "Campeón", "subcampeon": "Subcampeón", "tercero": "3er puesto",
    "bota_oro": "Bota de Oro", "bota_plata": "Bota de Plata", "bota_bronce": "Bota de Bronce",
    "balon_oro": "Balón de Oro", "balon_plata": "Balón de Plata", "balon_bronce": "Balón de Bronce",
}


SESSION_KEY = "competition_id"


def active_id() -> str:
    """Id de la competición activa (default si no se ha elegido ninguna)."""
    return st.session_state.get(SESSION_KEY) or DEFAULT_ID


def active_competition() -> Competition:
    """Competición activa (:class:`~porra.competitions.Competition`)."""
    return get_competition(active_id())


def set_competition(comp_id: str) -> None:
    """Fija la competición activa en el estado de sesión."""
    st.session_state[SESSION_KEY] = comp_id


def has_selection() -> bool:
    """¿El usuario ha elegido explícitamente una competición?"""
    return bool(st.session_state.get(SESSION_KEY))


@st.cache_data(show_spinner="Cargando competición…")
def _load_data(comp_id: str) -> TournamentData:
    """Carga (cacheada por competición) los datos del torneo vía su loader."""
    return get_competition(comp_id).loader()


def get_data() -> TournamentData:
    """Datos de la competición activa (cacheados, inmutables durante la sesión)."""
    return _load_data(active_id())


def require_porra(data: TournamentData) -> None:
    """Detiene la página con un aviso si la competición aún no tiene participantes.

    Las páginas que dependen de las predicciones (clasificación, jugador, etc.) no
    tienen nada que mostrar para un torneo sin porra todavía (p.ej. la Euro 2028):
    en vez de romper, invitan a explorar el calendario y los grupos.
    """
    if not data.players:
        comp = active_competition()
        st.info(
            f"La porra de la **{comp.name}** aún no tiene participantes ni predicciones. "
            "Cuando haya sorteo y pronósticos, esta sección cobrará vida. Mientras, echa un "
            "vistazo al **Calendario y Resultados** y a **Grupos y Brackets**.",
            icon="🗓️",
        )
        st.stop()


def _sf_session():
    """Sesión Snowpark activa si la app corre en Streamlit-in-Snowflake, o None."""
    try:
        from snowflake.snowpark.context import get_active_session
        return get_active_session()
    except Exception:
        return None


def get_results() -> Results:
    """Resultados de la competición activa, con sincronización automática app-wide.

    Cada competición persiste por separado (``data/results.json`` para el Mundial,
    ``data/results_euro2028.json`` para la Euro…). Al abrir **cualquier** página,
    incorpora los marcadores nuevos scrapeados (caché de 15 min), de modo que
    todas las secciones reflejan los marcadores sin intervención manual.
    """
    comp = active_competition()
    key = f"results::{comp.id}"
    if key not in st.session_state:
        session = _sf_session()
        if session is not None and comp.id == "wc2026":
            from porra.snowflake_store import load_results_sf
            st.session_state[key] = load_results_sf(session)
        else:
            st.session_state[key] = load_results(comp.results_path)
    auto_sync(st.session_state[key])
    return st.session_state[key]


@st.cache_data(ttl=900, show_spinner="Actualizando resultados desde ESPN y Wikipedia…")
def _fetch_games(comp_id: str):
    """Descarga (cacheada 15 min, por competición) los partidos de las fuentes."""
    from porra.sources.espn import ESPNSource
    from porra.sources.wikipedia import WikipediaSource

    comp = get_competition(comp_id)
    data = _load_data(comp_id)
    games = []
    for source in (ESPNSource(league=comp.espn_league),
                   WikipediaSource(articles=list(comp.wiki_articles))):
        try:
            games.extend(source.fetch(data))
        except Exception:  # noqa: BLE001 — una fuente caída no debe romper la app
            continue
    return games


@st.cache_data(ttl=30, show_spinner=False)
def _fetch_live_games(comp_id: str):
    """Descarga (cacheada 30 s, por competición) los partidos de ESPN para el directo.

    Solo ESPN: su API JSON es rápida e informa del estado del partido (en juego /
    finalizado) y del reloj, mientras que Wikipedia no da el directo de forma fiable.
    """
    from porra.sources.espn import ESPNSource

    comp = get_competition(comp_id)
    try:
        return ESPNSource(league=comp.espn_league).fetch(_load_data(comp_id))
    except Exception:  # noqa: BLE001 — el directo es best-effort
        return []


def _combined_games(comp_id: str):
    """Juegos para sincronizar finales: el directo (fresco, 30 s) tiene prioridad
    sobre la descarga combinada de 15 min ante un mismo enfrentamiento."""
    seen: set[tuple[str, str]] = set()
    out = []
    for g in list(_fetch_live_games(comp_id)) + list(_fetch_games(comp_id)):
        key = (g.home, g.away)
        if key not in seen:
            seen.add(key)
            out.append(g)
    return out


def get_live(results: Results) -> dict:
    """Marcadores en directo (``{nº: LiveMatch}``) de los partidos en juego.

    Provisional y **no** persistido: no toca ``results`` ni cuenta para los puntos,
    que solo se calculan cuando el partido finaliza y entra por :func:`auto_sync`.
    Excluye los que ya tienen resultado final almacenado.
    """
    from porra.sources.base import map_live_matches
    from porra.tournament import resolved_match_teams

    data = get_data()
    teams = resolved_match_teams(data, results)
    live = map_live_matches(data, results, _fetch_live_games(active_id()), teams)
    return {n: lm for n, lm in live.items() if not results.has(n)}


def auto_sync(results: Results) -> int:
    """Incorpora los resultados nuevos de las fuentes. Devuelve cuántos aplicó."""
    from porra.sources.base import map_to_matches
    from porra.tournament import resolved_match_teams

    data = get_data()
    try:
        games = _combined_games(active_id())
    except Exception:  # noqa: BLE001
        return 0
    applied = 0
    for _ in range(6):  # varias pasadas: al cerrar una ronda se resuelve la siguiente
        teams = resolved_match_teams(data, results)
        proposals = map_to_matches(data, results, games, teams)
        nuevos = {n: mr for n, mr in proposals.items()
                  if results.goals(n) != (mr.home_goals, mr.away_goals)}
        if not nuevos:
            break
        for n, mr in nuevos.items():
            results.set_match(n, mr.home_goals, mr.away_goals)
            if mr.winner and mr.home_goals == mr.away_goals:
                results.ko_winners[n] = mr.winner
            applied += 1
    if applied:
        persist(results)
    return applied


def force_resync() -> None:
    """Limpia la caché de scraping para forzar una actualización inmediata."""
    _fetch_games.clear()
    _fetch_live_games.clear()


def persist(results: Results) -> None:
    """Guarda los resultados en el backend adecuado.

    * Snowflake: tabla ``PORRA_RESULTS`` (Snowpark).
    * Streamlit Cloud / local: ``data/results.json`` y, si hay credenciales de
      GitHub en ``st.secrets``, commit al repositorio.
    """
    comp = active_competition()
    session = _sf_session()
    if session is not None and comp.id == "wc2026":
        from porra.snowflake_store import save_results_sf
        save_results_sf(session, results)
        try:
            st.toast("Guardado en Snowflake ✅")
        except Exception:
            pass
        return

    save_results(results, comp.results_path)
    gh = _github_secrets()
    if not gh:
        return
    content = json.dumps(to_dict(results), ensure_ascii=False, indent=2)
    outcome = commit_file(
        token=gh["token"], repo=gh["repo"],
        path=comp.github_path,  # por competición (ignora un path fijo en secrets)
        content=content, branch=gh.get("branch", "main"),
    )
    (st.toast if outcome.ok else st.warning)(outcome.message)


def _github_secrets() -> dict | None:
    try:
        gh = st.secrets["github"]
    except Exception:
        return None
    if "token" in gh and "repo" in gh:
        return dict(gh)
    return None


STATUS_LABELS = {"FINISHED": "Finalizado", "LIVE": "En juego", "UPCOMING": "Próximamente"}


def render_competition_badge() -> None:
    """Muestra en la barra lateral la competición activa y un enlace a la portada."""
    try:
        if not has_selection():
            return
        comp = active_competition()
        with st.sidebar:
            st.caption(f"{comp.emoji} **{comp.name}** · {STATUS_LABELS.get(comp.status, '')}")
            st.page_link("app.py", label="🔀 Cambiar de competición")
    except Exception:  # noqa: BLE001 — accesorio: nunca debe tumbar la página
        pass


def configure_page() -> None:
    try:
        st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
    except Exception:
        pass  # ya configurada (p.ej. al re-ejecutar)
    from theme import inject_theme
    inject_theme()
    render_competition_badge()
    render_music_player()


# URL directa del MP3 (CDN de Suno) del himno de la porra "Pa porra la mía" (Lasa 2.0).
# La página https://suno.com/song/<id> sirve el audio en https://cdn1.suno.ai/<id>.mp3.
_SONG_URL = "https://cdn1.suno.ai/6c62706a-5c1f-4089-ab3f-6722ef0f6f4b.mp3"

# Mini-reproductor autocontenido. Va en un iframe (st.iframe) porque necesita
# JS propio para los botones; aislado, no interfiere con el resto de la página.
# Arranca PAUSADO (preload="none", sin autoplay): solo suena si el usuario le da al play.
_MUSIC_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<style>
 @import url('https://fonts.googleapis.com/css2?family=Saira:wght@500;700;800&display=swap');
 *{ box-sizing:border-box; }
 body{ margin:0; font-family:'Saira','Segoe UI',sans-serif; }
 .mp{ background:linear-gradient(165deg,#1b2632 0%,#0c1118 100%); border:1px solid #27333f;
   border-radius:13px; padding:12px 13px; color:#eaf1f3; }
 .mp .ttl{ display:flex; align-items:center; gap:7px; font-weight:800; text-transform:uppercase;
   letter-spacing:.02em; font-size:.92rem; }
 .mp .sub{ color:#8a99a6; font-size:.66rem; text-transform:uppercase; letter-spacing:.1em;
   margin:2px 0 11px; }
 .mp .ctr{ display:flex; align-items:center; gap:9px; }
 .mp button{ cursor:pointer; border:0; border-radius:9px; font-family:'Saira',sans-serif;
   font-weight:700; display:inline-flex; align-items:center; justify-content:center;
   transition:transform .12s ease, filter .12s ease, background .12s ease; }
 .mp button:active{ transform:translateY(1px); }
 .mp button:disabled{ opacity:.4; cursor:not-allowed; transform:none; }
 .mp .err{ display:none; color:#ff5a3c; font-size:.66rem; letter-spacing:.02em; margin-top:9px; }
 .mp .pp{ width:42px; height:42px; border-radius:50%; background:#c2f23c; color:#0a0e13; font-size:1rem; }
 .mp .pp:hover{ filter:brightness(1.07); }
 .mp .stop{ width:34px; height:34px; background:#27333f; color:#eaf1f3; font-size:.82rem; }
 .mp .stop:hover{ background:#33414f; }
 .mp .bar{ flex:1; height:6px; background:rgba(255,255,255,.08); border-radius:4px;
   overflow:hidden; cursor:pointer; }
 .mp .fill{ height:100%; width:0; background:linear-gradient(90deg,#9ec62f,#c2f23c); }
 .mp .tm{ font-size:.64rem; color:#8a99a6; font-variant-numeric:tabular-nums; min-width:32px;
   text-align:right; }
</style></head>
<body>
 <div class="mp">
   <div class="ttl">🎵 Pa porra la mía</div>
   <div class="sub">Lasa 2.0 · himno oficial</div>
   <div class="ctr">
     <button class="pp" id="pp" title="Reproducir / Pausar" aria-label="Reproducir o pausar">&#9658;</button>
     <button class="stop" id="stp" title="Parar" aria-label="Parar">&#9632;</button>
     <div class="bar" id="bar"><div class="fill" id="fill"></div></div>
     <div class="tm" id="tm">0:00</div>
   </div>
   <div class="err" id="err">&#9888; Audio no disponible ahora mismo.</div>
   <audio id="au" src="__SONG_URL__" preload="none"></audio>
 </div>
<script>
 const au=document.getElementById('au'), pp=document.getElementById('pp'),
   stp=document.getElementById('stp'), fill=document.getElementById('fill'),
   tm=document.getElementById('tm'), bar=document.getElementById('bar'),
   err=document.getElementById('err');
 const f=s=>{ s=Math.floor(s||0); return Math.floor(s/60)+':'+String(s%60).padStart(2,'0'); };
 // Fail-safe: si la canción no carga (404, Suno caído, red), avisa y desactiva.
 function dead(){ err.style.display='block'; pp.disabled=true; stp.disabled=true;
   pp.innerHTML='&#9658;'; fill.style.width='0%'; }
 au.onerror=dead;
 pp.onclick=()=>{ if(au.paused){ au.play().catch(dead); } else { au.pause(); } };
 stp.onclick=()=>{ au.pause(); au.currentTime=0; };
 au.onplay=()=>{ pp.innerHTML='&#10074;&#10074;'; };
 au.onpause=()=>{ pp.innerHTML='&#9658;'; };
 au.onended=()=>{ pp.innerHTML='&#9658;'; fill.style.width='0%'; tm.textContent='0:00'; };
 au.ontimeupdate=()=>{ const d=au.duration||0; fill.style.width=(d?au.currentTime/d*100:0)+'%';
   tm.textContent=f(au.currentTime); };
 bar.onclick=e=>{ const r=bar.getBoundingClientRect(); const p=(e.clientX-r.left)/r.width;
   if(au.duration){ au.currentTime=Math.max(0,Math.min(1,p))*au.duration; } };
</script>
</body></html>
"""


@st.cache_data(ttl=1800, show_spinner=False)
def _song_available() -> bool:
    """¿Responde el MP3 del himno? Fail-safe: cualquier fallo -> ``False``.

    Cacheado 30 min para no pegarle a la CDN en cada recarga. Nunca propaga
    excepción (red caída, timeout, DNS…): si el servicio de Suno no está o la
    canción desapareció, devolvemos ``False`` y no se pinta el reproductor.
    """
    try:
        import requests
        r = requests.head(_SONG_URL, timeout=4, allow_redirects=True,
                          headers={"User-Agent": "porra/1.0"})
        return r.ok
    except Exception:  # noqa: BLE001 — best-effort, no debe romper la app
        return False


def render_music_player() -> None:
    """Pinta el mini-reproductor del himno en la barra lateral (en todas las páginas).

    No suena por defecto; el usuario decide reproducir, pausar o parar. Se llama
    desde :func:`configure_page`, así que aparece bajo el menú de navegación.

    Doble red de seguridad para que nunca dé error si la canción desaparece o
    Suno está caído: (1) si la comprobación de disponibilidad falla, no se
    muestra el reproductor; (2) aun mostrándose, el ``<audio>`` avisa y se
    desactiva solo si la reproducción falla.
    """
    try:
        if not _song_available():
            return
        with st.sidebar:
            # st.iframe (reemplazo de components.html, obsoleto tras 2026-06-01):
            # un string que no es URL ni ruta se incrusta como HTML crudo en el iframe.
            st.iframe(_MUSIC_HTML.replace("__SONG_URL__", _SONG_URL), height=118)
    except Exception:  # noqa: BLE001 — el reproductor es accesorio: nunca debe tumbar la página
        pass


def fmt(value: float) -> str:
    """Formatea puntos siempre con un decimal (7.0, no 7), para un formato uniforme."""
    return f"{value:.1f}"


def proper_name(name: str) -> str:
    """Nombre de jugador en formato Proper para mostrar (PACO -> Paco).

    Solo afecta a la presentación; los datos internos conservan el original.
    """
    return str(name).title()
