#!/usr/bin/env python3
"""Recolector del radar: del catálogo de fuentes al snapshot del día.

Ejecuta la parte mecánica de la recolección: leer cada fuente, normalizar sus
publicaciones al contrato 2.0, calcular `id` y `dedup_key`, deduplicar contra
el día anterior y escribir el archivo. No decide qué merece entrar ni redacta
resúmenes; el texto editorial llega desde fuera con --resumenes.

Es determinista a propósito: con las mismas entradas produce los mismos bytes,
así que repetir la pasada no genera diff. Solo biblioteca estándar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / ".codex/skills/recolectar-noticias-ia/references/fuentes.md"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

VERSION_CONTRATO = "2.0"
FORMATO_INSTANTE = "%Y-%m-%dT%H:%M:%SZ"
LARGO_CITA, LARGO_TITULO, LARGO_DIGESTO = 300, 200, 12
PARAMETROS_DE_SEGUIMIENTO = {"ref", "fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "si"}

# Etiqueta que publica la fuente -> categoría cerrada del contrato.
SECCIONES = {
    "product": "producto", "feature": "producto",
    "api": "api", "platform": "api",
    "model": "modelo", "models": "modelo",
    "research": "investigacion", "paper": "investigacion", "report": "investigacion",
    "library": "herramienta_open_source", "open-source": "herramienta_open_source",
    "release": "herramienta_open_source",
    "legal": "regulacion", "regulation": "regulacion",
}


def canonicalizar_url(url):
    """Copia exacta de la canonización del validador: si difirieran, el tool
    escribiría claves que el validador rechaza."""
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
    digesto = hashlib.sha256(canonicalizar_url(url).encode("utf-8")).hexdigest()
    return f"{source}:{digesto[:LARGO_DIGESTO]}"


def convertir_en_slug(texto, palabras=5):
    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    piezas = [p for p in re.split(r"[^a-zA-Z0-9]+", plano.lower()) if p]
    return "-".join(piezas[:palabras]) or "sin-titulo"


def recortar_cita(texto):
    limpio = " ".join(texto.split())
    if len(limpio) <= LARGO_CITA:
        return limpio
    return limpio[:LARGO_CITA].rsplit(" ", 1)[0] or limpio[:LARGO_CITA]


def leer_catalogo(ruta):
    """Lee la tabla de fuentes. El catálogo es la única fuente de verdad: no hay
    copia en JSON que pueda quedarse atrás."""
    fuentes = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if not linea.startswith("|") or set(linea) <= set("|- "):
            continue
        celdas = [c.strip().strip("`") for c in linea.strip("|").split("|")]
        if len(celdas) < 6 or celdas[0] in ("source", ""):
            continue
        fuentes.append(dict(zip(
            ("source", "nombre", "source_type", "url", "feed", "revision"), celdas
        )))
    if not fuentes:
        raise SystemExit(f"el catálogo {ruta} no tiene ninguna fuente legible")
    return fuentes


def leer_desde_fixture(fuente, directorio):
    ruta = directorio / f"{fuente['source']}.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {"items": []}


def leer_desde_red(fuente, espera):
    """Lee el feed Atom/RSS y lo deja en la misma forma que los fixtures."""
    peticion = Request(fuente["feed"], headers={"User-Agent": "AIRadar/2.0"})
    with urlopen(peticion, timeout=espera) as respuesta:
        arbol = ElementTree.fromstring(respuesta.read())

    items = []
    entradas = arbol.findall(".//{http://www.w3.org/2005/Atom}entry") or arbol.findall(".//item")
    for entrada in entradas:
        campos = {re.sub(r"^\{.*\}", "", hijo.tag): hijo for hijo in entrada}
        def texto(nombre):
            return (campos[nombre].text or "").strip() if nombre in campos else ""

        enlace = campos.get("link")
        cuerpo = next((n for n in ("summary", "description", "content") if n in campos), "")
        fecha = next((n for n in ("updated", "published", "pubDate") if n in campos), "")
        seccion = campos.get("category")
        items.append({
            "title": texto("title"),
            "url": (enlace.get("href") or enlace.text or "").strip() if enlace is not None else "",
            "published_at": texto(fecha),
            "section": ((seccion.get("term") or seccion.text or "").strip()
                        if seccion is not None else ""),
            "quote": texto(cuerpo),
        })
    return {"items": items}


def recolectar_fuente(fuente, opciones):
    """Devuelve (fuente, payload, error). Una fuente caída no detiene la pasada."""
    try:
        if opciones.red:
            return fuente, leer_desde_red(fuente, opciones.espera), None
        return fuente, leer_desde_fixture(fuente, opciones.fixtures), None
    except Exception as error:
        return fuente, {"items": []}, f"{type(error).__name__}: {error}"


def normalizar(fuente, bruto, recolectado_en, resumenes):
    """Convierte una publicación en bruto en una entrada del contrato 2.0."""
    titulo = " ".join(str(bruto.get("title", "")).split())[:LARGO_TITULO]
    url = str(bruto.get("url", "")).strip()
    publicado = str(bruto.get("published_at", "")).strip()
    if not (titulo and url and publicado):
        return None, "faltan título, enlace o fecha de publicación"
    try:
        datetime.strptime(publicado, FORMATO_INSTANTE)
    except ValueError:
        return None, f"fecha de publicación fuera de formato: {publicado}"

    cita = recortar_cita(str(bruto.get("quote", "")))
    if not cita:
        # El contrato exige una cita literal: sin ella la entrada no se escribe,
        # porque la alternativa sería redactar la prueba.
        return None, "la fuente no devolvió ninguna frase citable"

    seccion = str(bruto.get("section", "")).strip().lower()
    categoria = SECCIONES.get(seccion)
    pendiente = None
    if categoria is None:
        categoria = "regulacion" if fuente["source_type"] == "boletin_regulatorio" else "producto"
        pendiente = (
            f"La fuente etiquetó la publicación como «{seccion or 'sin sección'}», que no "
            "corresponde a ninguna categoría del contrato: falta clasificarla a mano."
        )

    identificador = f"{publicado[:10]}-{fuente['source']}-{convertir_en_slug(titulo)}"
    entrada = {
        "id": identificador,
        "title": titulo,
        "url": url,
        "source": fuente["source"],
        "source_type": fuente["source_type"],
        "category": categoria,
        "published_at": publicado,
        "collected_at": recolectado_en,
        "evidence": {"url": str(bruto.get("evidence_url") or url), "quote": cita},
        "dedup_key": clave_dedup(fuente["source"], url),
        "status": "pendiente" if pendiente else "procesado",
    }
    if pendiente:
        entrada["status_note"] = pendiente
    # El paso editorial escribe antes de que exista el `id`, así que puede
    # indexar su texto por la URL, que sí conoce.
    resumen = resumenes.get(identificador) or resumenes.get(url)
    if resumen:
        entrada["summary"] = " ".join(resumen.split())
    entrada["tags"] = [categoria, fuente["source_type"], fuente["source"]]
    return entrada, None


def cargar_anterior(ruta):
    if ruta is None:
        return None, {}
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    claves = {
        item["dedup_key"]: item["id"]
        for item in contenido.get("items", [])
        if isinstance(item, dict) and "dedup_key" in item
    }
    return contenido.get("snapshot_date"), claves


def armar_snapshot(entradas, fecha, generado_en, anterior_fecha, claves_anteriores):
    items, descartes, claves_del_dia = [], [], set()
    for entrada in entradas:
        clave = entrada["dedup_key"]
        if clave in claves_anteriores:
            descartes.append({
                "dedup_key": clave,
                "duplicate_of": claves_anteriores[clave],
                "reason": ("La fuente volvió a listar la publicación con la misma URL "
                           f"canónica; ya estaba registrada en el snapshot {anterior_fecha}."),
            })
        elif clave not in claves_del_dia:
            claves_del_dia.add(clave)
            items.append(entrada)

    # Más reciente primero; el `id` desempata para que el orden no dependa del reloj.
    items = sorted(items, key=lambda e: (e["published_at"], e["id"]), reverse=True)
    vistos = {}
    for item in items:
        vistos[item["id"]] = vistos.get(item["id"], 0) + 1
        if vistos[item["id"]] > 1:
            item["id"] = f"{item['id']}-{vistos[item['id']]}"

    return {
        "version": VERSION_CONTRATO,
        "snapshot_date": fecha,
        "generated_at": generado_en,
        "item_count": len(items),
        "items": items,
        "dedup": {
            "previous_snapshot": anterior_fecha,
            "discarded": sorted(descartes, key=lambda d: d["dedup_key"]),
        },
    }


def volcar(contenido):
    """Sangría de dos espacios y `tags` en una línea, como el resto del repo."""
    texto = json.dumps(contenido, ensure_ascii=False, indent=2)
    return re.sub(
        r'"tags": \[\n\s+([^\]]+?)\n\s+\]',
        lambda m: '"tags": [' + " ".join(x.strip() for x in m.group(1).splitlines()) + "]",
        texto,
    ) + "\n"


def leer_resumenes(ruta):
    if ruta is None:
        return {}
    texto = sys.stdin.read() if str(ruta) == "-" else Path(ruta).read_text(encoding="utf-8")
    return json.loads(texto) if texto.strip() else {}


def construir_analizador():
    a = argparse.ArgumentParser(description="Arma el snapshot diario del radar de IA.")
    a.add_argument("--fecha", required=True, help="día del snapshot en UTC (YYYY-MM-DD)")
    a.add_argument("--fuente", action="append", default=[], help="limita a esta fuente (repetible)")
    a.add_argument("--anterior", type=Path, help="snapshot del día anterior, para deduplicar")
    a.add_argument("--salida", type=Path, help="archivo a escribir")
    a.add_argument("--resumenes", help="JSON {id: resumen} del paso editorial, o '-' para stdin")
    a.add_argument("--catalogo", type=Path, default=CATALOGO, help="catálogo de fuentes")
    a.add_argument("--fixtures", type=Path, default=FIXTURES, help="carpeta de fixtures")
    a.add_argument("--red", action="store_true", help="lee los feeds reales en vez de los fixtures")
    a.add_argument("--espera", type=float, default=20.0, help="tiempo de espera por fuente")
    a.add_argument("--generado-en", dest="generado_en", help="instante de cierre del snapshot")
    a.add_argument("--dry-run", action="store_true", help="no escribe: solo informa qué haría")
    return a


def main(argv):
    opciones = construir_analizador().parse_args(argv)
    try:
        datetime.strptime(opciones.fecha, "%Y-%m-%d")
    except ValueError:
        raise SystemExit(f"--fecha debe ser YYYY-MM-DD: {opciones.fecha}")

    fuentes = leer_catalogo(opciones.catalogo)
    if opciones.fuente:
        desconocidas = set(opciones.fuente) - {f["source"] for f in fuentes}
        if desconocidas:
            raise SystemExit(f"fuera del catálogo: {', '.join(sorted(desconocidas))}")
        fuentes = [f for f in fuentes if f["source"] in set(opciones.fuente)]

    resumenes = leer_resumenes(opciones.resumenes)
    with ThreadPoolExecutor(max_workers=min(8, len(fuentes))) as piscina:
        lecturas = list(piscina.map(lambda f: recolectar_fuente(f, opciones), fuentes))

    entradas, incidencias, instantes = [], [], []
    for fuente, payload, error in lecturas:
        if error:
            incidencias.append(f"{fuente['source']}: no respondió ({error})")
            continue
        recolectado = payload.get("fetched_at") or f"{opciones.fecha}T00:00:00Z"
        instantes.append(recolectado)
        for bruto in payload.get("items", []):
            entrada, motivo = normalizar(fuente, bruto, recolectado, resumenes)
            if entrada is None:
                incidencias.append(f"{fuente['source']}: entrada sin escribir ({motivo})")
            else:
                entradas.append(entrada)

    if not entradas:
        print("ninguna fuente aportó entradas: no se escribe el archivo", file=sys.stderr)
        return 1

    anterior_fecha, claves_anteriores = cargar_anterior(opciones.anterior)
    snapshot = armar_snapshot(
        entradas, opciones.fecha, opciones.generado_en or max(instantes),
        anterior_fecha, claves_anteriores,
    )

    pendientes = sum(1 for i in snapshot["items"] if i["status"] == "pendiente")
    destino = opciones.salida or RAIZ / "data/snapshots" / f"{opciones.fecha}.json"
    print(f"{opciones.fecha}: {snapshot['item_count']} entradas de {len(fuentes)} fuentes "
          f"({pendientes} pendientes, "
          f"{len(snapshot['dedup']['discarded'])} descartadas por repetidas)")
    for incidencia in incidencias:
        print(f"  aviso · {incidencia}")

    if opciones.dry_run:
        print(f"  dry-run: no se escribió {destino}")
        return 0

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(volcar(snapshot), encoding="utf-8")
    print(f"  escrito {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
