# AIRadar

Un radar de noticias y lanzamientos de inteligencia artificial. Cada día se
revisan las mismas fuentes y se guarda un archivo JSON con lo publicado, con
una forma fija que permite compararlo con el de cualquier otro día. El
repositorio lo opera Codex siguiendo `AGENTS.md`.

Va por la etapa 2 de 5. La etapa 1 fijó las reglas: el contrato de datos, los
esquemas y la skill. La etapa 2 automatiza la recolección: un tool en Python
arma el snapshot, la skill lo invoca en lugar de hacer el trabajo a mano, y la
búsqueda se reparte entre cuatro subagentes que corren en paralelo con niveles
de razonamiento distintos.

## Dónde está cada cosa

| Entregable | Archivo |
|---|---|
| Manual operativo del repositorio para Codex | `AGENTS.md` |
| Contrato de datos de las noticias | `docs/contrato-de-datos.md` |
| JSON Schema de una noticia | `schemas/noticia.schema.json` |
| JSON Schema del snapshot diario | `schemas/snapshot.schema.json` |
| Snapshot de ejemplo, primer día | `data/snapshots/2026-09-14.json` |
| Snapshot de ejemplo, segundo día con deduplicación | `data/snapshots/2026-09-15.json` |
| Snapshot armado por el recolector | `data/snapshots/2026-09-16.json` |
| Skill de recolección | `.codex/skills/recolectar-noticias-ia/SKILL.md` |
| Catálogo de fuentes y sus feeds | `.codex/skills/recolectar-noticias-ia/references/fuentes.md` |
| Validador de snapshots | `.codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py` |
| Recolector: arma el snapshot del día | `tools/recolector.py` |
| Respuestas de ejemplo de los subagentes | `tools/fixtures/` |
| Medición de tokens, antes y después | `docs/medicion-de-tokens.md` |
| Reparto en paralelo y niveles de razonamiento | `docs/subagentes.md` |
| Subagente de blogs de proveedor | `.codex/agents/blogs-oficiales.md` |
| Subagente de changelogs y versiones | `.codex/agents/changelogs-y-releases.md` |
| Subagente de investigación | `.codex/agents/investigacion.md` |
| Subagente de regulación | `.codex/agents/regulacion.md` |

## Cómo se lee el proyecto

Empieza por `docs/contrato-de-datos.md`: define qué cuenta como noticia, qué
campos tiene —incluidas la evidencia que la respalda, la clave de
deduplicación y el estado—, y cómo se arma un snapshot. Los dos archivos de
`schemas/` son esa misma definición en JSON Schema draft 2020-12: el del
snapshot no repite la definición de una noticia, la referencia con
`"$ref": "./noticia.schema.json"`.

`data/snapshots/` tiene tres días seguidos escritos según esas reglas.
`AGENTS.md` explica cómo se trabaja sobre todo eso —incluida la política de
permisos de sesión frente a permanentes— y
`.codex/skills/recolectar-noticias-ia/` empaqueta la recolección en cinco
fases para poder repetirla igual cada día.

Para la etapa 2, sigue con `docs/subagentes.md`, que explica quién busca qué y
con qué nivel de razonamiento, y con `docs/medicion-de-tokens.md`, que mide lo
que cuesta la pasada con el tool y sin él.

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

El del 16 ya no está escrito a mano: lo produjo `tools/recolector.py` a partir
de las respuestas de `tools/fixtures/`, y deja dos hechos fuera por clave
repetida y una entrada en `pendiente` porque la fuente la etiquetó con una
sección que no corresponde a ninguna categoría del contrato.

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

## Armar un snapshot

```bash
# Con las respuestas de ejemplo que trae el repositorio
python3 tools/recolector.py \
  --fecha 2026-09-16 \
  --anterior data/snapshots/2026-09-15.json \
  --salida /tmp/2026-09-16.json

# Sin escribir nada, solo para ver qué haría
python3 tools/recolector.py --fecha 2026-09-16 --dry-run
```

Sale el mismo archivo que `data/snapshots/2026-09-16.json` salvo por los
`summary`: los resúmenes son lo único que no puede producir un programa, y el
paso editorial los entrega aparte con `--resumenes`, indexados por URL. Con
`--red` lee los feeds del catálogo en vez de los archivos de ejemplo.
Solo necesita Python 3 y su biblioteca estándar, igual que el validador, y es
determinista: repetir la orden con las mismas entradas no cambia ni un byte.
Las opciones completas están en `AGENTS.md`.

## Siguientes etapas

La publicación del radar llega en las etapas siguientes. Lo que se fija aquí es
el contrato: a partir de ahora, cualquier snapshot nuevo tiene que poder leerse
con las mismas reglas.
