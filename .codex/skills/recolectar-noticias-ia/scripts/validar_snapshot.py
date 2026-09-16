#!/usr/bin/env python3
"""Valida un snapshot diario del radar contra el contrato de datos 2.0.

Uso:
    python3 validar_snapshot.py data/snapshots/2026-09-15.json
    python3 validar_snapshot.py data/snapshots/2026-09-15.json --previous data/snapshots/2026-09-14.json

Sin `--previous` comprueba el archivo contra el contrato. Con `--previous`
comprueba además la deduplicación entre días. Sale con 0 si todo cumple y con
1 listando los errores. Solo usa la biblioteca estándar.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

VERSION_CONTRATO = "2.0"

CAMPOS_SNAPSHOT = {
    "version": str,
    "snapshot_date": str,
    "generated_at": str,
    "item_count": int,
    "items": list,
    "dedup": dict,
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
    "evidence": dict,
    "dedup_key": str,
    "status": str,
}

CAMPOS_EVIDENCIA = {"url": str, "quote": str}
CAMPOS_OPCIONALES = {"summary": str, "tags": list, "status_note": str}
CAMPOS_DESCARTE = {"dedup_key": str, "duplicate_of": str, "reason": str}

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

ESTADOS = {"pendiente", "procesado", "descartado"}
ESTADOS_QUE_EXIGEN_NOTA = {"pendiente", "descartado"}

# Parámetros que solo sirven para medir tráfico: no identifican la publicación.
PARAMETROS_DE_SEGUIMIENTO = {"ref", "fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "si"}

PATRON_ID = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")
PATRON_FUENTE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PATRON_CLAVE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*:[0-9a-f]{12}$")
PATRON_DIA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

FORMATO_DIA = "%Y-%m-%d"
FORMATO_INSTANTE = "%Y-%m-%dT%H:%M:%SZ"
LONGITUD_DIGESTO = 12


def canonicalizar_url(url):
    """Reduce una URL a lo que identifica la publicación.

    Baja a minúsculas el esquema y el host, quita el `www.` y la barra final,
    descarta los parámetros de seguimiento y ordena los que quedan. El
    fragmento SÍ se conserva: en un changelog de una sola página es lo único
    que distingue una entrada de otra.
    """
    partes = urlsplit(url.strip())
    host = partes.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    consulta = sorted(
        (clave, valor)
        for clave, valor in parse_qsl(partes.query, keep_blank_values=True)
        if clave.lower() not in PARAMETROS_DE_SEGUIMIENTO
        and not clave.lower().startswith("utm_")
    )
    cola = "?" + "&".join(f"{c}={v}" for c, v in consulta) if consulta else ""
    fragmento = f"#{partes.fragment}" if partes.fragment else ""

    return host + partes.path.rstrip("/") + cola + fragmento


def clave_dedup(source, url):
    """Construye la clave: `source` más el digesto de la URL canónica."""
    digesto = hashlib.sha256(canonicalizar_url(url).encode("utf-8")).hexdigest()
    return f"{source}:{digesto[:LONGITUD_DIGESTO]}"


def leer_instante(valor):
    """Devuelve el datetime de un instante UTC, o None si el formato no cuadra."""
    try:
        return datetime.strptime(valor, FORMATO_INSTANTE)
    except ValueError:
        return None


def revisar_tipos(objeto, campos, prefijo, errores):
    """Comprueba que estén los campos obligatorios y con el tipo esperado."""
    for campo, tipo in campos.items():
        if campo not in objeto:
            errores.append(f"{prefijo}falta el campo obligatorio '{campo}'")
            continue
        valor = objeto[campo]
        # bool es subclase de int en Python y no sirve como item_count.
        if tipo is int and isinstance(valor, bool):
            errores.append(f"{prefijo}'{campo}' debe ser un entero")
        elif not isinstance(valor, tipo):
            errores.append(f"{prefijo}'{campo}' debe ser de tipo {tipo.__name__}")


def revisar_sobrantes(objeto, permitidos, prefijo, errores):
    sobrantes = set(objeto) - set(permitidos)
    if sobrantes:
        errores.append(f"{prefijo}campos no previstos: {', '.join(sorted(sobrantes))}")


def validar_evidencia(item, prefijo, errores):
    evidencia = item.get("evidence")
    if not isinstance(evidencia, dict):
        return

    revisar_tipos(evidencia, CAMPOS_EVIDENCIA, f"{prefijo}evidence: ", errores)
    revisar_sobrantes(evidencia, CAMPOS_EVIDENCIA, f"{prefijo}evidence: ", errores)

    enlace = evidencia.get("url")
    if isinstance(enlace, str) and not enlace.startswith("https://"):
        errores.append(f"{prefijo}'evidence.url' debe ser un enlace https")

    cita = evidencia.get("quote")
    if isinstance(cita, str) and (not cita.strip() or len(cita) > 300):
        errores.append(f"{prefijo}'evidence.quote' debe tener entre 1 y 300 caracteres")


def validar_estado(item, prefijo, errores):
    estado = item.get("status")
    if not isinstance(estado, str):
        return

    if estado not in ESTADOS:
        cerrada = ", ".join(sorted(ESTADOS))
        errores.append(f"{prefijo}'status' fuera de la lista cerrada ({cerrada}): {estado}")
        return

    nota = item.get("status_note")
    if estado in ESTADOS_QUE_EXIGEN_NOTA:
        if not isinstance(nota, str) or not nota.strip():
            errores.append(f"{prefijo}'status' = {estado} exige 'status_note' con el motivo")
    elif nota is not None:
        errores.append(f"{prefijo}'status_note' solo se escribe si el estado no es procesado")


def validar_clave(item, prefijo, errores):
    clave = item.get("dedup_key")
    if not isinstance(clave, str):
        return

    if not PATRON_CLAVE.match(clave):
        errores.append(f"{prefijo}'dedup_key' no sigue el patrón fuente:digesto12: {clave}")
        return

    fuente, enlace = item.get("source"), item.get("url")
    if isinstance(fuente, str) and isinstance(enlace, str):
        esperada = clave_dedup(fuente, enlace)
        if clave != esperada:
            errores.append(
                f"{prefijo}'dedup_key' no corresponde a source + URL canónica: dice "
                f"{clave} y debería decir {esperada}"
            )


def validar_identificador(item, prefijo, errores):
    identificador, fuente = item.get("id"), item.get("source")
    if not isinstance(identificador, str):
        return

    if not PATRON_ID.match(identificador):
        errores.append(
            f"{prefijo}'id' no sigue el patrón YYYY-MM-DD-fuente-titulo-corto: {identificador}"
        )
        return

    publicado = item.get("published_at")
    if isinstance(publicado, str) and isinstance(fuente, str):
        esperado = f"{publicado[:10]}-{fuente}-"
        if not identificador.startswith(esperado):
            errores.append(
                f"{prefijo}'id' debe empezar por la fecha de publicación y la fuente "
                f"({esperado}…): {identificador}"
            )


def validar_noticia(item, posicion, errores):
    prefijo = f"items[{posicion}]: "
    if not isinstance(item, dict):
        errores.append(f"{prefijo}cada entrada debe ser un objeto")
        return None

    revisar_tipos(item, CAMPOS_NOTICIA, prefijo, errores)
    revisar_sobrantes(item, set(CAMPOS_NOTICIA) | set(CAMPOS_OPCIONALES), prefijo, errores)

    for campo, tipo in CAMPOS_OPCIONALES.items():
        if campo in item and not isinstance(item[campo], tipo):
            errores.append(f"{prefijo}'{campo}' debe ser de tipo {tipo.__name__}")

    fuente = item.get("source")
    if isinstance(fuente, str) and not PATRON_FUENTE.match(fuente):
        errores.append(
            f"{prefijo}'source' debe ser el identificador del catálogo en minúsculas "
            f"y con guiones: {fuente}"
        )

    validar_identificador(item, prefijo, errores)

    titulo = item.get("title")
    if isinstance(titulo, str) and (not titulo.strip() or len(titulo) > 200):
        errores.append(f"{prefijo}'title' debe tener entre 1 y 200 caracteres")

    resumen = item.get("summary")
    if isinstance(resumen, str):
        if not resumen.strip():
            errores.append(f"{prefijo}'summary' vacío: si no hay resumen, se omite el campo")
        elif len(resumen) > 280:
            errores.append(f"{prefijo}'summary' supera los 280 caracteres")

    etiquetas = item.get("tags")
    if isinstance(etiquetas, list):
        if any(not isinstance(t, str) or not t.strip() for t in etiquetas):
            errores.append(f"{prefijo}'tags' solo admite cadenas no vacías")
        if len(set(etiquetas)) != len(etiquetas):
            errores.append(f"{prefijo}'tags' tiene etiquetas repetidas")

    tipo_fuente = item.get("source_type")
    if isinstance(tipo_fuente, str) and tipo_fuente not in TIPOS_DE_FUENTE:
        errores.append(f"{prefijo}'source_type' fuera del catálogo: {tipo_fuente}")

    categoria = item.get("category")
    if isinstance(categoria, str) and categoria not in CATEGORIAS:
        errores.append(f"{prefijo}'category' fuera del catálogo: {categoria}")

    url = item.get("url")
    if isinstance(url, str) and not url.startswith("https://"):
        errores.append(f"{prefijo}'url' debe ser un enlace https")

    validar_evidencia(item, prefijo, errores)
    validar_estado(item, prefijo, errores)
    validar_clave(item, prefijo, errores)

    publicado = None
    for campo in ("published_at", "collected_at"):
        valor = item.get(campo)
        if not isinstance(valor, str):
            continue
        instante = leer_instante(valor)
        if instante is None:
            errores.append(
                f"{prefijo}'{campo}' no usa el formato YYYY-MM-DDTHH:MM:SSZ: {valor}"
            )
        elif campo == "published_at":
            publicado = instante

    return publicado


def validar_dedup(contenido, claves_del_dia, errores):
    """Revisa el bloque `dedup`: la referencia anterior y los descartes."""
    dedup = contenido.get("dedup")
    if not isinstance(dedup, dict):
        return

    revisar_sobrantes(dedup, {"previous_snapshot", "discarded"}, "dedup: ", errores)

    if "previous_snapshot" not in dedup:
        errores.append("dedup: falta el campo obligatorio 'previous_snapshot'")
    else:
        anterior = dedup["previous_snapshot"]
        if anterior is not None and (
            not isinstance(anterior, str) or not PATRON_DIA.match(anterior)
        ):
            errores.append("dedup: 'previous_snapshot' debe ser una fecha YYYY-MM-DD o null")

    descartes = dedup.get("discarded")
    if not isinstance(descartes, list):
        errores.append("dedup: 'discarded' debe ser una lista (vacía si no hubo descartes)")
        return

    vistas = set()
    for posicion, descarte in enumerate(descartes):
        prefijo = f"dedup.discarded[{posicion}]: "
        if not isinstance(descarte, dict):
            errores.append(f"{prefijo}cada descarte debe ser un objeto")
            continue

        revisar_tipos(descarte, CAMPOS_DESCARTE, prefijo, errores)
        revisar_sobrantes(descarte, CAMPOS_DESCARTE, prefijo, errores)

        clave = descarte.get("dedup_key")
        if isinstance(clave, str):
            if not PATRON_CLAVE.match(clave):
                errores.append(f"{prefijo}'dedup_key' no sigue el patrón fuente:digesto12: {clave}")
            if clave in claves_del_dia:
                errores.append(f"{prefijo}la clave descartada también está en 'items': {clave}")
            if clave in vistas:
                errores.append(f"{prefijo}clave descartada dos veces: {clave}")
            vistas.add(clave)

        duplicado = descarte.get("duplicate_of")
        if isinstance(duplicado, str) and not PATRON_ID.match(duplicado):
            errores.append(f"{prefijo}'duplicate_of' debe ser el 'id' de la entrada original")

        motivo = descarte.get("reason")
        if isinstance(motivo, str) and not motivo.strip():
            errores.append(f"{prefijo}'reason' no puede estar vacío")


def validar_contra_anterior(contenido, ruta_anterior, errores):
    """Comprueba la deduplicación contra el snapshot del día anterior."""
    try:
        anterior = json.loads(ruta_anterior.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errores.append(f"no se pudo leer el snapshot anterior: {error}")
        return

    if not isinstance(anterior, dict) or not isinstance(anterior.get("items"), list):
        errores.append("el snapshot anterior no tiene una lista 'items'")
        return

    claves_anteriores = {
        item["dedup_key"]: item.get("id")
        for item in anterior["items"]
        if isinstance(item, dict) and isinstance(item.get("dedup_key"), str)
    }

    dedup = contenido.get("dedup") if isinstance(contenido.get("dedup"), dict) else {}
    declarada = dedup.get("previous_snapshot")
    if declarada != anterior.get("snapshot_date"):
        errores.append(
            f"dedup: 'previous_snapshot' dice {declarada!r} pero el archivo anterior "
            f"cubre {anterior.get('snapshot_date')!r}"
        )

    for posicion, item in enumerate(contenido.get("items", [])):
        if not isinstance(item, dict):
            continue
        clave = item.get("dedup_key")
        if isinstance(clave, str) and clave in claves_anteriores:
            errores.append(
                f"items[{posicion}]: la clave ya estaba en el snapshot anterior "
                f"({claves_anteriores[clave]}): {clave}"
            )

    for posicion, descarte in enumerate(dedup.get("discarded") or []):
        if not isinstance(descarte, dict):
            continue
        prefijo = f"dedup.discarded[{posicion}]: "
        clave, duplicado = descarte.get("dedup_key"), descarte.get("duplicate_of")
        if not isinstance(clave, str):
            continue
        if clave not in claves_anteriores:
            errores.append(f"{prefijo}la clave no existe en el snapshot anterior: {clave}")
        elif duplicado != claves_anteriores[clave]:
            errores.append(
                f"{prefijo}'duplicate_of' dice {duplicado!r} pero esa clave pertenece "
                f"a {claves_anteriores[clave]!r}"
            )


def validar_snapshot(ruta, ruta_anterior=None):
    errores = []

    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"el archivo no es JSON válido: {error}"]

    if not isinstance(contenido, dict):
        return ["el snapshot debe ser un objeto JSON"]

    revisar_tipos(contenido, CAMPOS_SNAPSHOT, "", errores)
    revisar_sobrantes(contenido, CAMPOS_SNAPSHOT, "", errores)

    if contenido.get("version") != VERSION_CONTRATO:
        errores.append(f"'version' debe ser {VERSION_CONTRATO}")

    fecha = contenido.get("snapshot_date")
    if isinstance(fecha, str):
        try:
            datetime.strptime(fecha, FORMATO_DIA)
        except ValueError:
            errores.append(f"'snapshot_date' no usa el formato YYYY-MM-DD: {fecha}")
        else:
            if fecha != ruta.stem:
                errores.append(
                    f"'snapshot_date' ({fecha}) no coincide con el nombre del archivo "
                    f"({ruta.stem})"
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
        errores.append(f"'item_count' dice {total} pero hay {len(items)} entradas")

    ids_vistos, claves_vistas, publicaciones = set(), set(), []
    for posicion, item in enumerate(items):
        publicaciones.append(validar_noticia(item, posicion, errores))
        if not isinstance(item, dict):
            continue

        identificador = item.get("id")
        if isinstance(identificador, str):
            if identificador in ids_vistos:
                errores.append(f"'id' repetido en el snapshot: {identificador}")
            ids_vistos.add(identificador)

        clave = item.get("dedup_key")
        if isinstance(clave, str):
            if clave in claves_vistas:
                errores.append(f"'dedup_key' repetida en el snapshot: {clave}")
            claves_vistas.add(clave)

    if all(p is not None for p in publicaciones):
        if any(a < b for a, b in zip(publicaciones, publicaciones[1:])):
            errores.append("'items' debe ir de la publicación más reciente a la más antigua")

    validar_dedup(contenido, claves_vistas, errores)

    if ruta_anterior is not None:
        validar_contra_anterior(contenido, ruta_anterior, errores)

    return errores


def main(argv):
    analizador = argparse.ArgumentParser(
        description=f"Valida un snapshot del radar contra el contrato {VERSION_CONTRATO}."
    )
    analizador.add_argument("snapshot", help="ruta del snapshot a validar")
    analizador.add_argument(
        "--previous",
        metavar="RUTA",
        help="snapshot del día anterior, para comprobar la deduplicación entre días",
    )
    argumentos = analizador.parse_args(argv[1:])

    ruta = Path(argumentos.snapshot)
    if not ruta.is_file():
        print(f"no existe el archivo: {ruta}", file=sys.stderr)
        return 2

    ruta_anterior = None
    if argumentos.previous:
        ruta_anterior = Path(argumentos.previous)
        if not ruta_anterior.is_file():
            print(f"no existe el snapshot anterior: {ruta_anterior}", file=sys.stderr)
            return 2

    errores = validar_snapshot(ruta, ruta_anterior)
    if errores:
        print(f"{ruta}: {len(errores)} error(es)", file=sys.stderr)
        for error in errores:
            print(f"  - {error}", file=sys.stderr)
        return 1

    mensaje = f"{ruta}: cumple el contrato {VERSION_CONTRATO}"
    if ruta_anterior is not None:
        mensaje += f" y no repite ninguna clave de {ruta_anterior.stem}"
    print(mensaje)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
