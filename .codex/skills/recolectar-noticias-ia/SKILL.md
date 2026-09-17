---
name: recolectar-noticias-ia
description: Recolecta las noticias y lanzamientos de IA del día repartiendo las fuentes entre subagentes en paralelo y armando el snapshot con tools/recolector.py. Úsala cuando haya que generar el snapshot de un día, rehacerlo o agregarle una fuente nueva.
---

# Recolectar noticias de IA

## Propósito

Convertir lo publicado hoy por las fuentes del catálogo en un snapshot diario
que cumpla el contrato de datos 2.0. La skill cubre el flujo entero —buscar,
priorizar, estructurar, deduplicar y guardar—, pero ya no lo hace todo a mano:
la parte mecánica la ejecuta `tools/recolector.py` de una sola llamada, y la
búsqueda se reparte entre cuatro subagentes que corren en paralelo.

## Qué decide la skill y qué ejecuta el tool

| Le toca al modelo | Lo ejecuta el tool |
|---|---|
| Qué candidata es noticia y cuál es relleno | Leer el catálogo y cada fuente |
| Elegir el enlace primario cuando la fuente reseña a otra | Normalizar los campos al contrato |
| Resolver que dos fuentes cuentan el mismo hecho con URLs distintas | Calcular `id` y `dedup_key` |
| Redactar el `summary` en español | Deduplicar contra el día anterior |
| Revisar el reporte y decidir si se commitea | Ordenar, contar y escribir el archivo |

La línea es sencilla: lo que tiene una respuesta única y comprobable lo hace el
programa; lo que exige criterio se queda en el modelo. Un resumen redactado por
plantilla sería peor que ninguno, y una `dedup_key` calculada «a ojo» sería
sencillamente falsa.

## Cuándo usarla

- Se pide el snapshot del día o el de una fecha concreta.
- Hay que rehacer un snapshot porque se agregó o corrigió una fuente.
- Se quiere revisar qué publicó una fuente dentro del formato del radar.

No la uses para analizar snapshots ya escritos: eso no toca el catálogo ni
produce archivos nuevos.

## Entradas

| Entrada | Origen | Por defecto |
|---|---|---|
| Fecha del snapshot | la pide quien invoca la skill | el día de hoy en UTC |
| Catálogo de fuentes | `references/fuentes.md` | — |
| Subagentes | `.codex/agents/` | los cuatro |
| Snapshot anterior | el archivo más reciente de `data/snapshots/` | ninguno, si es el primer día |

## Permisos

Ningún permiso permanente. Tres aprobaciones por sesión, cada una pegada a la
fase que la usa:

| Fase | Permiso | Alcance |
|---|---|---|
| Buscar | Acceso a la red | Solo los dominios del catálogo, y cada subagente solo los de sus fuentes. |
| Buscar | Escritura en disco | Un directorio temporal fuera del repositorio, donde los subagentes dejan su JSON. |
| Guardar | Escritura en disco | Únicamente `data/snapshots/`, más el commit local. |

*Priorizar*, *Estructurar* y *Deduplicar* no piden nada: el tool solo lee el
catálogo, el directorio temporal y el snapshot anterior. `git push`, instalar
dependencias o escribir fuera de `data/snapshots/` quedan fuera de esta skill.
La política completa está en la sección «Permisos: sesión vs. permanentes» de
`AGENTS.md`.

## Procedimiento

### Fase 1 — Buscar

Lanza los cuatro subagentes **a la vez**, cada uno con su propio contexto:
`blogs-oficiales`, `changelogs-y-releases`, `investigacion` y `regulacion`.
Cada uno recibe la fecha y sus filas del catálogo, y devuelve el JSON de sus
fuentes. Guarda la respuesta de cada uno en el directorio de trabajo del día,
un archivo por `source`:

```bash
DIA=2026-09-16
TRABAJO="${TMPDIR:-/tmp}/radar-$DIA"
mkdir -p "$TRABAJO"          # aquí escribe cada subagente: <source>.json
```

Detalle del reparto, del contexto de cada uno y de qué hacer cuando uno falla:
`docs/subagentes.md`.

**Fallback:** un subagente que no responde deja fuera sus fuentes y se anota;
los demás siguen. Si ninguno devolvió nada, la pasada falló y no se escribe
archivo.

### Fase 2 — Priorizar

Lo único de la recolección que sigue siendo juicio, y por eso sigue aquí:

1. Descarta lo que el contrato no considera noticia: opiniones, hilos de redes
   sociales y notas que reescriben a otra fuente.
2. Si dos subagentes trajeron el mismo hecho con URLs distintas, conserva la
   publicación primaria. La clave de deduplicación **no** atrapa este caso:
   mide identidad de publicación, no parecido temático.
3. Borra del directorio de trabajo los ítems que no entran.
4. Redacta el `summary` de cada una en español y déjalos en un JSON indexado
   por URL, que es lo que el paso siguiente le pasa al tool.

### Fases 3 y 4 — Estructurar y deduplicar

Las dos las ejecuta el recolector en una sola llamada:

```bash
python3 tools/recolector.py \
  --fecha "$DIA" \
  --fixtures "$TRABAJO" \
  --anterior data/snapshots/2026-09-15.json \
  --salida "data/snapshots/$DIA.json" \
  --resumenes "$TRABAJO/resumenes.json"
```

Normaliza cada publicación al contrato, calcula `id` y `dedup_key`, compara
con el día anterior, ordena de lo más reciente a lo más antiguo, cuenta y
escribe. Con `--dry-run` informa sin escribir; con `--fuente` se limita a una
fuente; con `--red` lee los feeds del catálogo en vez del directorio de
trabajo.

Lee el reporte que imprime: cuántas entradas quedaron, cuántas en `pendiente`,
cuántas se fueron a `dedup.discarded` y qué fuentes dieron aviso. Una entrada
en `pendiente` o un aviso de fuente caída son información, no un fallo; una
entrada que el tool no pudo escribir por falta de cita sí exige volver a la
fuente.

### Fase 5 — Guardar

1. Valida y corrige lo que reporte antes de seguir:

   ```bash
   python3 .codex/skills/recolectar-noticias-ia/scripts/validar_snapshot.py \
     "data/snapshots/$DIA.json" --previous data/snapshots/2026-09-15.json
   ```

   Sin `--previous` solo el primer día de todos.
2. Revisa el archivo contra los criterios de «hecho» de `AGENTS.md`.
3. Haz un commit con el mensaje `data: snapshot $DIA`.
4. Borra el directorio de trabajo.

## Salidas

- `data/snapshots/<snapshot_date>.json`, válido contra el contrato 2.0.
- Un commit con ese archivo.
- Un resumen en la conversación: cuántas entradas quedaron, de qué fuentes,
  cuántas en `pendiente` y por qué, cuántas se descartaron por repetidas y qué
  fuentes o subagentes no respondieron.

## Archivos de la skill

| Archivo | Para qué sirve |
|---|---|
| `references/fuentes.md` | Catálogo de fuentes, su identificador canónico y su feed. |
| `scripts/validar_snapshot.py` | Valida un snapshot contra el contrato y, con `--previous`, la deduplicación entre días. Sale con 0 si está bien. |
| `tools/recolector.py` | Arma el snapshot: normaliza, calcula claves, deduplica y escribe. |
| `.codex/agents/` | Los cuatro subagentes que se reparten las fuentes. |
