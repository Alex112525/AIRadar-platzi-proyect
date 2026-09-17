---
name: recolectar-noticias-ia
description: Recolecta las noticias y lanzamientos de IA del día a partir del catálogo de fuentes del radar y escribe el snapshot diario en data/snapshots/. Úsala cuando haya que generar o rehacer el snapshot de un día.
---

# Recolectar noticias de IA

Esta skill sirve para armar el snapshot de un día con lo que publicaron las
fuentes del radar. Se usa cuando se pide el snapshot de hoy o el de una fecha
concreta.

## Cómo hacerlo

Primero hay que **buscar**. Toma la fecha del snapshot —si no te la dan, el
día de hoy en UTC— y revisa una por una las fuentes que están listadas en
`references/fuentes.md`, quedándote con lo que publicaron en las últimas 24
horas. De cada publicación anota el título, el enlace y la fecha. Deja fuera
las opiniones y las notas que reescriben a otra fuente: el enlace tiene que
ser el de la publicación original. Si dos fuentes cuentan el mismo hecho, con
una basta, y si el hecho ya salió en el snapshot anterior tampoco hace falta
repetirlo.

Después hay que **estructurar** lo que encontraste. Cada noticia se arma con
los campos del contrato (`docs/contrato-de-datos.md`): `id`, `title`, `url`,
`source`, `published_at`, `summary`, `tags` y, si aplica, `category`. El `id`
se escribe como `<fecha>-<fuente>-<titulo-corto>` en minúsculas y con guiones,
las fechas van en UTC con el formato `YYYY-MM-DDTHH:MM:SSZ` y el resumen se
escribe en español, en una o dos frases. Ordena las entradas de la más
reciente a la más antigua.

Por último hay que **guardar**. Envuelve las entradas en el objeto del
snapshot —`version`, `snapshot_date`, `generated_at`, `item_count` e `items`—
y escribe `data/snapshots/<fecha>.json` con sangría de dos espacios. Antes de
terminar, pasa el validador y corrige lo que reporte:

```bash
python3 .codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py \
  data/snapshots/<fecha>.json
```

Cuando el archivo esté bien, haz un commit con el mensaje
`data: snapshot <fecha>`.

## Archivos de la skill

| Archivo | Para qué sirve |
|---|---|
| `references/fuentes.md` | Catálogo de fuentes que revisa el radar. |
| `scripts/validar_snapshot.py` | Revisa que el snapshot tenga los campos y que las cuentas cuadren. |
