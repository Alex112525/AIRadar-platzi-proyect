# Catálogo de fuentes

Lista cerrada de fuentes que revisa el radar. La columna **`source`** es el
valor exacto que se escribe en el campo `source` de cada noticia: se copia de
aquí, no se reescribe.

| `source` | `source_type` | URL | Revisión |
|---|---|---|---|
| `OpenAI Blog` | `blog_oficial` | https://openai.com/news/ | diaria |
| `Anthropic Changelog` | `changelog` | https://docs.anthropic.com/en/release-notes/overview | diaria |
| `Google DeepMind Blog` | `blog_oficial` | https://deepmind.google/discover/blog/ | diaria |
| `Meta AI Blog` | `blog_oficial` | https://ai.meta.com/blog/ | diaria |
| `Mistral AI News` | `blog_oficial` | https://mistral.ai/news/ | diaria |
| `Hugging Face Blog` | `blog_oficial` | https://huggingface.co/blog | diaria |
| `GitHub · vllm-project/vllm` | `repositorio` | https://github.com/vllm-project/vllm/releases | diaria |
| `GitHub · huggingface/transformers` | `repositorio` | https://github.com/huggingface/transformers/releases | diaria |
| `Diario Oficial de la UE` | `boletin_regulatorio` | https://eur-lex.europa.eu/oj/direct-access.html | semanal |
| `Import AI` | `newsletter` | https://importai.substack.com/ | semanal |

## Cómo se eligieron

El criterio es que la fuente sea **primaria**: quien publica es quien hizo el
lanzamiento o quien emite la norma. Por eso el catálogo está formado por blogs
oficiales, changelogs, páginas de versiones de repositorios y publicaciones de
organismos públicos. Los medios que reescriben esas notas quedan fuera: de lo
contrario el radar acabaría lleno de duplicados del mismo hecho.

Las dos excepciones son `Import AI` y el `Diario Oficial de la UE`. El boletín
entra porque cubre investigación que no tiene blog oficial, y en ese caso la
entrada enlaza el artículo original que el boletín cita, no el boletín. El
diario oficial entra porque es la fuente primaria de lo regulatorio.

## Cómo agregar una fuente

1. Comprueba que es primaria y que publica al menos una vez al mes.
2. Agrega la fila a esta tabla eligiendo un `source` corto y estable. Ese
   nombre ya no se cambia: los snapshots anteriores seguirían escritos con el
   nombre viejo.
3. Elige el `source_type` de la lista cerrada del contrato de datos.
4. Menciona el cambio en el mensaje del commit, porque a partir de ese día los
   snapshots dejan de ser comparables con los anteriores en número de fuentes.
