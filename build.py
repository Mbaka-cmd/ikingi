#!/usr/bin/env python3
"""Static site builder: JSON data + Jinja2 templates + static assets -> dist/."""
import json, re, shutil, sys
from datetime import date
from pathlib import Path
from urllib.parse import quote, quote_plus
from html import unescape
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
SRC, DIST = ROOT / "src", ROOT / "dist"
WA_MESSAGE = "Hello, I would like to enquire about admission at Rev. Ikingi Boarding Primary School."
warnings = []

def load(name):
    return json.loads((SRC / "data" / name).read_text(encoding="utf-8"))

def digits(number):
    d = re.sub(r"\D", "", number or "")
    if d.startswith("0"):
        d = "254" + d[1:]
    return d

def enrich_school(s):
    s = dict(s)
    d = digits(s.get("phone"))
    s["tel_href"] = f"tel:+{d}" if d else ""
    w = digits(s.get("whatsapp"))
    s["wa_href"] = f"https://wa.me/{w}?text={quote(WA_MESSAGE)}" if w else ""
    s["wa_base"] = f"https://wa.me/{w}" if w else ""
    s["maps_confirmed"] = bool(s.get("mapsUrl"))
    q = s.get("mapsQuery") or ""
    lat, lng = s.get("latitude"), s.get("longitude")
    if lat is not None and lng is not None:
        s["directionsUrl"] = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
        if not s.get("mapsUrl"):
            s["mapsUrl"] = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    elif q:
        s["directionsUrl"] = "https://www.google.com/maps/dir/?api=1&destination=" + quote_plus(q)
        if not s.get("mapsUrl"):
            s["mapsUrl"] = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(q)
    else:
        s["directionsUrl"] = ""
    s["site_url"] = (s.get("siteUrl") or "").rstrip("/")
    return s

def find_documents():
    """Map file stem -> public URL for every document that actually exists."""
    out = {}
    docs = SRC / "static" / "documents"
    for f in sorted(docs.glob("*")):
        if f.is_file() and f.name != ".gitkeep":
            out[f.stem] = f"/documents/{f.name}"
    return out

def find_images():
    """Map image folder -> list of public URLs for photos that actually exist."""
    out = {}
    root = SRC / "static" / "images"

    # Git does not preserve empty directories.
    # If no images have been added yet, return an empty image map.
    if not root.exists():
        return out

    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        files = sorted(
            f for f in d.iterdir()
            if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        )
        if files:
            out[d.name] = [
                f"/static/images/{d.name}/{f.name}"
                for f in files
            ]

    return out
    return out
def build_jsonld(s):
    """schema.org School data. Only confirmed facts are included."""
    d = {"@context": "https://schema.org", "@type": "School", "name": s["name"],
         "address": {"@type": "PostalAddress", "addressLocality": s["locality"],
                     "addressRegion": s["county"], "addressCountry": "KE"}}
    if s["site_url"]:
        d["url"] = s["site_url"] + "/"
    if s.get("phone"):
        d["telephone"] = "+" + digits(s["phone"])
    if s.get("email"):
        d["email"] = s["email"]
    if s.get("latitude") is not None and s.get("longitude") is not None:
        d["geo"] = {"@type": "GeoCoordinates", "latitude": s["latitude"], "longitude": s["longitude"]}
    if s.get("maps_confirmed") and s.get("mapsUrl"):
        d["hasMap"] = s["mapsUrl"]
    if s["site_url"] and s.get("logo"):
        d["logo"] = s["site_url"] + s["logo"]
    if s["site_url"] and s.get("ogImage"):
        d["image"] = s["site_url"] + s["ogImage"]
    links = [u for u in (s.get("social") or {}).values() if u]
    if links:
        d["sameAs"] = links
    return json.dumps(d, ensure_ascii=False).replace("</", "<\\/")

def seo_audit(pages, school):
    for p in pages:
        html = (DIST / p).read_text(encoding="utf-8")
        t = re.search(r"<title>(.*?)</title>", html, re.S)
        if not t or not t.group(1).strip():
            warnings.append(f"SEO {p}: missing <title>")
        d = re.search(r'<meta name="description" content="([^"]*)"', html)
        if not d:
            warnings.append(f"SEO {p}: missing meta description")
        else:
            n = len(unescape(d.group(1)))
            if n < 70 or n > 160:
                warnings.append(f"SEO {p}: meta description is {n} chars (aim for 70-160)")
        if len(re.findall(r"<h1[ >]", html)) != 1:
            warnings.append(f"SEO {p}: page should have exactly one <h1>")
        if re.findall(r"<img(?![^>]*\balt=)[^>]*>", html):
            warnings.append(f"SEO {p}: image without alt attribute")
        if school["site_url"] and 'rel="canonical"' not in html:
            warnings.append(f"SEO {p}: missing canonical")
        if "og:image" not in html:
            warnings.append("SEO: no og:image yet - set ogImage in school.json (1200x630 photo/logo) and siteUrl")
def url_for(filename):
    return "/" if filename == "index.html" else f"/{filename}"

def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    school = enrich_school(load("school.json"))
    if not school["site_url"]:
        warnings.append("school.json siteUrl is empty: canonical, og:url, sitemap.xml are skipped until the domain is set.")
    context = {
        "school": school,
        "admissions": load("admissions.json"),
        "fees": load("fees.json"),
        "gallery": load("gallery.json"),
        "news": load("news.json"),
        "nav": load("nav.json"),
        "docs": find_documents(),
        "images": find_images(),
        "home": load("home.json"),
        "about": load("about.json"),
        "academics": load("academics.json"),
        "boarding": load("boarding.json"),
        "facilities": load("facilities.json"),
        "student_life": load("student-life.json"),
        "year": date.today().year,
    }

    env = Environment(loader=FileSystemLoader(str(SRC)),
                      autoescape=select_autoescape(["html"]),
                      trim_blocks=True, lstrip_blocks=True)

    pages = sorted(p.name for p in (SRC / "pages").glob("*.html"))
    for name in pages:
        html = env.get_template(f"pages/{name}").render(
            page=name, page_url=url_for(name),
            jsonld=(build_jsonld(school) if name in ("index.html", "contact.html") else ""), **context)
        (DIST / name).write_text(html, encoding="utf-8")

    # static assets (documents live at /documents, not /static/documents)
    shutil.copytree(SRC / "static", DIST / "static",
                    ignore=shutil.ignore_patterns("documents", ".gitkeep"))
    docs_src = SRC / "static" / "documents"
    (DIST / "documents").mkdir()
    for f in docs_src.glob("*"):
        if f.is_file() and f.name != ".gitkeep":
            shutil.copy2(f, DIST / "documents" / f.name)
    if not any((DIST / "documents").iterdir()):
        (DIST / "documents").rmdir()

    # robots + sitemap
    base = school["site_url"]
    robots = ["User-agent: *", "Allow: /"]
    if base:
        robots.append(f"Sitemap: {base}/sitemap.xml")
        urls = [p for p in pages if p != "404.html"]
        today = date.today().isoformat()
        body = "\n".join(
            f"  <url><loc>{base}{url_for(p)}</loc><lastmod>{today}</lastmod></url>" for p in urls)
        (DIST / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "\n</urlset>\n",
            encoding="utf-8")
    (DIST / "robots.txt").write_text("\n".join(robots) + "\n", encoding="utf-8")

    (DIST / ".htaccess").write_text("ErrorDocument 404 /404.html\n", encoding="utf-8")
    check_links(pages)
    seo_audit(pages, school)
    print(f"Built {len(pages)} page(s) -> {DIST}")
    seen = set()
    for w in warnings:
        if w not in seen:
            seen.add(w)
            print("WARNING:", w)

def check_links(pages):
    ids = {}
    for p in pages:
        html = (DIST / p).read_text(encoding="utf-8")
        ids[p] = set(re.findall(r'\bid="([^"]+)"', html))
    for p in pages:
        html = (DIST / p).read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', html):
            if re.match(r"^(https?:|tel:|mailto:|#|javascript:)", href):
                if href.startswith("#") and len(href) > 1 and href[1:] not in ids[p]:
                    warnings.append(f"{p}: dead in-page anchor {href}")
                continue
            path, _, frag = href.partition("#")
            target = "index.html" if path in ("", "/") else path.lstrip("/")
            if target.startswith("static/") or target.startswith("documents/"):
                if not (DIST / target).exists():
                    warnings.append(f"{p}: missing file {href}")
                continue
            if target not in ids:
                warnings.append(f"{p}: link to page not built yet -> {href}")
            elif frag and frag not in ids[target]:
                warnings.append(f"{p}: dead anchor -> {href}")

if __name__ == "__main__":
    build()
    sys.exit(0)
