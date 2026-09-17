# Subagentes del radar

La fase *Buscar* ya no la hace un solo agente recorriendo diez fuentes en fila.
Las fuentes se reparten por tipo entre cuatro subagentes que corren a la vez,
cada uno con su propio contexto y su propio nivel de razonamiento. Sus
definiciones están en `.codex/agents/`.

El reparto es por tipo porque un changelog y un reglamento no se leen igual:
uno llega estructurado y solo hay que copiarlo bien, el otro exige distinguir
un acto nuevo de una corrección de errores. Un agente único llevaría siempre
encima las instrucciones del caso difícil aunque estuviera leyendo el fácil, y
las diez fuentes se acumularían en un mismo contexto.

## Arquitectura en paralelo

```
                     orquestador (la skill)
                             │
          ┌──────────┬───────┴────────┬──────────────┐
          ▼          ▼                ▼              ▼
    blogs-      changelogs-      investigacion   regulacion
    oficiales   y-releases
    5 fuentes   3 fuentes        1 + derivadas   1 fuente
          │          │                │              │
          └──────────┴───────┬────────┴──────────────┘
                             ▼
            $TMPDIR/radar-<fecha>/<source>.json
                             ▼
                   tools/recolector.py
                             ▼
              data/snapshots/<fecha>.json
```

Los cuatro arrancan a la vez y no se hablan entre ellos. La pasada dura lo que
tarde el más lento, no la suma de los cuatro.

### Qué manda el orquestador a cada uno

Lo mínimo para hacer su trabajo: la fecha del snapshot en UTC, las filas del
catálogo que le tocan y su propia definición. Nada más.

Ninguno recibe el snapshot anterior, ni las fuentes de los otros, ni el
contrato de datos completo, ni los resúmenes. No lo necesitan: no deduplican
—eso ocurre después, con la clave— y no escriben el archivo final. Un
subagente que recibiera el snapshot anterior cargaría 6 KB en cada pasada para
no usarlos.

### Qué devuelve cada uno

El mismo JSON: `source` y una lista de `items` con `title`, `url`,
`published_at`, `section`, `quote` y `evidence_url` cuando difiere. Es la forma
que lee `tools/recolector.py`, así que la salida del subagente entra en el
recolector sin traducción intermedia. Los ejemplos de `tools/fixtures/` son
exactamente eso: las respuestas de los cuatro subagentes del 2026-09-16.

### Cómo se juntan los resultados

El orquestador deja cada respuesta en el directorio de trabajo del día, un
archivo por `source`, y llama al recolector una sola vez. La unión ocurre ahí,
y la deduplicación es por `dedup_key`:

1. **Dentro del día.** Dos subagentes pueden traer la misma publicación —pasa
   cuando un blog oficial anuncia un trabajo y `blogs-oficiales` se lo deriva a
   `investigacion`—. Misma URL canónica, misma clave: el recolector conserva
   una.
2. **Contra el día anterior.** Si la clave ya estaba en el snapshot previo, el
   hecho no vuelve a `items`: se anota en `dedup.discarded`.

La clave mide identidad de publicación, no parecido temático. Dos subagentes
que traigan el mismo hecho con URLs distintas **no** se resuelven aquí: eso es
la fase *Priorizar*, y sigue siendo criterio del modelo.

### Cuando uno falla

Un subagente que no responde, agota el tiempo o devuelve algo ilegible deja
fuera sus fuentes y se anota en el reporte de la pasada. Los otros tres siguen:
no hay dependencias entre ellos, así que no hay nada que rehacer.

El snapshot de ese día sale más corto y lo dice. Al día siguiente, cuando la
fuente vuelva a listar lo que no se recogió, entrará con normalidad, y lo que
sí se había recogido no se duplicará porque su clave ya está registrada. La
deduplicación por clave es lo que hace que una pasada incompleta se arregle
sola en la siguiente.

Si fallan los cuatro, no hay pasada: el recolector no escribe un archivo vacío,
porque el contrato exige al menos una entrada y un snapshot vacío no es un día
sin noticias, es una recolección fallida.

## Nivel de razonamiento por subagente

| Subagente | Nivel | Por qué ese nivel |
|---|---|---|
| `changelogs-y-releases` | `low` | La entrada ya viene estructurada: versión, fecha y notas en campos fijos. El trabajo es copiar sin alterar y respetar el fragmento de la URL. No hay nada que interpretar, y subir el nivel solo añadiría latencia. |
| `blogs-oficiales` | `medium` | Hay un juicio acotado y repetido: separar el anuncio del repaso o la nota de posicionamiento, y elegir el enlace primario cuando el post remite a un informe o a un repositorio. Es una decisión binaria con criterios escritos, no un análisis. |
| `investigacion` | `high` | Hay que leer lo que un trabajo afirma, distinguirlo de lo que el boletín dice que afirma y elegir la frase que sostiene el titular sin exagerarlo. Es la única tarea del reparto donde equivocarse produce una entrada plausible y falsa en vez de un error visible. |
| `regulacion` | `high` | Texto legal con ambigüedad deliberada: distinguir un acto de su corrección de errores, una consulta abierta de una norma en vigor, y a quién obliga cada plazo. El costo de leerlo mal no se nota en el snapshot, se nota después. |

El criterio es el mismo en los cuatro casos: el nivel lo fija **el costo de
equivocarse**, no el tamaño del texto. Donde un error se ve enseguida —una
versión mal copiada no cuadra con el repositorio— basta con `low`. Donde un
error produce algo que parece correcto, hace falta `high`.

## Costo y latencia del reparto

Los dos subagentes caros son también los que menos corren: `import-ai` y
`diario-oficial-ue` son de revisión semanal según el catálogo, así que una
pasada diaria normal solo despierta a `blogs-oficiales` y
`changelogs-y-releases`, que son los baratos. El día de la revisión semanal se
suman los dos de `high`, y ese día la pasada cuesta y tarda más.

En latencia el reparto gana siempre: cuatro contextos en paralelo terminan en
el tiempo del más lento. El que más tarda es `investigacion`, que abre los
trabajos que cita el boletín, y precisamente por correr en paralelo no arrastra
a los otros tres.

Lo que el reparto cuesta es mantenimiento: cuatro definiciones que hay que
tocar cuando se agrega una fuente, en vez de un prompt. La regla para no
multiplicarlos es la misma que para las skills: un subagente nuevo se justifica
cuando su forma de leer es distinta, no cuando solo cambia el dominio.
