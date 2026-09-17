# AGENTS.md — manual de AIRadar

Este archivo le explica a Codex qué es AIRadar y cómo se trabaja en este
repositorio.

## Propósito

AIRadar es un radar diario de noticias y lanzamientos de inteligencia
artificial. Cada día se revisan las fuentes del catálogo y se guarda un
archivo JSON con lo que se publicó, siempre con la misma forma, para poder
comparar un día con otro. No hay aplicación ni servidor: el producto son los
snapshots.

Todo el proyecto son archivos de texto: Markdown para la documentación, JSON
para los datos y un script de Python 3 que revisa que el snapshot esté bien
armado. No hace falta instalar nada.

## Estructura del repositorio

```
.
├── AGENTS.md
├── README.md
├── .codex/
│   └── skills/
│       └── recolectar-noticias-ia/   # SKILL.md, scripts y references
├── data/
│   └── snapshots/             # un archivo por día: YYYY-MM-DD.json
├── docs/
│   └── contrato-de-datos.md   # qué es una noticia y qué es un snapshot
└── schemas/
    ├── noticia.schema.json
    └── snapshot.schema.json
```

## Cómo se trabaja un día

1. Mira cuál fue el último archivo de `data/snapshots/`.
2. Invoca la skill `recolectar-noticias-ia` con la fecha de hoy: busca en las
   fuentes, arma las entradas y escribe el archivo del día.
3. Pasa el validador al archivo que quedó y corrige lo que reporte.
4. Haz el commit con el snapshot.

Codex pide permiso cuando necesita red o escribir archivos.

## Skills disponibles

| Skill | Cuándo se usa |
|---|---|
| `recolectar-noticias-ia` | Generar o rehacer el snapshot de un día. Ver `.codex/skills/recolectar-noticias-ia/SKILL.md`. |

## Convenciones

- Los snapshots se llaman `data/snapshots/YYYY-MM-DD.json`, con la fecha en
  UTC y uno por día.
- La prosa va en español y las claves de los datos en inglés
  (`published_at`, `source`), que es como vienen de las fuentes.
- Los mensajes de commit son `tipo: descripción en español`, por ejemplo
  `data: snapshot 2026-09-14`.
- Si hay que cambiar el contrato, se cambia primero
  `docs/contrato-de-datos.md` y después los esquemas de `schemas/`.
