# Plan de persistencia

Hoy el radar vive en archivos: un JSON por día en `data/snapshots/`,
comparables entre sí porque todos siguen el contrato 2.0. Eso alcanza para
leer un día, pero no para preguntar por varios. «Qué publicó Mistral este
trimestre» o «cuántas entradas siguen en `pendiente`» obliga hoy a abrir todos
los archivos y recorrerlos a mano.

Este documento define el modelo relacional con el que esos snapshots se
vuelcan a Supabase, y describe el administrador editorial que va a gobernar el
catálogo de fuentes desde Notion.

El archivo sigue siendo la fuente de verdad. La base de datos es una copia
consultable: si se borrara entera, se reconstruye volviendo a cargar los
snapshots, sin perder un solo campo. Por eso las columnas se llaman como los
campos del contrato y no se inventa ninguna que el JSON no tenga.

## Tabla `fuentes`

Es el catálogo de `.codex/skills/recolectar-noticias-ia/references/fuentes.md`
en forma de tabla. La clave primaria es el propio `source`, que el contrato ya
define como identificador estable y para siempre: no hace falta un entero
autoincremental que no significa nada.

| Columna | Tipo | Nulo | Descripción |
|---|---|---|---|
| `source` | `text` | no | Clave primaria. Identificador del catálogo, en minúsculas y con guiones (`openai-blog`). |
| `nombre` | `text` | no | Nombre legible de la fuente (`OpenAI Blog`). |
| `source_type` | `text` | no | Tipo de fuente, de la lista cerrada del contrato. |
| `url` | `text` | no | Página que se abre para verificar una entrada a mano. |
| `feed` | `text` | sí | Atom o RSS que lee el recolector con `--red`. Nulo si la fuente no publica feed. |
| `revision` | `text` | no | Cada cuánto se revisa: `diaria` o `semanal`. |
| `activa` | `boolean` | no | Si la fuente entra en la pasada del día. Una fuente retirada no se borra: se desactiva, porque los snapshots viejos siguen apuntando a ella. |
| `created_at` | `timestamptz` | no | Momento en que la fila entró a la base. |

## Tabla `lanzamientos`

Una fila por cada entrada de `items`. Las columnas son los campos del contrato
en el mismo orden, con dos ajustes: el objeto `evidence` se abre en dos
columnas, porque una base relacional no gana nada guardando un objeto de dos
campos, y `tags` se guarda como arreglo de texto.

| Columna | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id` | `text` | no | Clave primaria. El `id` del contrato: `<fecha>-<source>-<titulo-corto>`. |
| `title` | `text` | no | Título en el idioma original. |
| `url` | `text` | no | Enlace canónico a la publicación original. |
| `source` | `text` | no | Identificador de la fuente. Referencia a `fuentes.source`. |
| `source_type` | `text` | no | Tipo de fuente, de la lista cerrada. |
| `category` | `text` | no | Categoría temática, de la lista cerrada. |
| `published_at` | `timestamptz` | no | Fecha y hora de publicación, en UTC. |
| `collected_at` | `timestamptz` | no | Fecha y hora en que se recolectó, en UTC. |
| `evidence_url` | `text` | no | Enlace a la fuente primaria de la cita. |
| `evidence_quote` | `text` | no | Cita textual copiada de esa página. |
| `dedup_key` | `text` | no | Clave de deduplicación, única en toda la tabla. |
| `status` | `text` | no | `pendiente`, `procesado` o `descartado`. |
| `status_note` | `text` | sí | Motivo del estado. Obligatorio cuando el estado no es `procesado`. |
| `summary` | `text` | sí | Resumen en español. Nulo cuando la entrada no lo tiene. |
| `tags` | `text[]` | no | Etiquetas libres. Arreglo vacío cuando no hay ninguna. |
| `created_at` | `timestamptz` | no | Momento en que la fila entró a la base. |

### La relación entre las dos tablas

`lanzamientos.source` apunta a `fuentes.source`: cada entrada pertenece a una
y solo una fuente del catálogo, y una fuente tiene muchas entradas a lo largo
de los días. Es la única relación del modelo.

En `db/supabase/schema.sql` esa relación está descrita pero todavía no
declarada como clave foránea, así que por ahora nada impide insertar un
lanzamiento con un `source` que no exista en el catálogo.

### Cómo se vuelca un snapshot

Un snapshot es la foto de un día; la base guarda la serie completa. El volcado
es directo:

- Cada elemento de `items` se convierte en una fila de `lanzamientos`, campo a
  campo, con `evidence.url` y `evidence.quote` en sus dos columnas.
- El `source` de cada entrada ya existe en `fuentes`, porque el catálogo se
  carga antes que cualquier snapshot.
- La unicidad de `dedup_key` traslada a la base la regla de deduplicación
  entre días: un hecho que ya está registrado no puede volver a entrar,
  aunque la pasada lo traiga otra vez.
- El bloque `dedup` y los metadatos del día —`version`, `snapshot_date`,
  `generated_at`, `item_count`— no tienen tabla en esta primera pasada: se
  quedan en el archivo. La fecha del día se puede reconstruir desde
  `collected_at` de cada entrada, pero los descartes por clave repetida no,
  y eso es una pérdida que habrá que resolver antes de dar la carga por buena.

## El administrador editorial en Notion

El catálogo de fuentes es lo único del repositorio que cambia por criterio
editorial y no por la pasada del día: agregar un blog que empezó a publicar,
retirar uno que lleva meses en silencio, marcar cuál toca revisar.

La idea es llevar esa tabla a una base de datos de Notion y conectarla con
Codex mediante MCP, para que el agente la lea al empezar la pasada en lugar de
leer el archivo. El administrador gobernaría el alta y la baja de fuentes y el
estado de revisión de cada una: quién la propuso, si ya se comprobó que es
primaria y que publica seguido, y si está activa. Ahí encaja porque es una
decisión que se toma entre personas, con comentarios y un historial que no
cabe en un diff; el repositorio se queda con lo que sí es contrato, el
identificador `source`, que no puede cambiar nunca.

El servidor MCP todavía no está configurado y la base de Notion todavía no
existe: por ahora el catálogo se sigue editando a mano en el archivo del
repositorio, que es el único origen que la skill conoce.

## Riesgos

Tener el catálogo de fuentes en dos sitios —el archivo del repositorio y la
base— abre la puerta a que dejen de coincidir sin que nadie se entere.

Una carga que se interrumpa a la mitad puede dejar el día escrito por partes
en la base mientras el archivo sigue completo y válido.
