# AGENTS.md — manual operativo de AIRadar

Este archivo es el manual con el que Codex opera el repositorio. Describe qué
es este proyecto, dónde vive cada cosa, cómo se trabaja un día normal y cuándo
se considera terminado un snapshot. Si algo de aquí contradice al contrato de
datos, manda el contrato (`docs/contrato-de-datos.md`).

## Propósito

AIRadar mantiene un radar diario de noticias y lanzamientos de inteligencia
artificial. Cada día se revisan las fuentes del catálogo y se deja un archivo
JSON con lo publicado, siempre con la misma forma. El repositorio no tiene
aplicación ni servidor: el producto son los snapshots y las reglas que los
hacen comparables entre sí.

El valor está en la constancia y en el formato. Un snapshot bonito pero con
campos inventados vale menos que uno corto que respeta el contrato.

## Estructura del repositorio

```
.
├── AGENTS.md                  # este manual
├── README.md                  # mapa del repositorio
├── .codex/
│   └── skills/
│       └── recolectar-noticias-ia/   # skill de recolección: SKILL.md, scripts y references
├── data/
│   └── snapshots/             # un archivo por día: YYYY-MM-DD.json
├── docs/
│   └── contrato-de-datos.md   # definición de noticia y de snapshot
└── schemas/
    ├── noticia.schema.json    # JSON Schema de una noticia
    └── snapshot.schema.json   # JSON Schema del snapshot diario
```

## Skills disponibles

| Skill | Cuándo se usa |
|---|---|
| `recolectar-noticias-ia` | Generar o rehacer el snapshot de un día. Ver `.codex/skills/recolectar-noticias-ia/SKILL.md`. |

Una tarea que se repite dos veces con los mismos pasos es candidata a skill.
Antes de escribir una nueva, comprueba que no sea una variante de la que ya
existe: dos skills parecidas se desincronizan enseguida.

## Convenciones de nombres

- **Snapshots**: `data/snapshots/YYYY-MM-DD.json`, con la fecha en UTC. Un
  archivo por día, sin sufijos ni copias tipo `-v2`.
- **Identificadores de noticia**: `YYYY-MM-DD-fuente-titulo-corto`, en
  minúsculas, sin acentos y con guiones.
- **Documentos**: en `docs/`, nombre en español y con guiones
  (`contrato-de-datos.md`).
- **Skills**: una carpeta por skill en `.codex/skills/`, con el nombre en
  infinitivo (`recolectar-noticias-ia`), su `SKILL.md`, y `scripts/` y
  `references/` si los necesita.
- **Prosa en español, claves en inglés.** La documentación se escribe en
  español; los campos de los datos y los nombres de variables van en inglés
  (`published_at`, `source`), que es como están en las fuentes.

## Convenciones de commits

Formato `tipo: descripción en español`, en imperativo y sin punto final.

| Tipo | Para qué |
|---|---|
| `data` | Un snapshot nuevo o corregido. Mensaje: `data: snapshot 2026-09-14`. |
| `docs` | Cambios en `docs/`, el README o este manual. |
| `schema` | Cambios en `schemas/`. |
| `skill` | Cambios dentro de `.codex/skills/`. |
| `feat` | Capacidades nuevas del proyecto. |
| `fix` | Corrección de algo que estaba mal. |

Un commit por asunto. El snapshot del día va solo en su commit, sin arrastrar
cambios de documentación: así el historial de `data/snapshots/` se lee como la
bitácora del radar.

## Flujo de trabajo diario

1. Revisa en qué quedó el radar: cuál es el último snapshot y si el árbol de
   trabajo está limpio.
2. Invoca la skill `recolectar-noticias-ia` con la fecha de hoy.
3. Revisa el archivo que produjo contra los criterios de la sección siguiente.
4. Haz el commit del snapshot.
5. Si durante la pasada apareció una fuente que vale la pena seguir, agrégala
   al catálogo en un commit `skill:` aparte, nunca dentro del commit del
   snapshot.

Cambiar el contrato de datos no es parte del día a día. Si hace falta, se
cambia primero `docs/contrato-de-datos.md`, luego los esquemas y por último la
skill, en ese orden y en commits separados, subiendo la versión del contrato.
Los snapshots viejos se quedan con la versión con la que se escribieron.

## Comandos útiles

```bash
ls data/snapshots | tail -5                      # últimos días recolectados
python3 -m json.tool data/snapshots/2026-09-14.json > /dev/null   # ¿parsea el JSON?
git log --oneline -- data/snapshots              # bitácora del radar
git status --short                               # qué quedó sin commitear
```

## Criterios de "hecho" para un snapshot

Un snapshot está terminado cuando se cumple todo esto:

1. El archivo está en `data/snapshots/` y su nombre coincide con
   `snapshot_date`.
2. Todas las entradas traen los campos obligatorios del contrato.
3. Los `id` no se repiten dentro del archivo.
4. `published_at` y `collected_at` están en UTC con el formato
   `YYYY-MM-DDTHH:MM:SSZ`.
5. `category` y `source_type` salen de las listas cerradas del contrato, y
   `source` está escrito igual que en el catálogo de fuentes.
6. `items` va de la publicación más reciente a la más antigua y `item_count`
   coincide con el número de entradas.
7. Hay un commit `data:` que contiene ese archivo y nada más.

## Límites

- No se inventan noticias ni se completan campos a ojo: si un dato no está en
  la fuente, el campo opcional se omite y el obligatorio se busca hasta
  encontrarlo.
- No se editan snapshots ya publicados. Una corrección es un commit nuevo que
  la explica.
- No se agregan dependencias externas. Lo que corra en este repositorio debe
  funcionar con Python y su biblioteca estándar.
