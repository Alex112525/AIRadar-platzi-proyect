# Contrato de datos del radar

Define qué es una noticia para AIRadar y cómo debe verse un snapshot diario.
Es la referencia de la que dependen los esquemas de `schemas/`, la skill de
recolección y cualquier consumidor posterior del repositorio.

Versión del contrato: **2.0**. La 1.0 no tenía evidencia, clave de
deduplicación ni estado; los snapshots del repositorio se reescribieron a la
2.0 porque son ejemplos de referencia, no registro histórico.

## Entidad `noticia`

Una noticia es un hecho publicado por una fuente del catálogo: el lanzamiento
de un modelo, un cambio en una API, una versión de una herramienta de código
abierto, un resultado de investigación o una novedad regulatoria.

Una noticia **no** es una opinión, un hilo de redes sociales ni una nota de
prensa secundaria que reescribe a otra fuente. Siempre se enlaza la fuente
primaria.

### Campos

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `id` | string | sí | Identificador estable y único dentro del snapshot. |
| `title` | string | sí | Título en el idioma original, sin editar. Máximo 200 caracteres. |
| `url` | string | sí | Enlace canónico a la publicación original. |
| `source` | string | sí | **Fuente**: identificador estable del catálogo, en minúsculas y con guiones (`openai-blog`). |
| `source_type` | string | sí | Tipo de fuente. Lista cerrada (ver abajo). |
| `category` | string | sí | Categoría temática. Lista cerrada (ver abajo). |
| `published_at` | string | sí | **Fecha** y hora de publicación en UTC. |
| `collected_at` | string | sí | Fecha y hora en que Codex recolectó la entrada, en UTC. |
| `evidence` | object | sí | **Evidencia**: `{ "url": …, "quote": … }`. Ver abajo. |
| `dedup_key` | string | sí | **Clave de deduplicación**. Ver abajo. |
| `status` | string | sí | **Estado**: `pendiente`, `procesado` o `descartado`. Ver abajo. |
| `status_note` | string | condicional | Motivo del estado. Obligatorio si el estado es `pendiente` o `descartado`; ausente si es `procesado`. Máximo 300 caracteres. |
| `summary` | string | no | Resumen propio en español, una o dos frases, máximo 280 caracteres. |
| `tags` | array de string | no | Etiquetas libres en minúsculas para filtrar después. |

No se admiten campos fuera de esta tabla: los dos esquemas declaran
`additionalProperties: false` y el validador rechaza cualquier extra. Un dato
que no cabe en el contrato es señal de que hay que cambiar el contrato, no de
que haya que colarlo en el JSON.

### `evidence` — la prueba que sostiene el titular

Objeto con dos campos, ambos obligatorios:

| Campo | Tipo | Descripción |
|---|---|---|
| `url` | string | Enlace a la **fuente primaria** de la que sale la cita. Casi siempre coincide con el `url` de la noticia; se separan cuando la fuente del catálogo reseña a otra (el caso de `import-ai`, que debe enlazar el trabajo original). |
| `quote` | string | Cita textual corta, en el idioma original, copiada de esa página. Máximo 300 caracteres. |

La cita se copia, no se parafrasea: es lo que permite comprobar la entrada sin
volver a leer el artículo entero. Si la fuente no deja extraer ninguna frase,
la entrada no está lista y queda en `pendiente` con su motivo.

### `dedup_key` — la clave de deduplicación

```
dedup_key = "<source>:<12 primeros caracteres del SHA-256 de la URL canónica>"
```

La URL canónica se obtiene así, en este orden:

1. Se bajan a minúsculas el esquema y el host, y se quita el `www.`.
2. Se quita la barra final del camino. El camino, la consulta y el fragmento
   conservan sus mayúsculas: son sensibles a ellas.
3. Se descartan los parámetros de seguimiento (`utm_*`, `ref`, `fbclid`,
   `gclid`, `mc_cid`, `mc_eid`, `igshid`, `si`) y los que quedan se ordenan
   alfabéticamente.
4. El fragmento **sí** se conserva: en un changelog de una sola página es lo
   único que distingue una entrada de otra.

Ejemplo: `https://openai.com/index/batch-processing-responses-api/` con
`source` = `openai-blog` canoniza a
`openai.com/index/batch-processing-responses-api` y da la clave
`openai-blog:d06c82ebd6fc`. Como es determinista, el validador la recalcula y
compara: una clave que no cuadre con `source` + `url` es un error.

**Regla de deduplicación entre días.** Antes de escribir una entrada se
compara su `dedup_key` con las del snapshot anterior. Si ya estaba, el hecho
**no se vuelve a incluir en `items`**: se registra en `dedup.discarded` con la
clave, el `id` de la entrada original y el motivo. Dos hechos del mismo tema
con URL distinta no son duplicados: la clave mide identidad de publicación, no
parecido temático.

### `status` — el estado de la entrada

| Valor | Significado | Quién lo pone |
|---|---|---|
| `pendiente` | Capturada pero sin verificar del todo: la fuente respondió a medias (listado sin cuerpo, PDF caído, sin cita extraíble). No se propaga río abajo hasta revisarla. | La skill, durante la recolección, cuando se activa el fallback. |
| `procesado` | Verificada contra la fuente primaria, con cita y resumen. Estado normal de una entrada completa. | La skill cuando consiguió todo, o quien revise una `pendiente`. |
| `descartado` | No cumple el contrato como noticia (opinión, nota secundaria, enlace al agregador en vez de al original). Se conserva en el snapshot para dejar rastro de la decisión; no se propaga. | Quien revisa: una persona o una pasada posterior de la skill. |

El estado solo avanza —de `pendiente` a `procesado` o a `descartado`, nunca al
revés— y el cambio va en un commit nuevo que lo explica. Las entradas
`pendiente` y `descartado` cuentan igual en `item_count`: siguen siendo parte
de lo que se vio ese día.

**`status: descartado` y `dedup.discarded` no son lo mismo.** El primero es
una entrada que sí está en `items` y quedó marcada para no usarse. El segundo
es un hecho que **nunca entró** en `items` porque su clave ya estaba en el
snapshot anterior.

### Reglas

1. **`id` estable y único.** Se construye como
   `<fecha de publicación>-<source>-<titulo-corto>`, en minúsculas y con
   guiones: `2026-09-14-openai-blog-responses-batch`. El mismo hecho produce
   siempre el mismo `id`. Dentro de un snapshot no puede haber dos `id`
   iguales ni dos `dedup_key` iguales.
2. **`source` es un identificador, no un texto libre.** Se copia del catálogo
   en `.codex/skills/recolectar-noticias-ia/references/fuentes.md` y se
   escribe siempre igual. Dos grafías de la misma fuente contarían como dos
   fuentes al agrupar y darían claves distintas para el mismo hecho.
3. **Fechas en UTC y con formato fijo.** `published_at` y `collected_at` usan
   `YYYY-MM-DDTHH:MM:SSZ`. Si la fuente publica solo la fecha, se usa
   `T00:00:00Z`. `snapshot_date` usa `YYYY-MM-DD`.
4. **`summary` es opcional de verdad.** Si no hay resumen, el campo se omite;
   no se escribe una cadena vacía.
5. **`url` apunta a la fuente primaria**, sin parámetros de seguimiento.
6. **Idioma.** `title` y `evidence.quote` se conservan en el idioma original;
   `summary`, `status_note` y `tags` se escriben en español.

### Valores cerrados de `source_type`

| Valor | Significado |
|---|---|
| `blog_oficial` | Blog o sala de prensa de la organización que publica. |
| `changelog` | Registro de cambios de un producto o API. |
| `repositorio` | Publicación de versión en un repositorio público. |
| `newsletter` | Boletín editorial periódico. |
| `boletin_regulatorio` | Publicación oficial de un organismo público. |

### Valores cerrados de `category`

| Valor | Significado |
|---|---|
| `modelo` | Lanzamiento o actualización de un modelo. |
| `api` | Cambio en una API o en sus condiciones de uso. |
| `herramienta_open_source` | Versión de una biblioteca o herramienta abierta. |
| `investigacion` | Publicación de investigación o informe técnico. |
| `regulacion` | Norma, guía o calendario regulatorio. |
| `producto` | Funcionalidad de producto dirigida a personas usuarias. |

Una noticia tiene exactamente una categoría: la que describe el hecho
principal. Lo demás se expresa con `tags`.

## Entidad `snapshot`

Un snapshot es la foto de un día. Se guarda en
`data/snapshots/YYYY-MM-DD.json` y hay como máximo uno por día. Cubre lo que
se recolectó ese día, que puede incluir publicaciones de la víspera si la
fuente las sacó después de la pasada anterior.

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `version` | string | sí | Versión del contrato con la que se generó. Hoy `"2.0"`. |
| `snapshot_date` | string | sí | Día que cubre el snapshot, en `YYYY-MM-DD`. |
| `generated_at` | string | sí | Momento en que se cerró el snapshot, en UTC. |
| `item_count` | integer | sí | Número de entradas en `items`. |
| `items` | array de `noticia` | sí | Entradas del día, al menos una. |
| `dedup` | object | sí | Registro de la deduplicación. Ver abajo. |

### `dedup`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `previous_snapshot` | string \| null | sí | Día con el que se comparó, en `YYYY-MM-DD`. `null` solo en el primero de todos. |
| `discarded` | array | sí | Hechos que no entraron en `items` por repetidos. Lista vacía si no hubo ninguno. |

Cada elemento de `discarded` lleva `dedup_key` (la clave repetida),
`duplicate_of` (el `id` de la entrada del snapshot anterior que ya registraba
el hecho) y `reason` (por qué se volvió a ver). Ninguna clave de `discarded`
puede estar a la vez en `items`.

### Reglas

1. `item_count` coincide con la longitud de `items`.
2. El nombre del archivo coincide con `snapshot_date`.
3. `items` se ordena por `published_at` descendente: lo más reciente primero.
4. Un snapshot ya publicado no se reescribe. Si hay que corregirlo, se hace un
   commit nuevo que explique la corrección.
5. `dedup.previous_snapshot` nombra el snapshot inmediatamente anterior que
   existe en `data/snapshots/`, no una fecha cualquiera.

## Los esquemas: una definición, dos archivos

El contrato vive en dos JSON Schema draft 2020-12 que se componen:

- `schemas/noticia.schema.json` define una noticia y nada más.
- `schemas/snapshot.schema.json` define los metadatos del día, el bloque
  `dedup` y la lista `items`. **No repite la definición de una noticia: la
  referencia.** Su propiedad `items` declara
  `"items": { "$ref": "./noticia.schema.json" }`, de modo que cada elemento de
  la lista se valida contra el esquema de noticia.

Esa composición por `$ref` es la que mantiene sincronizados los dos archivos:
un campo nuevo en una noticia se agrega en un solo sitio. Ambos esquemas son
estrictos (`additionalProperties: false`, `required` completo, `format` y
`pattern` en fechas, URLs y claves) y las listas cerradas son `enum`.

## Ejemplo mínimo

```json
{
  "version": "2.0",
  "snapshot_date": "2026-09-14",
  "generated_at": "2026-09-14T21:10:00Z",
  "item_count": 1,
  "items": [
    {
      "id": "2026-09-14-openai-blog-responses-batch",
      "title": "Batch processing for the Responses API",
      "url": "https://openai.com/index/batch-processing-responses-api/",
      "source": "openai-blog",
      "source_type": "blog_oficial",
      "category": "api",
      "published_at": "2026-09-14T17:30:00Z",
      "collected_at": "2026-09-14T21:04:00Z",
      "evidence": {
        "url": "https://openai.com/index/batch-processing-responses-api/",
        "quote": "Batch requests are queued and returned within 24 hours at a lower per-token price than synchronous calls."
      },
      "dedup_key": "openai-blog:d06c82ebd6fc",
      "status": "procesado",
      "summary": "La API de respuestas acepta envíos por lotes con resultados diferidos y un precio menor por token que las llamadas en línea.",
      "tags": ["api", "costos", "openai"]
    }
  ],
  "dedup": {
    "previous_snapshot": null,
    "discarded": []
  }
}
```

Los dos snapshots completos de referencia están en
`data/snapshots/2026-09-14.json` (primer día, sin nada contra qué deduplicar)
y `data/snapshots/2026-09-15.json` (segundo día, con tres descartes por clave
repetida).
