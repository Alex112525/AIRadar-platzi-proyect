# AIRadar

Un radar de noticias y lanzamientos de inteligencia artificial. Cada día se
revisan las mismas fuentes y se guarda un archivo JSON con lo publicado, con
una forma fija que permite compararlo con el de cualquier otro día. El
repositorio lo opera Codex siguiendo `AGENTS.md`.

Esta es la etapa 1 de 5 del proyecto: los cimientos. Todavía no hay
recolección automática; lo que existe son las reglas, los esquemas, un
snapshot de ejemplo y la skill que hará el trabajo.

## Dónde está cada cosa

| Entregable | Archivo |
|---|---|
| Manual operativo del repositorio para Codex | `AGENTS.md` |
| Contrato de datos de las noticias | `docs/contrato-de-datos.md` |
| JSON Schema de una noticia | `schemas/noticia.schema.json` |
| JSON Schema del snapshot diario | `schemas/snapshot.schema.json` |
| Snapshot diario de ejemplo | `data/snapshots/2026-09-14.json` |
| Skill de recolección | `.codex/skills/recolectar-noticias-ia/SKILL.md` |
| Catálogo de fuentes que usa la skill | `.codex/skills/recolectar-noticias-ia/references/fuentes.md` |
| Validador de snapshots | `.codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py` |

## Cómo se lee el proyecto

Empieza por `docs/contrato-de-datos.md`: define qué cuenta como noticia, qué
campos tiene y cómo se arma un snapshot. Los dos archivos de `schemas/` son la
misma definición en JSON Schema (draft 2020-12), y
`data/snapshots/2026-09-14.json` es un día completo escrito según esas reglas.
`AGENTS.md` explica cómo se trabaja sobre todo eso y
`.codex/skills/recolectar-noticias-ia/` empaqueta la recolección para poder
repetirla igual cada día.

## Sobre el snapshot de ejemplo

`data/snapshots/2026-09-14.json` está construido a mano para mostrar cómo se
ve un día completo bajo el contrato: sirve como referencia de formato, no como
registro histórico. Las nueve entradas son ilustrativas del tipo de hecho que
sigue el radar (modelos, APIs, versiones de herramientas abiertas, novedades
regulatorias), no un archivo de prensa.

## Validar un snapshot

```bash
python3 .codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py data/snapshots/2026-09-14.json
```

Comprueba los campos obligatorios, los tipos, el formato de las fechas, las
listas cerradas, que los `id` no se repitan y que `item_count` coincida con el
número de entradas. Sale con código 0 cuando el archivo cumple el contrato y
con 1 cuando no, listando los errores. Solo necesita Python 3 y su biblioteca
estándar.

## Siguientes etapas

La recolección real, la revisión de duplicados entre días y la publicación del
radar llegan en las etapas siguientes. Lo que se fija aquí es el contrato: a
partir de ahora, cualquier snapshot nuevo tiene que poder leerse con las
mismas reglas.
