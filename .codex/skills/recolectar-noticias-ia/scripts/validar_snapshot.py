#!/usr/bin/env python3
"""Valida un snapshot diario del radar contra el contrato de datos 1.0.

Uso:
    python3 validar_snapshot.py data/snapshots/2026-09-14.json

Sale con código 0 si el archivo cumple el contrato y con 1 si encuentra
errores, que se imprimen uno por línea. Solo usa la biblioteca estándar para
que se pueda correr sin instalar nada.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

VERSION_CONTRATO = "1.0"

CAMPOS_SNAPSHOT = {
    "version": str,
    "snapshot_date": str,
    "generated_at": str,
    "item_count": int,
    "items": list,
}

CAMPOS_NOTICIA = {
    "id": str,
    "title": str,
    "url": str,
    "source": str,
    "source_type": str,
    "category": str,
    "published_at": str,
    "collected_at": str,
}

CAMPOS_OPCIONALES = {"summary": str, "tags": list}

TIPOS_DE_FUENTE = {
    "blog_oficial",
    "changelog",
    "repositorio",
    "newsletter",
    "boletin_regulatorio",
}

CATEGORIAS = {
    "modelo",
    "api",
    "herramienta_open_source",
    "investigacion",
    "regulacion",
    "producto",
}

PATRON_ID = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$")

FORMATO_FECHA = "%Y-%m-%d"
FORMATO_INSTANTE = "%Y-%m-%dT%H:%M:%SZ"


def leer_instante(valor):
    """Devuelve el datetime de un instante UTC o None si el formato no cuadra."""
    try:
        return datetime.strptime(valor, FORMATO_INSTANTE)
    except ValueError:
        return None


def revisar_tipos(objeto, campos, prefijo, errores):
    """Comprueba que estén los campos obligatorios y que su tipo sea el esperado."""
    for campo, tipo in campos.items():
        if campo not in objeto:
            errores.append(prefijo + "falta el campo obligatorio '" + campo + "'")
            continue
        valor = objeto[campo]
        # bool es subclase de int en Python y no sirve como item_count.
        if tipo is int and isinstance(valor, bool):
            errores.append(prefijo + "'" + campo + "' debe ser un entero")
        elif not isinstance(valor, tipo):
            errores.append(
                prefijo + "'" + campo + "' debe ser de tipo " + tipo.__name__
            )


def validar_noticia(item, posicion, errores):
    prefijo = "items[" + str(posicion) + "]: "
    if not isinstance(item, dict):
        errores.append(prefijo + "cada entrada debe ser un objeto")
        return None

    revisar_tipos(item, CAMPOS_NOTICIA, prefijo, errores)

    for campo, tipo in CAMPOS_OPCIONALES.items():
        if campo in item and not isinstance(item[campo], tipo):
            errores.append(prefijo + "'" + campo + "' debe ser de tipo " + tipo.__name__)

    identificador = item.get("id")
    if isinstance(identificador, str) and not PATRON_ID.match(identificador):
        errores.append(
            prefijo + "'id' no sigue el patrón YYYY-MM-DD-fuente-titulo-corto: "
            + identificador
        )

    titulo = item.get("title")
    if isinstance(titulo, str) and (not titulo.strip() or len(titulo) > 200):
        errores.append(prefijo + "'title' debe tener entre 1 y 200 caracteres")

    resumen = item.get("summary")
    if isinstance(resumen, str) and len(resumen) > 280:
        errores.append(prefijo + "'summary' supera los 280 caracteres")

    etiquetas = item.get("tags")
    if isinstance(etiquetas, list):
        if any(not isinstance(t, str) or not t.strip() for t in etiquetas):
            errores.append(prefijo + "'tags' solo admite cadenas no vacías")
        if len(set(etiquetas)) != len(etiquetas):
            errores.append(prefijo + "'tags' tiene etiquetas repetidas")

    tipo_fuente = item.get("source_type")
    if isinstance(tipo_fuente, str) and tipo_fuente not in TIPOS_DE_FUENTE:
        errores.append(prefijo + "'source_type' fuera del catálogo: " + tipo_fuente)

    categoria = item.get("category")
    if isinstance(categoria, str) and categoria not in CATEGORIAS:
        errores.append(prefijo + "'category' fuera del catálogo: " + categoria)

    url = item.get("url")
    if isinstance(url, str) and not url.startswith("https://"):
        errores.append(prefijo + "'url' debe ser un enlace https")

    publicado = None
    for campo in ("published_at", "collected_at"):
        valor = item.get(campo)
        if not isinstance(valor, str):
            continue
        instante = leer_instante(valor)
        if instante is None:
            errores.append(
                prefijo + "'" + campo + "' no usa el formato YYYY-MM-DDTHH:MM:SSZ: "
                + valor
            )
        elif campo == "published_at":
            publicado = instante

    return publicado


def validar_snapshot(ruta):
    errores = []

    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return ["el archivo no es JSON válido: " + str(error)]

    if not isinstance(contenido, dict):
        return ["el snapshot debe ser un objeto JSON"]

    revisar_tipos(contenido, CAMPOS_SNAPSHOT, "", errores)

    if contenido.get("version") != VERSION_CONTRATO:
        errores.append("'version' debe ser " + VERSION_CONTRATO)

    fecha = contenido.get("snapshot_date")
    if isinstance(fecha, str):
        try:
            datetime.strptime(fecha, FORMATO_FECHA)
        except ValueError:
            errores.append("'snapshot_date' no usa el formato YYYY-MM-DD: " + fecha)
        else:
            if fecha != ruta.stem:
                errores.append(
                    "'snapshot_date' (" + fecha + ") no coincide con el nombre del "
                    "archivo (" + ruta.stem + ")"
                )

    generado = contenido.get("generated_at")
    if isinstance(generado, str) and leer_instante(generado) is None:
        errores.append("'generated_at' no usa el formato YYYY-MM-DDTHH:MM:SSZ")

    items = contenido.get("items")
    if not isinstance(items, list):
        return errores

    if not items:
        errores.append("'items' no puede estar vacío")

    total = contenido.get("item_count")
    if isinstance(total, int) and not isinstance(total, bool) and total != len(items):
        errores.append(
            "'item_count' dice " + str(total) + " pero hay " + str(len(items))
            + " entradas"
        )

    vistos = set()
    publicaciones = []
    for posicion, item in enumerate(items):
        publicado = validar_noticia(item, posicion, errores)
        publicaciones.append(publicado)
        if isinstance(item, dict):
            identificador = item.get("id")
            if isinstance(identificador, str):
                if identificador in vistos:
                    errores.append("'id' repetido en el snapshot: " + identificador)
                vistos.add(identificador)

    conocidas = [p for p in publicaciones if p is not None]
    if len(conocidas) == len(publicaciones):
        for anterior, siguiente in zip(publicaciones, publicaciones[1:]):
            if anterior < siguiente:
                errores.append(
                    "'items' debe ir de la publicación más reciente a la más antigua"
                )
                break

    return errores


def main(argv):
    if len(argv) != 2:
        print("uso: validar_snapshot.py RUTA_DEL_SNAPSHOT", file=sys.stderr)
        return 2

    ruta = Path(argv[1])
    if not ruta.is_file():
        print("no existe el archivo: " + str(ruta), file=sys.stderr)
        return 2

    errores = validar_snapshot(ruta)
    if errores:
        print(str(ruta) + ": " + str(len(errores)) + " error(es)", file=sys.stderr)
        for error in errores:
            print("  - " + error, file=sys.stderr)
        return 1

    print(str(ruta) + ": el snapshot cumple el contrato " + VERSION_CONTRATO)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
