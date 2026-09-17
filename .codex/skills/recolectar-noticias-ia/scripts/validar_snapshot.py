#!/usr/bin/env python3
"""Revisa que un snapshot del radar tenga la forma que pide el contrato.

Uso:
    python3 validar_snapshot.py data/snapshots/2026-09-14.json

Comprueba que el archivo sea JSON valido, que esten los campos del snapshot y
los de cada noticia, y que item_count coincida con el numero de entradas. Sale
con 0 si todo cumple y con 1 listando los errores, uno por linea. Solo usa la
biblioteca estandar.
"""

import json
import sys
from pathlib import Path

CAMPOS_SNAPSHOT = ["version", "snapshot_date", "generated_at", "item_count", "items"]
CAMPOS_NOTICIA = ["id", "title", "url", "source", "published_at"]


def validar(ruta: Path) -> list[str]:
    errores: list[str] = []

    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"el archivo no es JSON valido: {error}"]

    if not isinstance(datos, dict):
        return ["el snapshot tiene que ser un objeto JSON"]

    for campo in CAMPOS_SNAPSHOT:
        if campo not in datos:
            errores.append(f"falta el campo '{campo}' del snapshot")

    items = datos.get("items")
    if not isinstance(items, list):
        errores.append("'items' tiene que ser una lista")
        return errores
    if not items:
        errores.append("'items' no puede estar vacio: un snapshot lleva al menos una entrada")

    for posicion, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errores.append(f"la entrada {posicion} no es un objeto")
            continue
        for campo in CAMPOS_NOTICIA:
            if campo not in item:
                errores.append(f"la entrada {posicion} no tiene '{campo}'")

    contador = datos.get("item_count")
    if isinstance(contador, int) and contador != len(items):
        errores.append(f"item_count dice {contador} y hay {len(items)} entradas")

    return errores


def main() -> int:
    if len(sys.argv) != 2:
        print("uso: validar_snapshot.py <archivo.json>")
        return 1

    ruta = Path(sys.argv[1])
    if not ruta.is_file():
        print(f"no existe el archivo {ruta}")
        return 1

    errores = validar(ruta)
    for error in errores:
        print(error)

    if errores:
        return 1

    print(f"{ruta}: {len(json.loads(ruta.read_text(encoding='utf-8'))['items'])} entradas, sin errores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
