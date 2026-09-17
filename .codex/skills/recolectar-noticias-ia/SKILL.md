---
name: recolectar-noticias-ia
description: Recolecta las noticias y lanzamientos de IA del día a partir del catálogo de fuentes del radar, las deduplica contra el snapshot anterior y escribe el snapshot diario en data/snapshots/. Úsala cuando haya que generar el snapshot de un día, rehacerlo o agregarle una fuente nueva.
---

# Recolectar noticias de IA

## Propósito

Convertir lo publicado hoy por las fuentes del catálogo en un snapshot diario
que cumpla el contrato de datos 2.0. La skill cubre el flujo entero —buscar,
priorizar, estructurar, deduplicar y guardar— para que la recolección sea
siempre la misma: mismas fuentes, mismos campos, mismo formato de archivo, sin
decidir nada nuevo cada mañana.

## Cuándo usarla

- Se pide el snapshot del día o el de una fecha concreta.
- Hay que rehacer un snapshot porque se agregó o corrigió una fuente.
- Se quiere revisar qué publicó una fuente dentro del formato del radar.

No la uses para analizar o resumir snapshots ya escritos: eso no toca el
catálogo ni produce archivos nuevos.

## Entradas

| Entrada | Origen | Por defecto |
|---|---|---|
| Fecha del snapshot | la pide quien invoca la skill | el día de hoy en UTC |
| Catálogo de fuentes | `references/fuentes.md` | — |
| Contrato de datos | `docs/contrato-de-datos.md` | — |
| Snapshot anterior | el archivo más reciente de `data/snapshots/` | ninguno, si es el primer día |

## Permisos

La skill no necesita ningún permiso permanente. Solo dos aprobaciones por
sesión, cada una pegada a la fase que la usa:

| Fase | Permiso | Alcance |
|---|---|---|
| Buscar | Acceso a la red | Únicamente los dominios que aparecen en `references/fuentes.md`. |
| Guardar | Escritura en disco | Únicamente `data/snapshots/`, más el commit local. |

Las fases *Priorizar*, *Estructurar* y *Deduplicar* no piden nada: trabajan
sobre lo que ya está en memoria y sobre archivos del repositorio, que se leen
sin aprobación. `git push`, instalar dependencias o escribir fuera de
`data/snapshots/` quedan fuera de esta skill. La política completa está en la
sección «Permisos: sesión vs. permanentes» de `AGENTS.md`.

## Procedimiento

La recolección son cinco fases en orden. Cada una recibe lo que dejó la
anterior; si una falla, se aplica su fallback y se sigue.

### Fase 1 — Buscar

- **Entra:** la fecha del snapshot en UTC y el catálogo `references/fuentes.md`.
- **Pasos:**
  1. Fija la fecha en UTC. Ese valor es `snapshot_date` y también el nombre
     del archivo.
  2. Pide la aprobación de red para los dominios del catálogo.
  3. Recorre las fuentes en el orden de la tabla y toma las publicaciones de
     las últimas 24 horas. De cada una guarda título, enlace, fecha y una
     frase literal que sirva de evidencia.
- **Fallback por fuente:** si una fuente no responde, se reintenta una vez y
  se pasa a la siguiente, anotando que ese día no entró. Si responde a medias
  o con un formato irreconocible, se conserva lo legible y la entrada nacerá
  en `pendiente`. Si no publicó nada, no es un fallo. Nunca se completa lo que
  falta desde el conocimiento propio.
- **Sale:** una lista de candidatas en bruto, cada una con su fuente de origen.

### Fase 2 — Priorizar

- **Entra:** las candidatas en bruto.
- **Pasos:**
  1. Descarta lo que el contrato no considera noticia: opiniones, hilos de
     redes sociales y notas que reescriben a otra fuente.
  2. Si dos candidatas del mismo día cuentan el mismo hecho, conserva la
     publicación primaria y descarta la que la reseña.
  3. Ordena lo que queda por `published_at`, de lo más reciente a lo más
     antiguo.
- **Sale:** la lista del día, ordenada y sin relleno.

### Fase 3 — Estructurar

- **Entra:** la lista priorizada.
- **Pasos:**
  1. Arma cada entrada con los campos del contrato. Los tres cuidados que
     suelen fallar: `source` se copia literal del catálogo, `category` sale de
     la lista cerrada, y `evidence.quote` se copia de la fuente sin
     reescribirla.
  2. Construye el `id` como `<fecha de publicación>-<source>-<titulo-corto>`.
  3. Calcula `dedup_key` como `<source>:<12 primeros caracteres del SHA-256 de
     la URL canónica>`, con la canonización que describe el contrato.
  4. Pon `status`: `procesado` si la entrada quedó verificada con su cita;
     `pendiente` si algo faltó, siempre con `status_note` diciendo qué.
  5. Escribe `summary` en español, o **omite el campo**: nunca una cadena
     vacía.
- **Sale:** las entradas ya conformes al contrato, todavía sin deduplicar.

### Fase 4 — Deduplicar

- **Entra:** las entradas estructuradas y el snapshot del día anterior.
- **Pasos:**
  1. Lee el snapshot anterior y reúne sus `dedup_key`.
  2. Para cada entrada de hoy, compara su clave con ese conjunto.
  3. Si la clave ya estaba, **saca la entrada de `items`** y anótala en
     `dedup.discarded` con `dedup_key`, el `id` de la entrada original en
     `duplicate_of` y el `reason` por el que volvió a aparecer.
  4. Comprueba que tampoco haya dos claves iguales dentro del día.
  5. Rellena `dedup.previous_snapshot` con la fecha de ese snapshot anterior,
     o `null` si es el primero de todos.
- **Ojo:** dos publicaciones del mismo tema con URL distinta **no** son
  duplicados. La clave mide identidad de publicación, no parecido temático.
- **Sale:** la lista definitiva de `items` y el bloque `dedup`.

### Fase 5 — Guardar

- **Entra:** `items`, el bloque `dedup` y la fecha del snapshot.
- **Pasos:**
  1. Pide la aprobación de escritura para `data/snapshots/`.
  2. Envuelve todo en el objeto del snapshot: `version` `"2.0"`,
     `snapshot_date`, `generated_at` con el instante de cierre en UTC,
     `item_count` con el número de entradas de `items`, `items` y `dedup`.
  3. Escribe `data/snapshots/<snapshot_date>.json` con sangría de dos espacios
     y sin reordenar las claves. Si no quedó ninguna entrada, no escribas el
     archivo: informa de la pasada fallida.
  4. Valida y corrige lo que reporte antes de seguir:

     ```bash
     python3 .codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py \
       data/snapshots/<snapshot_date>.json --previous data/snapshots/<día anterior>.json
     ```

     Sin `--previous` solo el primer día de todos.
  5. Haz un commit con el mensaje `data: snapshot <snapshot_date>`.
- **Sale:** el archivo del día, validado y commiteado.

## Salidas

- `data/snapshots/<snapshot_date>.json`, válido contra el contrato 2.0.
- Un commit con ese archivo.
- Un resumen en la conversación: cuántas entradas quedaron, de qué fuentes,
  cuántas en `pendiente` y por qué, cuántas se descartaron por repetidas y qué
  fuentes no respondieron.

## Archivos de la skill

| Archivo | Para qué sirve |
|---|---|
| `.codex/skills/recolectar-noticias-ia/references/fuentes.md` | Catálogo de fuentes y el identificador canónico de cada una. |
| `.codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py` | Valida un snapshot contra el contrato y, con `--previous`, la deduplicación entre días. Sale con 0 si está bien. |
