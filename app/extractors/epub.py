"""Extractor de EPUB sin dependencias copyleft: zipfile + lxml (no usa ebooklib, que es AGPL)."""
from __future__ import annotations

import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

from lxml import etree
from lxml import html as lhtml

from app.cleaning.chapters import is_skippable_title
from app.cleaning.normalize import clean_chapter_text
from app.errors import UserError
from app.extractors.base import Book, Chapter

_BLOCKS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre", "dt", "dd",
           "figcaption", "caption", "tr", "div", "section", "article", "td", "th", "ul", "ol",
           "table", "aside", "header", "footer"}
_LEAF_BLOCKS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre", "dt", "dd",
                "figcaption", "caption", "td", "th", "div"}
_HEADINGS = {"h1", "h2", "h3"}


def _local(tag: object) -> str:
    return tag.split("}")[-1].lower() if isinstance(tag, str) else ""


@dataclass
class _Block:
    tag: str
    text: str
    ids: set[str] = field(default_factory=set)


def _drop_noise(root: lhtml.HtmlElement) -> None:
    """Elimina scripts, estilos, navegación, llamadas a nota y notas al pie."""
    for el in list(root.iter()):
        tag = _local(el.tag)
        etype = (el.get("epub:type") or el.get("{http://www.idpf.org/2007/ops}type") or "").lower()
        role = (el.get("role") or "").lower()
        noisy = (
            tag in {"script", "style", "nav", "rt", "head"}
            or "noteref" in etype or "footnote" in etype or "endnote" in etype
            or "doc-noteref" in role or "doc-footnote" in role or "doc-endnote" in role
            or (tag == "sup" and re.fullmatch(r"[\s\[\]\d*†‡a-z]{0,6}", "".join(el.itertext()).lower()))
        )
        if noisy and el.getparent() is not None:
            el.drop_tree()


def _has_block_desc(el: lhtml.HtmlElement) -> bool:
    return any(_local(d.tag) in _BLOCKS for d in el.iterdescendants())


def _blocks(root: lhtml.HtmlElement) -> list[_Block]:
    raw: list[_Block] = []
    for el in root.iter():
        tag = _local(el.tag)
        if tag not in _LEAF_BLOCKS or _has_block_desc(el):
            continue
        text = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
        ids = {el.get("id")} if el.get("id") else set()
        ids |= {a.get("id") or a.get("name") for a in el.iterdescendants() if a.get("id") or a.get("name")}
        raw.append(_Block(tag, text, {i for i in ids if i}))
    # un bloque vacío con id (<div id="cap2"/>) pasa su id al bloque con texto siguiente
    carried: set[str] = set()
    result = []
    for b in raw:
        if not b.text:
            carried |= b.ids
            continue
        b.ids |= carried
        carried = set()
        result.append(b)
    return result


def _decode_markup(data: bytes) -> str:
    """Decodifica (X)HTML respetando BOM/declaración; UTF-8 si no dice nada (lxml asumiría latin-1)."""
    if data.startswith(b"\xef\xbb\xbf"):
        enc = "utf-8-sig"
    elif data.startswith((b"\xff\xfe", b"\xfe\xff")):
        enc = "utf-16"
    else:
        m = re.search(rb"""(?:encoding|charset)\s*=\s*["']?([A-Za-z0-9_\-]+)""", data[:1024])
        enc = m.group(1).decode("ascii") if m else "utf-8"
    try:
        text = data.decode(enc)
    except (UnicodeDecodeError, LookupError):
        text = data.decode("utf-8", errors="replace")
    return re.sub(r"^\s*<\?xml[^>]*\?>", "", text)


def _parse_xhtml(data: bytes) -> lhtml.HtmlElement:
    root = lhtml.fromstring(_decode_markup(data))
    _drop_noise(root)
    return root


def _xp(node: etree._Element, expr: str) -> list:
    return node.xpath(expr)


def _toc_titles(z: zipfile.ZipFile, manifest: dict, opf: etree._Element) -> dict[str, str]:
    """Mapa 'ruta#fragmento' (o 'ruta') -> título, desde nav.xhtml (EPUB3) o toc.ncx (EPUB2)."""
    titles: dict[str, str] = {}

    def add(href: str, label: str, base: str) -> None:
        label = re.sub(r"\s+", " ", label).strip()
        if not href or not label:
            return
        path, _, frag = unquote(href).partition("#")
        full = posixpath.normpath(posixpath.join(base, path)) if path else base
        titles.setdefault(f"{full}#{frag}" if frag else full, label)

    nav = next((i for i in manifest.values() if "nav" in i["props"]), None)
    if nav:
        try:
            root = lhtml.fromstring(_decode_markup(z.read(nav["path"])))
            base = posixpath.dirname(nav["path"])
            for a in root.iter():
                if _local(a.tag) == "a" and a.get("href"):
                    add(a.get("href"), "".join(a.itertext()), base)
            if titles:
                return titles
        except (KeyError, etree.ParserError, ValueError):
            pass
    ncx_id = (_xp(opf, "//*[local-name()='spine']/@toc") or [""])[0]
    ncx = manifest.get(ncx_id) or next(
        (i for i in manifest.values() if i["type"] == "application/x-dtbncx+xml"), None)
    if ncx:
        try:
            root = etree.fromstring(z.read(ncx["path"]))
            base = posixpath.dirname(ncx["path"])
            for np_ in _xp(root, "//*[local-name()='navPoint']"):
                label = " ".join(_xp(np_, "./*[local-name()='navLabel']/*[local-name()='text']/text()"))
                src = (_xp(np_, "./*[local-name()='content']/@src") or [""])[0]
                add(src, label, base)
        except (KeyError, etree.XMLSyntaxError):
            pass
    return titles


def _read_opf(z: zipfile.ZipFile) -> tuple[etree._Element, str]:
    try:
        container = etree.fromstring(z.read("META-INF/container.xml"))
        opf_path = _xp(container, "//*[local-name()='rootfile']/@full-path")[0]
        return etree.fromstring(z.read(opf_path)), posixpath.dirname(opf_path)
    except (KeyError, IndexError, etree.XMLSyntaxError) as exc:
        raise UserError("epub_invalid", str(exc)) from exc


def _meta(opf: etree._Element, name: str) -> str:
    vals = _xp(opf, f"//*[local-name()='metadata']/*[local-name()='{name}']/text()")
    return ", ".join(v.strip() for v in vals if v.strip())


def _is_drm(z: zipfile.ZipFile) -> bool:
    if "META-INF/encryption.xml" not in z.namelist():
        return False
    enc = z.read("META-INF/encryption.xml")
    return b"EncryptedData" in enc and b"idpf.org/2008/embedding" not in enc


def extract_epub(path: Path) -> Book:
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise UserError("epub_invalid", "no es un ZIP válido") from exc
    with z:
        if _is_drm(z):
            raise UserError("epub_drm")
        opf, opf_dir = _read_opf(z)
        manifest = {}
        for item in _xp(opf, "//*[local-name()='manifest']/*[local-name()='item']"):
            manifest[item.get("id")] = {
                "path": posixpath.normpath(posixpath.join(opf_dir, unquote(item.get("href", "")))),
                "type": item.get("media-type", ""),
                "props": (item.get("properties") or "").split(),
            }
        spine = [manifest[i] for i in
                 _xp(opf, "//*[local-name()='spine']/*[local-name()='itemref']/@idref") if i in manifest]
        titles = _toc_titles(z, manifest, opf)

        chapters: list[Chapter] = []
        for item in spine:
            if "html" not in item["type"] and "xml" not in item["type"]:
                continue
            try:
                root = _parse_xhtml(z.read(item["path"]))
            except (KeyError, etree.ParserError, ValueError):
                continue
            blocks = _blocks(root)
            if blocks:
                chapters.extend(_split_document(item["path"], blocks, titles, chapters))
        cover, mime = _cover(z, opf, manifest)
        book = Book(
            title=_meta(opf, "title") or path.stem, author=_meta(opf, "creator"),
            language=(_meta(opf, "language") or "")[:2].lower(), cover=cover, cover_mime=mime,
        )
    cleaned: list[Chapter] = []
    for ch in chapters:
        body = clean_chapter_text(ch.text)
        if body:
            cleaned.append(Chapter(ch.title, body, included=not is_skippable_title(ch.title)))
    if not cleaned:
        raise UserError("empty_book")
    book.chapters = cleaned
    return book


def _split_document(path: str, blocks: list[_Block], titles: dict[str, str],
                    previous: list[Chapter]) -> list[Chapter]:
    """Convierte un documento del spine en uno o varios capítulos."""
    frags = {k.partition("#")[2]: v for k, v in titles.items()
             if "#" in k and k.partition("#")[0] == path}
    if len(frags) >= 2:  # varios capítulos dentro de un mismo archivo
        out: list[Chapter] = []
        cur_title, cur = "", []
        for b in blocks:
            hit = next((frags[i] for i in b.ids if i in frags), None)
            if hit:
                if cur:
                    out.append(Chapter(cur_title or "Sección", "\n\n".join(cur)))
                cur, cur_title = [], hit
                if b.tag in _HEADINGS:
                    continue  # el título se narra aparte; no se duplica
            cur.append(b.text)
        if cur:
            out.append(Chapter(cur_title or "Sección", "\n\n".join(cur)))
        return out

    title = titles.get(path, "")
    heading = next((b.text for b in blocks[:3] if b.tag in _HEADINGS), "")
    if not title and not heading and previous:  # continuación de un capítulo partido en archivos
        previous[-1].text += "\n\n" + "\n\n".join(b.text for b in blocks)
        return []
    body_blocks = blocks[1:] if blocks[0].tag in _HEADINGS else blocks
    name = title or heading or f"Sección {len(previous) + 1}"
    text = "\n\n".join(b.text for b in body_blocks) or heading
    return [Chapter(name, text)]


def _cover(z: zipfile.ZipFile, opf: etree._Element, manifest: dict) -> tuple[bytes | None, str]:
    item = next((i for i in manifest.values() if "cover-image" in i["props"]), None)
    if not item:
        cid = (_xp(opf, "//*[local-name()='metadata']/*[local-name()='meta'][@name='cover']/@content")
               or [""])[0]
        item = manifest.get(cid)
    if item and item["type"].startswith("image/"):
        try:
            return z.read(item["path"]), item["type"]
        except KeyError:
            pass
    return None, ""
