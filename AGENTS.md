# AGENTS.md — manual operativo de AIRadar

Este archivo es el manual con el que Codex opera el repositorio: qué es el
proyecto, con qué está hecho, cómo se comporta el agente, qué permisos usa,
cómo se trabaja un día normal, qué hacer cuando algo falla y cuándo se
considera terminado un snapshot. Si algo de aquí contradice al contrato de
datos, manda el contrato (`docs/contrato-de-datos.md`).

## Propósito

AIRadar mantiene un radar diario de noticias y lanzamientos de inteligencia
artificial. Cada día se revisan las fuentes del catálogo y se deja un archivo
JSON con lo publicado, siempre con la misma forma. El repositorio no tiene
aplicación ni servidor: el producto son los snapshots y las reglas que los
hacen comparables entre sí.

El valor está en la constancia y en el formato. Un snapshot bonito pero con
campos inventados vale menos que uno corto que respeta el contrato.

## Tecnologías

| Pieza | Qué se usa | Por qué |
|---|---|---|
| Agente | **Codex CLI**, dirigido por este manual y por la skill de `.codex/skills/` | Orquesta la pasada diaria y aporta el criterio editorial. |
| Subagentes | Cuatro definiciones en `.codex/agents/`, una por tipo de fuente, en paralelo | Reparten la búsqueda y llevan cada uno su contexto y su nivel de razonamiento. |
| Recolección | **`tools/recolector.py`**, Python 3 y biblioteca estándar | Ejecuta la parte mecánica: normaliza, calcula claves, deduplica y escribe el snapshot. |
| Datos | **JSON** con sangría de dos espacios, UTF-8, un archivo por día | Legible en un diff y trivial de leer desde cualquier lenguaje. |
| Contrato | **JSON Schema draft 2020-12**, dos archivos compuestos por `$ref` | Define la forma una sola vez y se valida con herramientas estándar. |
| Validación | **Python 3 y solo su biblioteca estándar** (`json`, `re`, `hashlib`, `argparse`, `datetime`, `urllib.parse`) | El validador corre sin instalar nada, en cualquier máquina. |
| Documentación | **Markdown** en español | El repositorio se lee antes de ejecutarse. |
| Versiones | **Git**, un commit por asunto | El historial de `data/snapshots/` es la bitácora del radar. |

No hay dependencias externas, ni `requirements.txt`, ni entorno virtual. Si
una tarea parece necesitar una biblioteca de terceros, casi siempre está mal
planteada para este repositorio.

## Reglas de comportamiento del agente

**Siempre:**

- Trabaja con las fuentes del catálogo
  (`.codex/skills/recolectar-noticias-ia/references/fuentes.md`) y con nada más.
- Copia literalmente el identificador de `source` y la cita de `evidence`.
- Deja constancia de lo que no pudo verificar: `status: pendiente` con su
  `status_note`, en vez de silencio.
- Valida el snapshot antes de darlo por terminado y corrige lo que reporte.
- Pide confirmación antes de cualquier acción que salga del repositorio.
- Explica en el mensaje del commit qué cambió y por qué.

**Nunca:**

- Inventar una noticia, una cita, una fecha o una URL. Un dato que no está en
  la fuente no se escribe: el campo opcional se omite y el obligatorio deja la
  entrada en `pendiente`.
- Rellenar `summary` con una cadena vacía, un guion o un «sin resumen».
- Reescribir un snapshot publicado para tapar un error; se corrige con un
  commit nuevo que lo explique.
- Cambiar el contrato sobre la marcha para que quepa una entrada rebelde.
- Renombrar un `source`: los snapshots viejos quedarían escritos con un
  identificador que ya no existe y sus claves dejarían de cuadrar.
- Instalar dependencias, borrar snapshots o empujar a remoto por iniciativa
  propia.
- Tocar nada fuera de este repositorio.

## Estructura del repositorio

```
.
├── AGENTS.md                  # este manual
├── README.md                  # mapa del repositorio
├── .codex/
│   ├── skills/
│   │   └── recolectar-noticias-ia/   # skill: SKILL.md, scripts y references
│   └── agents/                # subagentes: uno por tipo de fuente
├── data/
│   └── snapshots/             # un archivo por día: YYYY-MM-DD.json
├── docs/
│   ├── contrato-de-datos.md   # definición de noticia y de snapshot
│   ├── medicion-de-tokens.md  # ahorro del recolector, antes y después
│   └── subagentes.md          # reparto en paralelo y niveles de razonamiento
├── schemas/
│   ├── noticia.schema.json    # JSON Schema de una noticia
│   └── snapshot.schema.json   # JSON Schema del snapshot diario
└── tools/
    ├── recolector.py          # arma el snapshot del día
    └── fixtures/              # respuestas de ejemplo, una por fuente
```

## Skills disponibles

| Skill | Cuándo se usa |
|---|---|
| `recolectar-noticias-ia` | Generar o rehacer el snapshot de un día. Ver `.codex/skills/recolectar-noticias-ia/SKILL.md`. |

La skill encapsula el flujo completo —buscar, priorizar, estructurar,
deduplicar y guardar— para que la recolección no dependa de recordar los pasos
cada mañana. Delega la búsqueda en los cuatro subagentes de `.codex/agents/` y
la parte mecánica en `tools/recolector.py`. Una tarea que se repite dos veces con los mismos pasos es
candidata a skill; antes de escribir una nueva, comprueba que no sea una
variante de la que ya existe.

## Permisos: sesión vs. permanentes

Codex corre en un sandbox y pide aprobación para salir de él. Este repositorio
se apoya en ese modelo a propósito: la skill corre **todos los días**, y un
permiso concedido «para siempre» es un permiso que nadie vuelve a mirar. La
regla es que el alcance del permiso dure lo mismo que la tarea, así que se
trabaja con el modo que pregunta, no con el que deja de preguntar.

**Siempre permitido, sin preguntar** — lectura y comprobación, sin efectos
fuera del repositorio:

- Leer cualquier archivo: manual, contrato, esquemas, catálogo, snapshots.
- Ejecutar el validador
  (`.codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py`), que
  solo lee archivos y escribe en la salida estándar.
- Consultas de git de solo lectura: `git status`, `git log`, `git diff`.

**Aprobación por sesión**, una vez en cada pasada, y caduca al terminarla:

- **Red, limitada a los dominios del catálogo de fuentes**, y dentro de eso
  **cada subagente solo alcanza los dominios de sus propias fuentes**:
  `blogs-oficiales` los cinco blogs de proveedor, `changelogs-y-releases` el
  changelog y los dos repositorios, `regulacion` el boletín oficial, y
  `investigacion` el boletín editorial más los dominios de los trabajos que
  cita, que es la excepción explícita del catálogo. Es lo que necesita la fase
  *Buscar*. Un dominio que no está en el catálogo no se visita: si aparece uno
  nuevo, se agrega primero a
  `.codex/skills/recolectar-noticias-ia/references/fuentes.md`, en su propio
  commit.
- **Escritura en un directorio temporal fuera del repositorio**, donde los
  subagentes dejan su JSON y de donde lo lee el recolector. Se borra al cerrar
  la pasada.
- **Escritura en disco, limitada a `data/snapshots/`.** Es lo que necesita la
  fase *Guardar*. El resto del árbol —`docs/`, `schemas/`, `.codex/`— se toca
  en tareas aparte, nunca durante la recolección diaria.
- **Crear un commit local** con el snapshot del día.

**Nunca de forma permanente** — cada vez que haga falta se pide de nuevo y se
justifica:

- Instalar dependencias o modificar el entorno. El proyecto vive con la
  biblioteca estándar; una instalación silenciosa rompe la promesa de que el
  validador corre en cualquier máquina.
- `git push` o cualquier escritura en el remoto: la publicación la decide una
  persona, después de mirar el diff.
- Borrar o reescribir snapshots publicados. Una corrección es un commit nuevo.
- Ejecutar scripts que no estén bajo `.codex/skills/`. Lo que corre aquí está
  versionado y revisado; un script traído de fuera, no.

Cuando una acción caiga fuera de lo permitido, el agente se detiene y lo dice,
con el motivo y la alternativa. Un snapshot incompleto y honesto es un
resultado aceptable; un permiso tomado por la vía rápida, no.

## Convenciones de nombres

- **Snapshots**: `data/snapshots/YYYY-MM-DD.json`, fecha en UTC. Un archivo
  por día, sin sufijos ni copias tipo `-v2`.
- **Identificadores de noticia**: `<fecha de publicación>-<source>-<titulo-corto>`,
  en minúsculas, sin acentos y con guiones.
- **Identificadores de fuente**: en minúsculas y con guiones (`openai-blog`),
  definidos en el catálogo y estables para siempre.
- **Documentos**: en `docs/`, nombre en español y con guiones.
- **Skills**: una carpeta por skill en `.codex/skills/`, con el nombre en
  infinitivo, su `SKILL.md`, y `scripts/` y `references/` si los necesita.
- **Prosa en español, claves en inglés.** La documentación se escribe en
  español; los campos de los datos van en inglés (`published_at`, `source`),
  que es como están en las fuentes.

## Convenciones de commits

Formato `tipo: descripción en español`, en imperativo y sin punto final.

| Tipo | Para qué |
|---|---|
| `data` | Un snapshot nuevo o corregido: `data: snapshot 2026-09-15`. |
| `docs` | Cambios en `docs/`, el README o este manual. |
| `schema` | Cambios en `schemas/`. |
| `skill` | Cambios dentro de `.codex/skills/`. |
| `feat` | Capacidades nuevas del proyecto. |
| `fix` | Corrección de algo que estaba mal. |

Un commit por asunto. El snapshot del día va solo en su commit, sin arrastrar
documentación: así el historial de `data/snapshots/` se lee como la bitácora
del radar.

## Flujo de trabajo diario

1. Revisa en qué quedó el radar: último snapshot y árbol de trabajo limpio.
2. Invoca la skill `recolectar-noticias-ia` con la fecha de hoy. Lanza los
   cuatro subagentes en paralelo, prioriza lo que trajeron, redacta los
   resúmenes y arma el archivo con una llamada al recolector. La skill pide la
   aprobación de red antes de *Buscar* y la de escritura antes de *Guardar*.
3. Valida el archivo que produjo, con el snapshot anterior como referencia.
4. Revísalo contra los criterios de «hecho».
5. Haz el commit del snapshot.
6. Si apareció una fuente que vale la pena seguir, agrégala al catálogo en un
   commit `skill:` aparte, nunca dentro del commit del snapshot.

Cambiar el contrato no es parte del día a día. Si hace falta, se cambia
primero `docs/contrato-de-datos.md`, luego los esquemas y por último la skill
y el validador, en ese orden, en commits separados y subiendo la versión.

## Cómo se recolecta

La parte mecánica de la pasada es una sola llamada. Lee el catálogo, normaliza
cada publicación al contrato, calcula `id` y `dedup_key`, deduplica contra el
día anterior, ordena, cuenta y escribe:

```bash
python3 tools/recolector.py \
  --fecha 2026-09-16 \
  --fixtures "$TRABAJO" \
  --anterior data/snapshots/2026-09-15.json \
  --salida data/snapshots/2026-09-16.json \
  --resumenes "$TRABAJO/resumenes.json"
```

| Opción | Para qué |
|---|---|
| `--fecha` | Día del snapshot en UTC. Obligatoria. |
| `--fuente` | Limita la pasada a una fuente. Repetible. |
| `--fixtures` | Directorio con la respuesta de cada subagente, un archivo por `source`. |
| `--red` | Lee los feeds del catálogo en vez del directorio de trabajo. |
| `--anterior` / `--salida` | Snapshot anterior con el que deduplicar y archivo a escribir. |
| `--resumenes` | JSON con el texto editorial, indexado por URL o por `id`. `-` lee de la entrada estándar. |
| `--dry-run` | Informa qué haría sin escribir nada. |

Es determinista: con las mismas entradas produce los mismos bytes, así que
repetir una pasada no genera diff. Lo que el recolector **no** hace es decidir
qué merece entrar ni redactar resúmenes; eso sigue siendo del modelo, y el
reparto está en la tabla del principio de la skill.

## Cómo se mide el ahorro

`docs/medicion-de-tokens.md` compara la misma tarea con y sin el recolector,
con las órdenes exactas para rehacer la cuenta. A 2026-09-16 el snapshot pasa
de 7 562 a 79 tokens, un 99,0 % menos. Cuando cambie el tool o el contrato, se
vuelve a medir y se actualiza ese documento: una cifra vieja ahí es peor que
ninguna.

## Cómo validar

El validador es la comprobación oficial. Revisa los campos obligatorios
—incluidos los anidados de `evidence`—, las listas cerradas, el formato de las
fechas, que `dedup_key` corresponda a `source` más la URL canónica, que no se
repitan ni los `id` ni las claves, que `item_count` cuadre, que el nombre del
archivo coincida con `snapshot_date` y que los descartes de `dedup` no estén
también en `items`.

```bash
# Un snapshot contra el contrato
python3 .codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py \
  data/snapshots/2026-09-15.json

# Además, la deduplicación contra el día anterior
python3 .codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py \
  data/snapshots/2026-09-15.json --previous data/snapshots/2026-09-14.json
```

Con `--previous` comprueba también que ninguna clave del día anterior
reaparezca en `items`, que cada descarte declarado exista de verdad en ese
snapshot y que `dedup.previous_snapshot` nombre el archivo correcto.

Sale con código 0 si todo cumple y con 1 listando los errores, uno por línea.
El snapshot del día se valida **con** `--previous` siempre que exista un día
anterior; sin él, solo el primero de todos.

## Manejo de errores y fallback

Una fuente que falla no puede convertirse ni en un hueco silencioso ni en un
dato inventado:

| Qué pasó | Qué se hace |
|---|---|
| La fuente no responde o agota el tiempo de espera | Se reintenta una vez; si falla otra vez, se sigue con la siguiente y se anota en el resumen de la pasada que ese día no entró. No se escribe ninguna entrada por ella. |
| La fuente responde pero no publicó nada | No es un error: simplemente no aporta entradas. |
| Responde a medias (llega el listado pero no el cuerpo, el PDF enlazado se cae) | Se escribe la entrada con lo verificado, en `status: pendiente` y con `status_note` diciendo qué falta. |
| El formato cambió y no se reconocen los campos | Se escribe lo legible, en `pendiente`, y se anota el cambio de formato. Ajustar el catálogo es un trabajo aparte, con su commit. |
| No se puede extraer ninguna cita para `evidence` | La entrada queda en `pendiente` con el motivo, nunca con una cita reescrita a mano. |
| No queda ninguna entrada en todo el día | Se informa y **no se escribe el archivo**: el contrato exige al menos una entrada, y un snapshot vacío no es un día sin noticias, es una pasada fallida. |
| Un subagente no responde | Sus fuentes quedan fuera ese día y se anota; los otros tres siguen, porque no hay dependencias entre ellos. Lo que no se recogió entra al día siguiente sin duplicarse, porque la clave decide. |
| El recolector deja una entrada sin escribir | Lo dice como aviso, con el motivo. La causa habitual es que la fuente no devolvió ninguna frase citable: se vuelve a la fuente, no se redacta la evidencia. |
| El validador reporta errores | Se corrigen y se vuelve a validar. Un snapshot no se commitea con el validador en rojo. |

La regla que gobierna todas: **nunca se inventa nada**. Ante la duda, la
entrada queda en `pendiente` con su nota, que es información útil, en lugar de
completa y falsa, que es ruido.

## Criterios de "hecho" para un snapshot

1. El archivo está en `data/snapshots/` y su nombre coincide con
   `snapshot_date`.
2. Todas las entradas traen los campos obligatorios del contrato, incluidos
   `evidence`, `dedup_key` y `status`.
3. Ni los `id` ni las `dedup_key` se repiten dentro del archivo.
4. Cada entrada en `pendiente` o `descartado` explica por qué en `status_note`.
5. `published_at`, `collected_at` y `generated_at` están en UTC con el formato
   `YYYY-MM-DDTHH:MM:SSZ`.
6. `category`, `source_type` y `status` salen de sus listas cerradas, y
   `source` está escrito igual que en el catálogo de fuentes.
7. `items` va de la publicación más reciente a la más antigua y `item_count`
   coincide con el número de entradas.
8. `dedup.previous_snapshot` nombra el snapshot anterior y `dedup.discarded`
   registra cada hecho que se dejó fuera por repetido.
9. El validador sale con código 0, con `--previous` si hay día anterior.
10. El archivo lo escribió el recolector, no una edición a mano: volver a
    correrlo con las mismas entradas no cambia ni un byte.
11. Los avisos de la pasada están revisados: una fuente caída o una entrada sin
    cita son información que va en el resumen, no algo que se deja pasar.
12. Cada entrada `procesado` tiene su `summary` en español, que es lo único del
    archivo que no puede salir de un programa.
13. Hay un commit `data:` que contiene ese archivo y nada más.
