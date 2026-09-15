# Contrato de datos del radar

Este documento define qué es una noticia para AIRadar y cómo debe verse un
snapshot diario. Es la referencia de la que dependen los esquemas de
`schemas/`, la skill de recolección y cualquier consumidor posterior del
repositorio.

Versión del contrato: **1.0**.

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
| `source` | string | sí | Nombre de la fuente, tomado tal cual del catálogo. |
| `source_type` | string | sí | Tipo de fuente. Valores cerrados (ver abajo). |
| `category` | string | sí | Categoría temática. Valores cerrados (ver abajo). |
| `published_at` | string | sí | Fecha y hora de publicación en UTC. |
| `collected_at` | string | sí | Fecha y hora en que Codex recolectó la entrada, en UTC. |
| `summary` | string | no | Resumen propio en español, una o dos frases, máximo 280 caracteres. |
| `tags` | array de string | no | Etiquetas libres en minúsculas para filtrar después. |

### Reglas

1. **`id` estable y único.** Se construye como
   `YYYY-MM-DD-fuente-titulo-corto`, en minúsculas y con guiones: por ejemplo
   `2026-09-14-openai-responses-batch`. La fecha es la de publicación. El
   mismo hecho debe producir siempre el mismo `id`, de modo que una noticia
   recolectada dos veces se reconozca como la misma. Dentro de un snapshot no
   puede haber dos `id` iguales.
2. **`source` es un identificador, no un texto libre.** Se escribe exactamente
   igual siempre para la misma fuente y se copia del catálogo en
   `.codex/skills/recolectar-noticias-ia/references/fuentes.md`. Dos grafías
   distintas de la misma fuente cuentan como dos fuentes al agrupar.
3. **Fechas en UTC y con formato fijo.** `published_at` y `collected_at` usan
   `YYYY-MM-DDTHH:MM:SSZ`. Si la fuente publica solo la fecha, se usa
   `T00:00:00Z`. `snapshot_date` usa `YYYY-MM-DD`.
4. **`summary` es opcional de verdad.** Si no hay resumen, el campo se omite;
   no se escribe una cadena vacía.
5. **`url` apunta a la fuente primaria** y se guarda sin parámetros de
   seguimiento (`utm_*`, `ref`, etc.).
6. **Idioma.** `title` se conserva en el idioma original; `summary` y `tags`
   se escriben en español.

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

Una noticia tiene exactamente una categoría: se elige la que describe el hecho
principal. Lo demás se expresa con `tags`.

## Entidad `snapshot`

Un snapshot es la foto de un día. Se guarda en
`data/snapshots/YYYY-MM-DD.json` y hay como máximo uno por día. Cubre lo que
se recolectó ese día, que puede incluir publicaciones de la víspera si la
fuente las sacó después de la pasada anterior.

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `version` | string | sí | Versión del contrato con la que se generó. |
| `snapshot_date` | string | sí | Día que cubre el snapshot, en `YYYY-MM-DD`. |
| `generated_at` | string | sí | Momento en que se cerró el snapshot, en UTC. |
| `item_count` | integer | sí | Número de entradas en `items`. |
| `items` | array de `noticia` | sí | Entradas del día, al menos una. |

### Reglas

1. `item_count` debe coincidir con la longitud de `items`.
2. El nombre del archivo debe coincidir con `snapshot_date`.
3. `items` se ordena por `published_at` descendente: lo más reciente primero.
4. Un snapshot ya publicado no se reescribe. Si hay que corregirlo, se hace un
   commit nuevo que explique la corrección en el mensaje.

## Ejemplo mínimo

```json
{
  "version": "1.0",
  "snapshot_date": "2026-09-14",
  "generated_at": "2026-09-14T21:10:00Z",
  "item_count": 1,
  "items": [
    {
      "id": "2026-09-14-openai-responses-batch",
      "title": "Batch processing for the Responses API",
      "url": "https://openai.com/index/batch-processing-responses-api/",
      "source": "OpenAI Blog",
      "source_type": "blog_oficial",
      "category": "api",
      "published_at": "2026-09-14T17:30:00Z",
      "collected_at": "2026-09-14T21:04:00Z",
      "summary": "La API de respuestas acepta envíos por lotes con resultados diferidos y un precio menor por token que las llamadas en línea.",
      "tags": ["api", "costos", "openai"]
    }
  ]
}
```

El snapshot completo de referencia está en `data/snapshots/2026-09-14.json`.
