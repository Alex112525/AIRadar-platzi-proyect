---
name: recolectar-noticias-ia
description: Recolecta las noticias y lanzamientos de IA del día a partir del catálogo de fuentes del radar y escribe el snapshot diario en data/snapshots/. Úsala cuando haya que generar el snapshot de un día, rehacerlo o agregarle una fuente nueva.
---

# Recolectar noticias de IA

## Propósito

Convertir lo publicado hoy por las fuentes del catálogo en un snapshot diario
que cumpla el contrato de datos 1.0. La skill existe para que la recolección
sea siempre la misma: mismas fuentes, mismos campos, mismo formato de archivo,
sin decidir nada nuevo cada mañana.

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

## Procedimiento

1. Fija la fecha del snapshot en UTC. Ese valor es `snapshot_date` y también
   el nombre del archivo.
2. Lee `references/fuentes.md` y recorre las fuentes en el orden de la tabla.
3. En cada fuente, toma las publicaciones de las últimas 24 horas.
4. Descarta lo que el contrato no considera noticia: opiniones, hilos de redes
   sociales y notas que reescriben a otra fuente. Ante la duda, conserva solo
   la publicación primaria.
5. Arma cada entrada con los campos del contrato. Dos cuidados que suelen
   fallar: `source` se copia literal del catálogo, y `category` sale de la
   lista cerrada del contrato, nunca inventada.
6. Ordena las entradas por `published_at` de la más reciente a la más antigua.
7. Envuélvelas en el objeto del snapshot: `version` `"1.0"`, `snapshot_date`,
   `generated_at` con el instante de cierre en UTC, `item_count` con el número
   de entradas e `items`.
8. Escribe `data/snapshots/<snapshot_date>.json` con sangría de dos espacios y
   sin reordenar las claves.
9. Valida el archivo y corrige lo que reporte antes de seguir:

   ```bash
   python3 .codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py data/snapshots/<snapshot_date>.json
   ```

10. Haz un commit con el mensaje `data: snapshot <snapshot_date>`.

## Salidas

- `data/snapshots/<snapshot_date>.json`, válido contra el contrato 1.0.
- Un commit con ese archivo.
- Un resumen en la conversación: cuántas entradas quedaron y de qué fuentes.

## Archivos de la skill

| Archivo | Para qué sirve |
|---|---|
| `.codex/skills/recolectar-noticias-ia/references/fuentes.md` | Catálogo de fuentes y el nombre canónico de cada una. |
| `.codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py` | Valida un snapshot contra el contrato. Sale con 0 si está bien. |
