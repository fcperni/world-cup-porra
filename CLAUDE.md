# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este repositorio

No es un proyecto de software: no hay código fuente, ni build, ni tests, ni linters. Es una **porra/quiniela del Mundial de fútbol** gestionada íntegramente con libros de Excel (`.xlsx`) almacenados en `docs/`. La plantilla original es obra de Miguel Ángel Tejero (`matejero`), está en español y los libros están protegidos por contraseña (las contraseñas no se facilitan) y no contienen macros.

No esperes comandos de compilación/test. El "trabajo" aquí es inspeccionar, comparar o explicar datos de las hojas de cálculo.

## Estructura de `docs/`

- `ADMIN.xlsx` — libro **maestro/agregador**. Recoge las predicciones de todos los participantes y calcula la clasificación general, estadísticas y gráficos.
- Un libro **por participante**, con su nombre como nombre de archivo: `ALFON`, `ANGEL`, `ARTURO`, `BELLO`, `BONERA`, `CASAS`, `CHISCO`, `FLORES`, `GAGO`, `GARZON`, `LASA`, `MAICKY`, `OBLI`, `OSCAR`, `PACO`, `PANDO`, `PIRI`, `RONIE`, `VICTOR`.

### Hojas de un libro de participante
`Home`, `WORLDCUP`, `Pool` (donde el participante introduce sus predicciones), `Fixture`, `Credits` y hojas auxiliares ocultas (`Idiomas`, `Combinaciones`, `Equipos`, `Horarios`).

### Hojas adicionales del libro `ADMIN`
Sustituye `Pool` por la maquinaria de agregación: `ADMIN`, `CLAS` (clasificación general), `DailyPrediction`, `DailyClas`, `Stats`, más hojas ocultas (`Graf`, `Combinaciones3`). Incluye gráficos (`xl/charts/`).

## Reglas de edición (heredadas de la plantilla)

Solo deben editarse las **celdas de entrada** designadas: los resultados de los partidos y los nombres de los equipos. Las fórmulas, la protección y la estructura de las hojas no deben modificarse — romperlas invalida los cálculos del libro `ADMIN`. Los nombres de los equipos y resultados se propagan a la clasificación mediante fórmulas y rangos con nombre (p. ej. `Ganador`, `FGLocal`, `FGVisitante`, `Part1Empate1L`...).

## Inspeccionar el contenido de un `.xlsx`

Un `.xlsx` es un ZIP de XML. Para leer su contenido sin abrir Excel:

```bash
unzip -o docs/ADMIN.xlsx -d /tmp/admin
# Nombres de hojas:
grep -o '<sheet [^/]*/>' /tmp/admin/xl/workbook.xml
# Textos/etiquetas (cadenas compartidas):
cat /tmp/admin/xl/sharedStrings.xml
# Celdas de una hoja concreta:
cat /tmp/admin/xl/worksheets/sheet1.xml
```

Los valores de texto de las celdas se almacenan en `xl/sharedStrings.xml` y se referencian por índice desde los `worksheets/sheetN.xml`. Para análisis de datos más serio, usa una librería (p. ej. `openpyxl` en Python) en lugar de parsear el XML a mano.
