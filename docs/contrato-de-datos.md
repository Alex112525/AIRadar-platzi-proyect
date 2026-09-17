# Contrato de datos del radar

Define qué es una noticia para AIRadar y cómo se ve el archivo de un día. De
aquí salen los esquemas de `schemas/` y el formato de lo que hay en
`data/snapshots/`.

Versión del contrato: 1.0.

## Entidad `noticia`

Una noticia es un hecho publicado por alguna de las fuentes del catálogo: el
lanzamiento de un modelo, un cambio en una API, una versión de una herramienta
de código abierto, un resultado de investigación o una novedad regulatoria.
No cuentan las opiniones, los hilos de redes sociales ni las notas de prensa
que reescriben a otra fuente.

### Campos

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `id` | string | sí | Identificador de la entrada dentro del snapshot. |
| `title` | string | sí | Título de la publicación, en su idioma original. |
| `url` | string | sí | Enlace a la publicación. |
| `source` | string | sí | Fuente de la que salió la noticia. |
| `published_at` | string | sí | Fecha y hora de publicación, en UTC. |
| `summary` | string | sí | Resumen corto en español, una o dos frases. |
| `tags` | array de string | sí | Etiquetas en minúsculas para filtrar después. |
| `category` | string | no | Categoría temática: `modelo`, `api`, `herramienta_open_source`, `investigacion`, `regulacion` o `producto`. |

### Reglas

1. El `id` se arma como `<fecha>-<fuente>-<titulo-corto>`, en minúsculas y con
   guiones, y no se repite dentro del mismo archivo.
2. `published_at` se escribe en UTC con el formato `YYYY-MM-DDTHH:MM:SSZ`. Si
   la fuente publica solo el día, se usa `T00:00:00Z`.
3. `url` apunta a la publicación original, sin parámetros de seguimiento.
4. `title` se conserva en el idioma original; `summary` y `tags` se escriben
   en español.
5. Hay que evitar repetidos: un hecho que ya salió en un snapshot anterior no
   se vuelve a anotar.

## Entidad `snapshot`

Un snapshot es la foto de un día. Se guarda en
`data/snapshots/YYYY-MM-DD.json` y hay uno por día.

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `version` | string | sí | Versión del contrato con la que se generó. Hoy `"1.0"`. |
| `snapshot_date` | string | sí | Día que cubre el snapshot, en `YYYY-MM-DD`. |
| `generated_at` | string | sí | Momento en que se cerró el archivo, en UTC. |
| `item_count` | integer | sí | Número de entradas de `items`. |
| `items` | array de `noticia` | sí | Las noticias del día, al menos una. |

Además: `item_count` coincide con la cantidad de entradas, el nombre del
archivo coincide con `snapshot_date` e `items` va de la publicación más
reciente a la más antigua.

## Los esquemas

`schemas/noticia.schema.json` describe una noticia y
`schemas/snapshot.schema.json` describe el archivo del día. Los dos están
escritos en JSON Schema draft 2020-12.

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
      "published_at": "2026-09-14T17:30:00Z",
      "category": "api",
      "summary": "La API de respuestas acepta envíos por lotes con resultados diferidos y un precio menor por token que las llamadas en línea.",
      "tags": ["api", "costos", "openai"]
    }
  ]
}
```
