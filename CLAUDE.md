# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es

App **Streamlit** ("Pa porra la mía") para la porra del Mundial 2026 de 19 participantes. Lee `docs/ADMIN.xlsx` como **fuente de solo lectura** (predicciones, reglas, calendario, equipos, tabla de mejores terceros) y **reimplementa en Python** todo el cálculo. Permite introducir resultados manualmente o por scraping (ESPN principal, Wikipedia backup). Desplegada en Streamlit Cloud desde `github.com/fcperni/world-cup-porra`.

**Decisión central:** `openpyxl` no recalcula fórmulas de Excel (solo lee el valor cacheado, hoy todo a 0). Por eso el motor de puntuación y la lógica del torneo viven en `porra/`, no en el Excel.

## Flujo de trabajo (git) — OBLIGATORIO

**Haz commit y push de _cada_ cambio** en cuanto esté terminado y verificado (no
acumules cambios sin subir). Tras editar, ejecuta los tests relevantes, commitea
con un mensaje descriptivo y haz `git push origin main`.

Gotcha de credenciales: el entorno suele exponer un `GITHUB_TOKEN` (un PAT
fine-grained) **sin acceso** a `world-cup-porra`, y `gh` lo prioriza sobre la
credencial de keyring (OAuth con scope `repo`, que sí tiene push). Si el push da
`403 Write access not granted`, haz el push sin esa variable:

```bash
env -u GITHUB_TOKEN git push origin main          # bash
```
```powershell
$env:GITHUB_TOKEN=$null; git push origin main      # PowerShell
```

Termina los mensajes de commit con la línea `Co-Authored-By: Claude …`.

## Comandos

```bash
pip install -r requirements.txt
streamlit run app.py                       # arrancar la app
pytest                                      # toda la suite (56 tests)
pytest tests/test_fidelity.py -q            # validación de fidelidad al Excel
pytest tests/test_scoring.py::test_exacto   # un test concreto
python -m porra.excel_loader                # verificación rápida de extracción
```

En Windows, antepón `PYTHONUTF8=1` al ejecutar scripts que impriman nombres con acentos (la consola usa cp1252 y peta con `México`, `🥇`, etc.). Los datos del fichero son UTF-8 correctos; es solo la consola.

## Arquitectura

`porra/` es un paquete **puro** (sin Streamlit). Streamlit vive en `app.py`, `pages/` y `ui_common.py`.

- **`excel_loader.py`** → `load_tournament()` devuelve un `TournamentData` (equipos, 104 `Match`, 19 `Player`, `ScoringRules`, bracket, tabla de terceros). Toda la extracción es **programática** y verificada por `tests/test_extraction.py` — no hardcodees datos del Excel sin pasar por aquí.
- **`tournament.py`** → clasificación de grupos con desempates (**reglas FIFA 2026**, Art. 13: puntos → enfrentamiento directo [puntos → DG → GF entre las empatadas] → DG general → GF general → ranking FIFA; el directo va **antes** que la DG general, al revés que hasta 2022 — el *fair play* se omite por no tener tarjetas), `qualified_thirds_groups()` (8 mejores terceros), `locked_group_positions()` (posiciones de grupo ya matemáticamente aseguradas, sin falsos positivos), `clinched_knockout()` (selecciones con el pase a dieciseisavos asegurado) y `resolve_bracket()`/`resolved_match_teams()` que resuelven placeholders (`1A`, `3ABCDF`, `W74`, `L101`) a selecciones reales — incluyendo posiciones de grupo en cuanto quedan fijadas, no solo al cerrar el grupo.
- **`scoring.py`** → `scoreboard()` y `score_player()`. `score_match()` es el núcleo y se reutiliza en grupos y KO.
- **`results_store.py`** → `Results` (resultados + cuadro de honor + ganadores por penaltis) ↔ `data/results.json`.
- **`github_sync.py`** + `ui_common.persist()` → al guardar, commitea `results.json` al repo si hay `[github]` en `st.secrets` (necesario en Cloud, disco efímero). Sin secrets, solo escribe en disco.
- **`sources/`** → `ResultsSource` (interfaz), `espn.py`, `wikipedia.py`. `map_to_matches()` empareja por la **pareja** de selecciones (normalizando nombres con la tabla de alias de `base.py`); solo partidos **finalizados**. `map_live_matches()` hace el mismo emparejado para los partidos **en juego** (`state == "in"`, vía ESPN), que `ui_common.get_live()` expone como marcador en directo. El directo **no** se escribe en `Results` ni cuenta para los puntos: solo se muestra (Calendario y Predicciones, con indicador "en juego" y autorefresco vía `st.fragment(run_every=30)`); los puntos se calculan únicamente cuando el partido finaliza y `auto_sync` lo incorpora a `results.json`.

- **`analytics.py`** → analítica de uso **privada** y opcional. Cada página llama a `analytics.track(pagina, detalle)`; registra una fila por *(sesión, página, detalle)* en Postgres (`st.connection("analytics")`), deduplicando en `st.session_state` para que los reruns no inflen las cifras. Es **no-op** si no hay `[connections.analytics]` en secrets. Se consulta en `pages/8_Admin.py`, oculta del menú lateral (CSS en `theme.py`) y protegida por `st.secrets['admin']['password']`. Solo guarda un id de sesión aleatorio (sin IP ni datos personales).

Flujo: `excel_loader` (cacheado con `st.cache_data` en `ui_common.get_data()`) → `Results` en `st.session_state` → `tournament` resuelve el cuadro → `scoring` calcula → las páginas renderizan.

## Reglas de puntuación (reproducen ADMIN.xlsx)

Por partido: si aciertas signo **y** marcador → `(signo+diferencia+exacto)*bonus`; si solo el signo → `(signo + diferencia*(1 - dist*0.1))*bonus` acotado a ≥0, donde `dist` = `|local_real-local_predicho|` en empates o `|dif_real-dif_predicha|`; si fallas el signo → 0. Los puntos base escalan por ronda. Además: posiciones exactas de grupo, equipos clasificados por ronda, partidos KO (acertando la **pareja** del cruce, en cualquier orden) y cuadro de honor.

**Fidelidad:** `test_fidelity.py` construye un "jugador perfecto" y comprueba que el motor reproduce **exactamente** los máximos por categoría que el Excel declara en `CLAS` fila 3 (630, 576, 345…; total 4364). Si tocas el scoring, este test debe seguir verde.

## Detalles no evidentes del Excel (hoja ADMIN)

- **Codificación de predicciones**: grupos `"signo|local-visitante"` (`"1|3-1"`, signo ∈ {1,X,2}); KO `"Local-Visitante·signo|l-v"` (dos equipos antes del `·`; ningún nombre lleva guion). Cuadro de honor: nombres.
- **Columnas de jugador**: la predicción del jugador *i* está en la columna `19 + 3*i` (S, V, Y, …), nombre en la fila 5.
- **Filas → partido**: los grupos (filas 6-77) se vinculan a WORLDCUP por la fórmula de la columna O (`=WORLDCUP!AC<fila>`); los KO, por la etiqueta de cruce de la columna K.
- **Grupo de un partido**: en WORLDCUP la etiqueta "Grupo X" solo aparece en la 1ª fila de cada bloque; se deriva del equipo local.
- **Numeración**: grupos 1-72, 1/16 73-88, 1/8 89-96, 1/4 97-100, 1/2 101-102, 3-4 103, final 104. Bonus por ronda: grupos var. (1 ó 3), 1/16-1/4 = 2, 1/2-final = 3.
- **Mejores terceros**: hoja `Combinaciones3` (495 combos C(12,8)); cada cruce con tercero tiene como local uno de `1A,1B,1D,1E,1G,1I,1K,1L`.

## Despliegue

Push a `fcperni/world-cup-porra` y conectar en share.streamlit.io (`app.py`). En **Settings → Secrets** pegar un PAT con *Contents: Read and write* (formato en `.streamlit/secrets.toml.example`). `.streamlit/secrets.toml` está en `.gitignore` — nunca subir el token. Solo `docs/ADMIN.xlsx` se despliega; los `.xlsx` de participantes están ignorados.
