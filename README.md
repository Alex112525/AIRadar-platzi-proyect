# AIRadar

Un radar de noticias y lanzamientos de inteligencia artificial. Cada día se
revisan las mismas fuentes y se guarda un archivo JSON con lo publicado, con
una forma fija que permite compararlo con el de cualquier otro día. El
repositorio lo opera Codex siguiendo `AGENTS.md`.

Esta es la etapa 1 de 5 del proyecto: los cimientos. Todavía no hay
recolección automática; lo que existe son las reglas, los esquemas, dos
snapshots de ejemplo y la skill que hará el trabajo.

## Dónde está cada cosa

| Entregable | Archivo |
|---|---|
| Manual operativo del repositorio para Codex | `AGENTS.md` |
| Contrato de datos de las noticias | `docs/contrato-de-datos.md` |
| JSON Schema de una noticia | `schemas/noticia.schema.json` |
| JSON Schema del snapshot diario | `schemas/snapshot.schema.json` |
| Snapshot de ejemplo, primer día | `data/snapshots/2026-09-14.json` |
| Snapshot de ejemplo, segundo día con deduplicación | `data/snapshots/2026-09-15.json` |
| Skill de recolección | `.codex/skills/recolectar-noticias-ia/SKILL.md` |
| Catálogo de fuentes que usa la skill | `.codex/skills/recolectar-noticias-ia/references/fuentes.md` |
| Validador de snapshots | `.codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py` |

## Cómo se lee el proyecto

Empieza por `docs/contrato-de-datos.md`: define qué cuenta como noticia, qué
campos tiene —incluidas la evidencia que la respalda, la clave de
deduplicación y el estado—, y cómo se arma un snapshot. Los dos archivos de
`schemas/` son esa misma definición en JSON Schema draft 2020-12: el del
snapshot no repite la definición de una noticia, la referencia con
`"$ref": "./noticia.schema.json"`.

`data/snapshots/` tiene dos días seguidos escritos según esas reglas.
`AGENTS.md` explica cómo se trabaja sobre todo eso —incluida la política de
permisos de sesión frente a permanentes— y
`.codex/skills/recolectar-noticias-ia/` empaqueta la recolección en cinco
fases para poder repetirla igual cada día.

## Sobre los snapshots de ejemplo

Los dos snapshots están construidos a mano para mostrar cómo se ve un día
completo bajo el contrato: sirven como referencia de formato, no como registro
histórico. Sus entradas son ilustrativas del tipo de hecho que sigue el radar
(modelos, APIs, versiones de herramientas abiertas, novedades regulatorias),
no un archivo de prensa.

El del 14 es el primer día: no hay nada anterior contra lo que deduplicar, dos
entradas quedaron en `pendiente` porque la fuente respondió a medias y una
quedó en `descartado` por enlazar al boletín en vez de al trabajo original. El
del 15 se compara con el anterior y deja tres hechos fuera por clave repetida,
anotados en `dedup.discarded`.

## Validar un snapshot

```bash
# Contra el contrato
python3 .codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py \
  data/snapshots/2026-09-14.json

# Contra el contrato y contra el día anterior
python3 .codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py \
  data/snapshots/2026-09-15.json --previous data/snapshots/2026-09-14.json
```

Comprueba los campos obligatorios —incluidos los de `evidence`—, los tipos, el
formato de las fechas, las listas cerradas de `category`, `source_type` y
`status`, que `dedup_key` corresponda a `source` más la URL canónica, que no
se repitan ni los `id` ni las claves y que `item_count` coincida con el número
de entradas. Con `--previous` comprueba además que ninguna clave del día
anterior reaparezca y que los descartes declarados existan de verdad. Sale con
código 0 cuando el archivo cumple el contrato y con 1 cuando no, listando los
errores. Solo necesita Python 3 y su biblioteca estándar.

## Siguientes etapas

La recolección real y la publicación del radar llegan en las etapas
siguientes. Lo que se fija aquí es el contrato: a partir de ahora, cualquier
snapshot nuevo tiene que poder leerse con las mismas reglas.
