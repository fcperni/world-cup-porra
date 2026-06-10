# ⚽ Pa porra la mía

App web (Streamlit) para gestionar y analizar la **porra del Mundial 2026** de 19
participantes. Lee las predicciones desde `docs/ADMIN.xlsx`, reproduce **con
fidelidad 100%** el sistema de puntuación de la plantilla Excel en Python, y
actualiza los resultados de los partidos **automáticamente por scraping** (ESPN
como fuente principal, Wikipedia de reserva) — sin entrada ni sincronización manual.

Funciona tal cual en **dos entornos** sin tocar el código: Streamlit Community
Cloud / local (persistencia en `data/results.json` + commit opcional a GitHub) y
**Streamlit in Snowflake** (persistencia en la tabla `PORRA_RESULTS`). La app
detecta sola dónde corre.

## Por qué Python y no Excel

`openpyxl` no recalcula las fórmulas de Excel (solo lee el último valor cacheado).
Por eso `ADMIN.xlsx` se usa como **fuente de solo lectura** (predicciones, reglas,
calendario, tabla de equipos y mejores terceros) y todo el cálculo —clasificación
de grupos con desempates, mejores terceros, propagación del cuadro y puntuación—
se reimplementa en `porra/`. La fidelidad está verificada: el motor reproduce
exactamente los **máximos por categoría** que el propio Excel declara
(`tests/test_fidelity.py`).

## Estructura

```
app.py                     Entrypoint Streamlit
pages/                     Resultados · Clasificación · Jugador · Grupos y Brackets
ui_common.py               Carga cacheada + estado de sesión + persistencia
porra/
  excel_loader.py          Extracción de ADMIN.xlsx
  models.py                Modelos de dominio
  tournament.py            Standings, desempates, mejores terceros, brackets
  scoring.py               Motor de puntuación (reproduce las fórmulas)
  results_store.py         Lectura/escritura de data/results.json
  github_sync.py           Commit de resultados vía API de GitHub
  sources/                 base · espn · wikipedia (scraping)
data/results.json          Resultados introducidos (se commitea al repo)
tests/                     Extracción, scoring, torneo, fidelidad, fuentes, smoke UI
```

## Puntuación (resumen)

Por partido: **signo 1X2**, **diferencia de goles** (crédito parcial: el acierto
disminuye un 10% por cada gol de error si el signo es correcto) y **resultado
exacto**; todo multiplicado por el **bonus** del partido. Los puntos base escalan
por ronda (grupos → final). Además: **posiciones exactas** de grupo, **equipos
clasificados** a cada ronda, **partidos** de eliminatorias (acertando la pareja
del cruce) y el **cuadro de honor** (campeón, subcampeón, 3º, botas y balones).

## Uso local

```bash
pip install -r requirements.txt
streamlit run app.py
pytest                      # ejecutar los tests
```

## Despliegue en Streamlit Cloud

1. Sube el repo a `github.com/fcperni/world-cup-porra` (incluye `docs/ADMIN.xlsx`).
2. Crea la app en https://share.streamlit.io apuntando a `app.py`.
3. En **Settings → Secrets** pega el contenido de
   `.streamlit/secrets.toml.example` con un **PAT** de GitHub (permiso
   *Contents: Read and write*). Así `data/results.json` se commitea al repo y los
   resultados persisten entre reinicios (el disco de Cloud es efímero).

Sin secrets, la app funciona igual pero solo guarda en disco local.

> Nota: el repo incluye `requirements.txt` (pip, para Cloud/local) y
> `environment.yml` (conda, para Snowflake). Streamlit Community Cloud usa **un
> solo** archivo de dependencias; si alguna vez fallara por elegir
> `environment.yml`, basta con añadirle `streamlit` o priorizar `requirements.txt`.

## Despliegue en Streamlit in Snowflake

La app corre nativamente en Snowflake (persistencia en tabla, sin GitHub). Pasos:

1. Ejecuta `deploy/snowflake_setup.sql` en una hoja de Snowsight con un rol admin.
   Crea warehouse, base/esquema, la tabla `PORRA_RESULTS`, la **integración Git**
   con este repo, una **External Access Integration** para el scraping (ESPN +
   Wikipedia) y el objeto `STREAMLIT`.
2. Abre la app en **Snowsight → Projects → Streamlit → "Pa porra la mía"**.
3. Tras cada `git push`, ejecuta `ALTER GIT REPOSITORY … FETCH;` para actualizarla.

Dependencias en Snowflake: `environment.yml` (canal Anaconda de Snowflake; sin
PyGithub). Si omites la integración de red, la app arranca igual pero no podrá
scrapear (la entrada es solo automática, así que conviene configurarla).
