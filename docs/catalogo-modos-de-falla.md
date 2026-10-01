# Catálogo de modos de falla — `tools/recolector.py`

Etapa 1 del proyecto. Módulo evaluado: **`tools/recolector.py`** en el commit
`4f5cc2f`, el que arma cada día `data/snapshots/YYYY-MM-DD.json`. Lo elegí
porque es el único punto del radar que escribe datos: si se equivoca, el error
queda en el historial de `data/snapshots/`, que es la bitácora del proyecto.

La especificación contra la que se compara es la del propio repositorio:

- `docs/contrato-de-datos.md` (contrato 2.0): campos, límites, fechas, reglas
  de `id`, `dedup_key`, `status` y del snapshot.
- `AGENTS.md`, sección *Permisos*: escritura limitada a `data/snapshots/` y
  «nunca reescribir snapshots publicados».

Cada comportamiento observado sale de ejecutar el módulo real con Python 3
(biblioteca estándar), sobre una copia del repositorio y con fixtures armados
para cada caso. Los comandos están al final.

## Resumen

| ID | Familia | Entrada disparadora | Observado | Contrato |
|---|---|---|---|---|
| MF-FR-01 | Frontera | `section` de 250 caracteres | `status_note` de 372 caracteres | máx. 300 |
| MF-FR-02 | Frontera | `title` de 205 caracteres | cortado a 200 a mitad de palabra | pendiente de decisión |
| MF-FR-03 | Frontera | resumen de 400 caracteres | se escribe entero | máx. 280 |
| MF-EQ-01 | Equivalencia | `published_at` = `2026-09-16` | entrada no escrita | completar con `T00:00:00Z` |
| MF-EQ-02 | Equivalencia | ISO con zona, con milisegundos o RFC 822 | entrada no escrita | convertir a UTC fijo |
| MF-EQ-03 | Equivalencia | dos títulos sin letras latinas | `…-sin-titulo` y `…-sin-titulo-2` | pendiente de decisión |
| MF-NV-01 | Null / vacío | `quote: null` | cita literal `"None"` en `procesado` | sin cita = no lista |
| MF-NV-02 | Null / vacío | `title: null` o `url: null` | título o URL `"None"` | campo faltante |
| MF-NV-03 | Null / vacío | resumen `"   "` | `"summary": ""` | omitir el campo |
| MF-NV-04 | Null / vacío | `quote: ""` | entrada no escrita | pendiente de decisión |
| MF-NV-05 | Null / vacío | pasada sin `--anterior` | `previous_snapshot: null`, sin deduplicar | `null` solo en el primero |
| MF-CC-01 | Carrera | dos pasadas a la vez, mismo archivo | gana la última; 3000 entradas perdidas sin aviso | un snapshot por día, completo |
| MF-CC-02 | Carrera | `--anterior` a medio escribir | traceback `JSONDecodeError` | error controlado |
| MF-BA-01 | Bypass de autorización | `--salida docs/contrato-de-datos.md` | sobrescribe el contrato | escribir solo en `data/snapshots/` |
| MF-BA-02 | Bypass de autorización | otra pasada de un día ya publicado | reescribe el snapshot publicado | nunca reescribir |

## Fichas

### Frontera

**MF-FR-01 — La nota de estado no respeta su tope**
- **Categoría:** frontera, límite de longitud de `status_note`.
- **Entrada disparadora:** una publicación con `section` de 250 caracteres que
  no está en `SECCIONES`.
- **Comportamiento observado:** la entrada queda `pendiente` con una
  `status_note` de **372** caracteres, porque `normalizar` copia la etiqueta
  completa dentro de la nota.
- **Contrato esperado:** `status_note` tiene un máximo de 300 caracteres. La
  etiqueta citada se recorta para que la nota quepa.

**MF-FR-02 — El título se edita para que quepa**
- **Categoría:** frontera, límite de `title`.
- **Entrada disparadora:** `title` de 205 caracteres.
- **Comportamiento observado:** se corta en el carácter 200, a mitad de palabra
  (termina en `"… Realtime Re"`). La cita, en cambio, sí se corta en el último
  espacio.
- **Contrato esperado: pendiente de decisión.** El contrato pide dos cosas que
  aquí chocan: «sin editar» y «máximo 200 caracteres». Las opciones son cortar
  en el último espacio o dejar la entrada `pendiente` con el título completo
  para que una persona lo resuelva.

**MF-FR-03 — Un resumen largo pasa sin control**
- **Categoría:** frontera, límite de `summary`.
- **Entrada disparadora:** `--resumenes` con un texto de 400 caracteres.
- **Comportamiento observado:** el snapshot se escribe con un `summary` de 400
  caracteres.
- **Contrato esperado:** `summary` tiene un máximo de 280 caracteres. Un
  resumen que no cabe no se escribe, y la entrada no queda `procesado`.

### Equivalencia

**MF-EQ-01 — Una fecha sin hora se pierde**
- **Categoría:** equivalencia, clase «solo fecha» del campo `published_at`.
- **Entrada disparadora:** `published_at` = `"2026-09-16"`.
- **Comportamiento observado:** la entrada no se escribe («fecha de publicación
  fuera de formato»). Si era la única del día, la pasada termina con código 1 y
  sin archivo.
- **Contrato esperado:** regla 3: «Si la fuente publica solo la fecha, se usa
  `T00:00:00Z`». Debería escribirse con `2026-09-16T00:00:00Z`.

**MF-EQ-02 — Instantes válidos en otra grafía se rechazan**
- **Categoría:** equivalencia, todas las representaciones del mismo instante.
- **Entrada disparadora:** `2026-09-16T15:20:00+00:00`,
  `2026-09-16T15:20:00.000Z` y `Wed, 16 Sep 2026 15:20:00 GMT`.
- **Comportamiento observado:** las tres se rechazan. Es más grave de lo que
  parece: con `--red`, `leer_desde_red` toma la fecha de `pubDate` en los feeds
  RSS, y en RSS 2.0 `pubDate` siempre viene en RFC 822. Ninguna fuente RSS puede
  aportar entradas.
- **Contrato esperado:** el formato fijo es la **salida**, no un filtro de
  entrada. Un instante válido se convierte a UTC con `YYYY-MM-DDTHH:MM:SSZ`.

**MF-EQ-03 — Títulos sin letras latinas comparten `id`**
- **Categoría:** equivalencia, títulos sin caracteres ASCII.
- **Entrada disparadora:** dos publicaciones del mismo día y fuente, tituladas
  `新しい推論モデル` y `構造化出力の更新`.
- **Comportamiento observado:** `convertir_en_slug` deja ambos en `sin-titulo`;
  `armar_snapshot` resuelve el choque con un sufijo y produce
  `2026-09-16-openai-blog-sin-titulo` y `…-sin-titulo-2`. El sufijo depende del
  orden de las entradas de ese día, así que el mismo hecho cambia de `id` si
  aparece otra publicación parecida.
- **Contrato esperado: pendiente de decisión.** La regla 1 pide que el mismo
  hecho produzca siempre el mismo `id`. Una opción es usar el digesto de la
  `dedup_key` como título corto cuando el slug queda vacío.

### Null / vacío

**MF-NV-01 — Una cita nula se convierte en la cita `"None"`**
- **Categoría:** null, campo `quote`.
- **Entrada disparadora:** publicación con `"quote": null`.
- **Comportamiento observado:** la entrada se escribe como `procesado` con
  `"evidence": {"url": "…", "quote": "None"}`. `str(None)` pasa la comprobación
  de «hay cita». El radar presenta como prueba textual una palabra que la
  fuente nunca escribió.
- **Contrato esperado:** la cita se copia, no se inventa. `null` cuenta como
  ausencia de cita.

**MF-NV-02 — Título o URL nulos se escriben como `"None"`**
- **Categoría:** null, campos obligatorios `title` y `url`.
- **Entrada disparadora:** `"title": null` en un caso y `"url": null` en otro,
  con el resto válido.
- **Comportamiento observado:** se escribe una noticia titulada `"None"` y otra
  con `"url": "None"` y `dedup_key` `openai-blog:dc937b598926`, calculada sobre
  la palabra `None`.
- **Contrato esperado:** son campos obligatorios. La entrada se trata como
  «faltan título, enlace o fecha», igual que cuando el campo no existe.

**MF-NV-03 — Un resumen en blanco deja `summary` vacío**
- **Categoría:** vacío, campo opcional `summary`.
- **Entrada disparadora:** `--resumenes` con `"   "` para la URL de la entrada.
- **Comportamiento observado:** se escribe `"summary": ""`. El texto pasa el
  `if resumen` y queda vacío después de normalizar espacios.
- **Contrato esperado:** regla 4 y `AGENTS.md`: si no hay resumen, el campo se
  omite; nunca una cadena vacía.

**MF-NV-04 — Una entrada sin cita desaparece en vez de quedar pendiente**
- **Categoría:** vacío, campo `quote`.
- **Entrada disparadora:** `"quote": ""`.
- **Comportamiento observado:** la entrada no se escribe; solo queda un aviso
  en la salida estándar.
- **Contrato esperado: pendiente de decisión.** La sección de `evidence` dice
  que una entrada sin frase citable «queda en `pendiente` con su motivo», pero
  el esquema exige `evidence.quote`. El módulo eligió descartar, y el contrato
  no dice cuál de las dos reglas manda.

**MF-NV-05 — Sin `--anterior` no hay deduplicación**
- **Categoría:** null, argumento opcional `--anterior`.
- **Entrada disparadora:** una pasada del 2026-09-16 sin `--anterior`, con
  `2026-09-15.json` en `data/snapshots/`.
- **Comportamiento observado:** el snapshot sale con
  `"dedup": {"previous_snapshot": null, "discarded": []}` y no compara con
  nada: lo repetido del día anterior vuelve a entrar.
- **Contrato esperado:** regla 5: `previous_snapshot` nombra el snapshot
  inmediatamente anterior que existe, y `null` solo vale en el primero. El
  módulo debería encontrarlo en `data/snapshots/` o negarse a seguir.

### Condiciones de carrera

**MF-CC-01 — Dos pasadas a la vez: la última borra a la otra**
- **Categoría:** condición de carrera, escritura del snapshot.
- **Entrada disparadora:** dos procesos simultáneos con la misma `--salida` y
  fixtures distintos de 3000 entradas cada uno.
- **Comportamiento observado:** los dos terminan con código 0. El archivo final
  solo tiene las entradas de una pasada; las 3000 de la otra se pierden sin
  aviso. `destino.write_text` trunca y escribe, sin bloqueo ni archivo temporal.
- **Contrato esperado:** «hay como máximo uno por día» y debe estar completo.
  La escritura debe ser atómica (archivo temporal más `os.replace`) y una
  segunda pasada del mismo día debe fallar mientras la primera no termine.

**MF-CC-02 — Leer el snapshot anterior mientras se escribe**
- **Categoría:** condición de carrera, lectura de `--anterior`.
- **Entrada disparadora:** `--anterior` apuntando a un archivo a medio escribir
  (`2026-09-15.json` cortado a 400 bytes, que es lo que ve un lector durante
  MF-CC-01).
- **Comportamiento observado:** la pasada muere con un traceback
  `json.decoder.JSONDecodeError: Expecting value: line 12 column 22 (char 400)`.
  `cargar_anterior` no captura nada.
- **Contrato esperado:** `AGENTS.md`: «cuando una acción caiga fuera de lo
  permitido, el agente se detiene y lo dice, con el motivo». Un mensaje claro
  que nombre el archivo, no un traceback.

### Bypass de autorización

**MF-BA-01 — `--salida` escribe fuera de `data/snapshots/`**
- **Categoría:** bypass de autorización, alcance de escritura.
- **Entrada disparadora:**
  `python3 tools/recolector.py --fecha 2026-09-16 --fuente openai-blog --salida docs/contrato-de-datos.md`.
- **Comportamiento observado:** escribe un snapshot encima del contrato de
  datos (`git status`: `M docs/contrato-de-datos.md`). Lo mismo con cualquier
  ruta, incluido `.codex/`.
- **Contrato esperado:** `AGENTS.md` aprueba por sesión la «escritura en disco,
  limitada a `data/snapshots/`», y ese permiso se concede al ejecutar el
  recolector. Como el módulo no comprueba el destino, quien tiene permiso para
  correrlo puede escribir donde quiera. Debe rechazar cualquier destino fuera de
  `data/snapshots/`.

**MF-BA-02 — Una pasada repetida reescribe un snapshot publicado**
- **Categoría:** bypass de autorización, acción prohibida.
- **Entrada disparadora:** volver a correr el día 2026-09-16, que ya está en
  el repositorio, solo con `--fuente openai-blog`.
- **Comportamiento observado:** sobrescribe `data/snapshots/2026-09-16.json`
  sin preguntar (`git diff --stat`: 14 inserciones, 63 borrados). Las entradas
  de las otras fuentes de ese día desaparecen.
- **Contrato esperado:** regla 4 del snapshot y `AGENTS.md`: «Borrar o
  reescribir snapshots publicados» nunca es un permiso permanente; se corrige
  con un commit nuevo. El módulo debe negarse si el archivo ya existe, salvo en
  `--dry-run`.

## Cómo falló el prompt ingenuo

Prompt usado, sin contrato ni `AGENTS.md` en el contexto:

> Genera pruebas unitarias completas para `tools/recolector.py`.

Devolvió seis pruebas. Corridas contra el módulo real: **2 fallan y 4 pasan**,
y ninguna de las que pasan detecta un modo de falla del catálogo.

| Prueba generada | Resultado | Qué salió mal |
|---|---|---|
| `test_normalizar_sin_titulo_lanza_valueerror` | FAIL: `ValueError not raised` | **Contrato inventado.** `normalizar` nunca lanza: devuelve `(None, motivo)` para que una fuente mala no detenga la pasada. |
| `test_fecha_con_zona_horaria_se_normaliza_a_utc` | ERROR: `TypeError: 'NoneType' object is not subscriptable` | **Contrato inventado.** Supone que el módulo convierte `-05:00` a UTC; en realidad rechaza la entrada (MF-EQ-02). |
| `test_entrada_sin_cita_se_descarta` | pasa | **Bug consolidado.** Toma como correcto lo que el contrato contradice (MF-NV-04). |
| `test_titulo_largo_se_trunca_a_200` | pasa | **Bug no detectado.** Solo mide la longitud; no ve el corte a mitad de palabra ni el «sin editar» (MF-FR-02). |
| `test_clave_dedup_ignora_utm` | pasa | Correcta, y coincide con el contrato. |
| `test_ids_distintos_para_titulos_distintos` | pasa | **Bug no detectado.** Usa títulos en inglés; con títulos sin letras latinas los `id` chocan (MF-EQ-03). |

Las dos fallas concretas que pide la etapa:

1. **Inventó contratos.** Escribió pruebas para un `ValueError` y una
   conversión a UTC que el módulo no implementa ni el contrato promete en esa
   forma. Las pruebas rojas no señalaban un bug: señalaban la imaginación del
   modelo.
2. **Dejó pasar los bugs reales.** Ninguna prueba usa `null`, textos en blanco,
   límites exactos, títulos no latinos, dos pasadas a la vez ni rutas de
   `--salida`. Por eso no aparecen MF-NV-01 (cita `"None"`), MF-CC-01 ni
   MF-BA-01, y la prueba de la cita convierte MF-NV-04 en comportamiento
   «esperado».

### Comparación con la especificación

| Tema | Lo que asumió el prompt ingenuo | Lo que dice la especificación | Lo que hace el módulo |
|---|---|---|---|
| Datos inválidos | Lanza excepción | El agente se detiene y lo dice | Devuelve `(None, motivo)` y avisa |
| Fechas | Convierte zonas a UTC | Salida en UTC fijo; solo fecha → `T00:00:00Z` | Rechaza todo lo que no sea el formato exacto |
| Entrada sin cita | Se descarta | Queda `pendiente` (choca con el esquema) | Se descarta |
| Escritura | No la prueba | Solo `data/snapshots/`, nunca reescribir | Escribe donde le digan y reescribe |
| Valores nulos | No los prueba | Campo obligatorio = presente y no vacío | Los convierte en el texto `"None"` |

## Cómo reproducir

Sobre una copia del repositorio, con un directorio de fixtures por caso que
contiene `openai-blog.json` (`{"fetched_at": "…", "items": [ … ]}`):

```bash
python3 tools/recolector.py --fecha 2026-09-16 --fuente openai-blog --fixtures <dir> --salida <dir>/out.json
python3 tools/recolector.py --fecha 2026-09-16 --fuente openai-blog --fixtures <dir> --salida <dir>/out.json --resumenes - <<< '{"<url>": "   "}'
python3 tools/recolector.py --fecha 2026-09-16 --fuente openai-blog --anterior <archivo cortado>.json --dry-run
python3 tools/recolector.py --fecha 2026-09-16 --fuente openai-blog --salida docs/contrato-de-datos.md
python3 tools/recolector.py --fecha 2026-09-16 --fuente openai-blog
```

MF-CC-01 se reproduce lanzando el primer comando dos veces en paralelo, con
fixtures distintos y la misma `--salida`.
