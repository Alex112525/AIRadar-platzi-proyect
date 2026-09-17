# Catálogo de fuentes

Estas son las fuentes que revisa el radar. La columna **Fuente** es lo que se
escribe en el campo `source` de cada noticia, y la revisión dice cada cuánto
vale la pena mirarla.

| Fuente | URL | Revisión |
|---|---|---|
| OpenAI Blog | https://openai.com/news/ | diaria |
| Anthropic Changelog | https://docs.anthropic.com/en/release-notes/overview | diaria |
| Google DeepMind | https://deepmind.google/discover/blog/ | diaria |
| Meta AI Blog | https://ai.meta.com/blog/ | diaria |
| Mistral AI | https://mistral.ai/news/ | diaria |
| Hugging Face Blog | https://huggingface.co/blog | diaria |
| GitHub vllm | https://github.com/vllm-project/vllm/releases | diaria |
| GitHub transformers | https://github.com/huggingface/transformers/releases | diaria |
| Diario Oficial de la UE | https://eur-lex.europa.eu/oj/direct-access.html | semanal |
| Import AI | https://importai.substack.com/ | semanal |

## Cómo se eligieron

El criterio es que la fuente sea primaria: quien publica es quien hizo el
lanzamiento o quien emite la norma. Por eso el catálogo son blogs oficiales,
changelogs, páginas de versiones de repositorios y publicaciones de organismos
públicos. Los medios que reescriben esas notas quedan fuera, porque el radar
acabaría lleno del mismo hecho contado varias veces.

Import AI es la excepción: entra porque cubre investigación que no tiene blog
oficial, y en ese caso la entrada enlaza el artículo original que el boletín
cita, no el boletín.

## Cómo agregar una fuente

1. Comprueba que es primaria y que publica al menos una vez al mes.
2. Agrega la fila con su URL y cada cuánto se revisa.
3. Menciona el cambio en el mensaje del commit, porque a partir de ese día los
   snapshots dejan de ser comparables con los anteriores en número de fuentes.
