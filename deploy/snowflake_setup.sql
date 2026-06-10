/* ============================================================================
   Despliegue de "Pa porra la mía" en Streamlit in Snowflake (SiS)
   ----------------------------------------------------------------------------
   Ejecuta este script en una hoja SQL de Snowsight con un rol con privilegios
   suficientes (ACCOUNTADMIN o un rol con CREATE INTEGRATION / WAREHOUSE / DB).
   Ajusta los nombres si lo prefieres; el repo es PÚBLICO, así que la integración
   Git no necesita secreto.
   ============================================================================ */

-- 0) Contexto -----------------------------------------------------------------
SET app_role = 'SYSADMIN';   -- rol propietario de la app (cámbialo si quieres)
USE ROLE ACCOUNTADMIN;

-- 1) Warehouse, base de datos y esquema --------------------------------------
CREATE WAREHOUSE IF NOT EXISTS PORRA_WH
  WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE INITIALLY_SUSPENDED = TRUE;
CREATE DATABASE IF NOT EXISTS PORRA_DB;
CREATE SCHEMA  IF NOT EXISTS PORRA_DB.APP;

GRANT USAGE ON WAREHOUSE PORRA_WH        TO ROLE IDENTIFIER($app_role);
GRANT USAGE ON DATABASE  PORRA_DB        TO ROLE IDENTIFIER($app_role);
GRANT ALL   ON SCHEMA    PORRA_DB.APP    TO ROLE IDENTIFIER($app_role);

USE ROLE IDENTIFIER($app_role);
USE DATABASE PORRA_DB;
USE SCHEMA   PORRA_DB.APP;
USE WAREHOUSE PORRA_WH;

-- 2) Tabla de resultados (persistencia; la app también la crea si falta) ------
CREATE TABLE IF NOT EXISTS PORRA_DB.APP.PORRA_RESULTS (id INT PRIMARY KEY, payload VARIANT);

-- 3) Integración Git con el repositorio público ------------------------------
USE ROLE ACCOUNTADMIN;
CREATE OR REPLACE API INTEGRATION PORRA_GIT_API
  API_PROVIDER = git_https_api
  API_ALLOWED_PREFIXES = ('https://github.com/fcperni')
  ENABLED = TRUE;
GRANT USAGE ON INTEGRATION PORRA_GIT_API TO ROLE IDENTIFIER($app_role);

USE ROLE IDENTIFIER($app_role);
CREATE OR REPLACE GIT REPOSITORY PORRA_DB.APP.PORRA_REPO
  API_INTEGRATION = PORRA_GIT_API
  ORIGIN = 'https://github.com/fcperni/world-cup-porra';
ALTER GIT REPOSITORY PORRA_DB.APP.PORRA_REPO FETCH;   -- repetir tras cada push

-- 4) Acceso de red para el scraping (ESPN + Wikipedia) -----------------------
--    Opcional: si lo omites, la entrada manual de resultados funciona igual.
USE ROLE ACCOUNTADMIN;
CREATE OR REPLACE NETWORK RULE PORRA_DB.APP.PORRA_NET_RULE
  MODE = EGRESS TYPE = HOST_PORT
  VALUE_LIST = ('site.api.espn.com', 'en.wikipedia.org');
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION PORRA_EAI
  ALLOWED_NETWORK_RULES = (PORRA_DB.APP.PORRA_NET_RULE)
  ENABLED = TRUE;
GRANT USAGE ON INTEGRATION PORRA_EAI TO ROLE IDENTIFIER($app_role);

-- 5) Crear la app Streamlit desde el repositorio Git -------------------------
USE ROLE IDENTIFIER($app_role);
CREATE OR REPLACE STREAMLIT PORRA_DB.APP.PORRA_APP
  ROOT_LOCATION = '@PORRA_DB.APP.PORRA_REPO/branches/main'
  MAIN_FILE = 'app.py'
  QUERY_WAREHOUSE = PORRA_WH
  EXTERNAL_ACCESS_INTEGRATIONS = (PORRA_EAI)   -- quita esta línea si omites el paso 4
  TITLE = 'Pa porra la mía';

-- 6) (Opcional) permitir que otros roles vean la app -------------------------
-- GRANT USAGE ON STREAMLIT PORRA_DB.APP.PORRA_APP TO ROLE <ROL_DE_USUARIOS>;

-- 7) Abrir la app: Snowsight → Projects → Streamlit → "Pa porra la mía"
--    o consulta la URL con:
SHOW STREAMLITS IN SCHEMA PORRA_DB.APP;

/* ----------------------------------------------------------------------------
   ACTUALIZAR la app tras un nuevo push al repo:
     ALTER GIT REPOSITORY PORRA_DB.APP.PORRA_REPO FETCH;
   y recarga la app (o vuelve a ejecutar el CREATE OR REPLACE STREAMLIT).
   ---------------------------------------------------------------------------- */
