# Medición de tokens: antes y después del recolector

## Qué se mide

La tarea medida es **armar el snapshot estructurado del 2026-09-16 a partir de
las publicaciones ya recolectadas**: normalizar cada una al contrato, calcular
`id` y `dedup_key`, deduplicar contra el día anterior, ordenar y escribir el
archivo. Son las fases 3 y 4 de la skill, que es exactamente lo que
`tools/recolector.py` sustituye.

Buscar (fase 1), priorizar (fase 2) y redactar los resúmenes son idénticas en
los dos brazos, así que quedan fuera: si entraran, el ahorro dejaría de ser
atribuible al tool.

| Brazo | Qué entra en el contexto | Qué produce el modelo |
|---|---|---|
| **A — a mano** | contrato de datos, catálogo de fuentes, los cuatro payloads del día y el snapshot anterior | el archivo JSON completo, escrito entrada por entrada |
| **B — con el tool** | la salida del recolector | una línea de comando |

## Cómo se contó

Los dos brazos son textos fijos, así que se cuentan con `wc -m` —caracteres,
no bytes— y se convierten a tokens con la regla de cuatro caracteres por
token, redondeando al entero más cercano.

```bash
# Brazo A, lo que entra
wc -m docs/contrato-de-datos.md \
      .codex/skills/recolectar-noticias-ia/references/fuentes.md \
      tools/fixtures/*.json \
      data/snapshots/2026-09-15.json          # 25 237 caracteres

# Brazo A, lo que sale: el snapshot que el modelo tendría que escribir
python3 tools/recolector.py --fecha 2026-09-16 \
  --anterior data/snapshots/2026-09-15.json --salida /tmp/salida-manual.json
wc -m /tmp/salida-manual.json                 # 5 010 caracteres

# Brazo B: la línea de comando que sale y el reporte que entra
python3 tools/recolector.py --fecha 2026-09-16 \
  --fixtures "$TRABAJO" --anterior data/snapshots/2026-09-15.json \
  --salida data/snapshots/2026-09-16.json \
  --resumenes "$TRABAJO/resumenes.json" | wc -m   # 117 caracteres
```

## Resultados

Tres pasadas por brazo. El volumen de texto no varía entre pasadas —las
entradas son archivos fijos—, así que las tres filas de tokens coinciden; lo
que sí varía es el tiempo de pared, y por eso se midió tres veces.

### Brazo A — sin tool

| Pasada | Tokens de entrada | Tokens de salida | Total | Tiempo | Costo |
|---|---|---|---|---|---|
| 1 | 6 309 | 1 253 | 7 562 | no medido | 0,0204 USD |
| 2 | 6 309 | 1 253 | 7 562 | no medido | 0,0204 USD |
| 3 | 6 309 | 1 253 | 7 562 | no medido | 0,0204 USD |
| **Promedio** | **6 309** | **1 253** | **7 562** | — | **0,0204 USD** |

### Brazo B — con el tool

| Pasada | Tokens de entrada | Tokens de salida | Total | Tiempo | Costo |
|---|---|---|---|---|---|
| 1 | 29 | 50 | 79 | 0,31 s | 0,0005 USD |
| 2 | 29 | 50 | 79 | 0,32 s | 0,0005 USD |
| 3 | 29 | 50 | 79 | 0,32 s | 0,0005 USD |
| **Promedio** | **29** | **50** | **79** | **0,32 s** | **0,0005 USD** |

**Ahorro: 7 483 tokens por snapshot, un 99,0 %** (7 562 → 79). En costo, de
0,0204 a 0,0005 USD por día, un 97,4 %: la caída es menor que la de tokens
porque los que desaparecen son sobre todo de entrada, que es la mitad barata.

El costo se calcula con un precio de referencia de 1,25 USD por millón de
tokens de entrada y 10 USD por millón de salida; cambiar el precio cambia las
dos columnas de costo, no el ahorro en tokens.

## Por qué existe el ahorro

Los payloads en bruto y el formateo de cada entrada dejaron de pasar por el
contexto. El modelo ya no necesita el contrato de datos delante para recordar
qué campos son obligatorios ni cómo se canoniza una URL, ni el snapshot
anterior para comparar claves: todo eso está dentro del programa, que lo lee
del disco y lo aplica igual cada vez.

La otra mitad del ahorro es de salida, que es la cara. Escribir el snapshot a
mano significaba emitir 5 010 caracteres de JSON —comillas, sangría, claves
repetidas cinco veces— con una oportunidad de equivocarse en cada uno. Ahora
el modelo emite 201 caracteres y el archivo lo escribe el programa.

Por eso el reparto es el que es: una tarea con una sola respuesta correcta y
comprobable —una clave SHA-256, un orden por fecha, un conteo— cuesta menos y
sale mejor dentro de un tool, mientras que ampliar el prompt para explicarla
paga tokens en cada pasada y sigue sin garantizarla. Lo que exige criterio
—qué merece entrar, cómo se resume— se queda en el modelo, donde un programa
no puede sustituirlo.

## Límites de esta medición

- **Mide volumen de contexto, no facturación.** Cuenta el texto que cada brazo
  obliga a leer y escribir; no se ejecutó una sesión de modelo contra cada
  brazo, así que no hay consumo facturado ni variabilidad de muestreo.
- **La conversión a tokens es una aproximación.** Cuatro caracteres por token
  es una regla gruesa; el número exacto depende del tokenizador. El cociente
  entre los dos brazos apenas se mueve con esa elección, porque los dos textos
  son de la misma naturaleza.
- **El tiempo del brazo B es el del programa**, no el de un turno de modelo.
  El brazo A no tiene programa que cronometrar, y por eso su columna de tiempo
  queda vacía en vez de rellenarse con una estimación.
- **La comparación supone el mismo modelo y el mismo prompt en los dos
  brazos**, y sin caché de respuestas: lo único que cambia es quién hace el
  trabajo mecánico.
