# Catálogo de fuentes

Lista cerrada de fuentes que revisa el radar. La columna **`source`** es el
identificador exacto que se escribe en el campo `source` de cada noticia: se
copia de aquí, no se reescribe. Es un identificador en minúsculas y con
guiones, no el nombre comercial; el nombre legible va en la columna siguiente,
solo para leerlo.

La fase *Buscar* de la skill solo visita los dominios de esta tabla: un
dominio que no está aquí no se consulta hasta que se agregue con su commit.

| `source` | Nombre | `source_type` | URL | Revisión |
|---|---|---|---|---|
| `openai-blog` | OpenAI Blog | `blog_oficial` | https://openai.com/news/ | diaria |
| `anthropic-changelog` | Anthropic Changelog | `changelog` | https://docs.anthropic.com/en/release-notes/overview | diaria |
| `google-deepmind-blog` | Google DeepMind Blog | `blog_oficial` | https://deepmind.google/discover/blog/ | diaria |
| `meta-ai-blog` | Meta AI Blog | `blog_oficial` | https://ai.meta.com/blog/ | diaria |
| `mistral-ai-news` | Mistral AI News | `blog_oficial` | https://mistral.ai/news/ | diaria |
| `hugging-face-blog` | Hugging Face Blog | `blog_oficial` | https://huggingface.co/blog | diaria |
| `github-vllm` | GitHub · vllm-project/vllm | `repositorio` | https://github.com/vllm-project/vllm/releases | diaria |
| `github-transformers` | GitHub · huggingface/transformers | `repositorio` | https://github.com/huggingface/transformers/releases | diaria |
| `diario-oficial-ue` | Diario Oficial de la UE | `boletin_regulatorio` | https://eur-lex.europa.eu/oj/direct-access.html | semanal |
| `import-ai` | Import AI | `newsletter` | https://importai.substack.com/ | semanal |

## Cómo se eligieron

El criterio es que la fuente sea **primaria**: quien publica es quien hizo el
lanzamiento o quien emite la norma. Por eso el catálogo está formado por blogs
oficiales, changelogs, páginas de versiones de repositorios y publicaciones de
organismos públicos. Los medios que reescriben esas notas quedan fuera: de lo
contrario el radar acabaría lleno de duplicados del mismo hecho.

Las dos excepciones son `import-ai` y `diario-oficial-ue`. El boletín entra
porque cubre investigación que no tiene blog oficial, y en ese caso la entrada
enlaza el artículo original que el boletín cita, no el boletín; una entrada de
`import-ai` que apunte al propio boletín está mal armada y se marca
`descartado`. El diario oficial entra porque es la fuente primaria de lo
regulatorio.

## Sobre `source` y la deduplicación

`source` es la primera mitad de la `dedup_key` de cada noticia
(`<source>:<digesto de la URL canónica>`). Dos grafías distintas de la misma
fuente producirían dos claves distintas para el mismo hecho y romperían la
deduplicación entre días. Por eso el identificador es una cadena fija y no un
nombre que cada pasada pueda escribir a su manera.

## Cómo agregar una fuente

1. Comprueba que es primaria y que publica al menos una vez al mes.
2. Agrega la fila eligiendo un `source` corto y estable, en minúsculas y con
   guiones. Ese identificador ya no se cambia: los snapshots anteriores
   seguirían escritos con el viejo y sus claves dejarían de cuadrar.
3. Elige el `source_type` de la lista cerrada del contrato de datos.
4. Menciona el cambio en el mensaje del commit, porque a partir de ese día los
   snapshots dejan de ser comparables con los anteriores en número de fuentes.
