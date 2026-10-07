#!/usr/bin/env python3
"""Static site builder: JSON data + Jinja2 templates + static assets -> dist/."""

import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote, quote_plus
from html import unescape

from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).parent
SRC = ROOT / "src"
DIST = ROOT / "dist"

WA_MESSAGE = (
    "Hello, I would like to enquire about admission at "
    "Rev. Ikingi Boarding Primary School."
)

warnings = []


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

# Empty for Truehost/root-domain deployment.
# GitHub Pages project site uses /ikingi.
BASE_PATH = os.getenv("SITE_BASE_PATH", "").rstrip("/")


def site_path(path):
    """Return a deployment-aware site URL."""
    if not path.startswith("/"):
        path = "/" + path

    return f"{BASE_PATH}{path}" or "/"


# ---------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------

def load(name):
    return json.loads(
        (SRC / "data" / name).read_text(encoding="utf-8")
    )


def digits(number):
    """Convert a phone number to digits and normalize Kenyan 0-prefix."""
    d = re.sub(r"\D", "", number or "")

    if d.startswith("0"):
        d = "254" + d[1:]

    return d


def enrich_school(s):
    """Add derived contact/map fields without inventing school facts."""
    s = dict(s)

    # Phone
    d = digits(s.get("phone"))
    s["tel_href"] = f"tel:+{d}" if d else ""

    # WhatsApp
    w = digits(s.get("whatsapp"))
    s["wa_href"] = (
        f"https://wa.me/{w}?text={quote(WA_MESSAGE)}"
        if w
        else ""
    )
    s["wa_base"] = f"https://wa.me/{w}" if w else ""

    # Maps
    s["maps_confirmed"] = bool(s.get("mapsUrl"))

    q = s.get("mapsQuery") or ""
    lat = s.get("latitude")
    lng = s.get("longitude")

    if lat is not None and lng is not None:
        s["directionsUrl"] = (
            "https://www.google.com/maps/dir/"
            f"?api=1&destination={lat},{lng}"
        )

        if not s.get("mapsUrl"):
            s["mapsUrl"] = (
                "https://www.google.com/maps/search/"
                f"?api=1&query={lat},{lng}"
            )

    elif q:
        s["directionsUrl"] = (
            "https://www.google.com/maps/dir/"
            "?api=1&destination=" + quote_plus(q)
        )

        if not s.get("mapsUrl"):
            s["mapsUrl"] = (
                "https://www.google.com/maps/search/"
                "?api=1&query=" + quote_plus(q)
            )

    else:
        s["directionsUrl"] = ""

    # Confirmed production domain only.
    s["site_url"] = (s.get("siteUrl") or "").rstrip("/")

    return s


# ---------------------------------------------------------------------
# Asset discovery
# ---------------------------------------------------------------------

def find_documents():
    """Map document stem -> deployment-aware public URL."""
    out = {}

    docs = SRC / "static" / "documents"

    if not docs.exists():
        return out

    for f in sorted(docs.glob("*")):
        if f.is_file() and f.name != ".gitkeep":
            out[f.stem] = site_path(
                f"/documents/{f.name}"
            )

    return out


def find_images():
    """Map image folder -> deployment-aware URLs for real image files."""
    out = {}

    root = SRC / "static" / "images"

    # Git does not preserve empty directories.
    if not root.exists():
        return out

    for d in sorted(
        p for p in root.iterdir()
        if p.is_dir()
    ):
        files = sorted(
            f for f in d.iterdir()
            if f.suffix.lower()
            in (".jpg", ".jpeg", ".png", ".webp")
        )

        if files:
            out[d.name] = [
                site_path(
                    site_path(f"/static/images/{d.name}/{f.name}")
                )
                for f in files
            ]

    return out


# ---------------------------------------------------------------------
# Structured data
# ---------------------------------------------------------------------

def build_jsonld(s):
    """Build schema.org School data using confirmed facts only."""

    d = {
        "@context": "https://schema.org",
        "@type": "School",
        "name": s["name"],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": s["locality"],
            "addressRegion": s["county"],
            "addressCountry": "KE",
        },
    }

    if s["site_url"]:
        d["url"] = s["site_url"] + "/"

    if s.get("phone"):
        d["telephone"] = "+" + digits(s["phone"])

    if s.get("email"):
        d["email"] = s["email"]

    if (
        s.get("latitude") is not None
        and s.get("longitude") is not None
    ):
        d["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": s["latitude"],
            "longitude": s["longitude"],
        }

    if s.get("maps_confirmed") and s.get("mapsUrl"):
        d["hasMap"] = s["mapsUrl"]

    if s["site_url"] and s.get("logo"):
        d["logo"] = s["site_url"] + s["logo"]

    if s["site_url"] and s.get("ogImage"):
        d["image"] = s["site_url"] + s["ogImage"]

    links = [
        u
        for u in (s.get("social") or {}).values()
        if u
    ]

    if links:
        d["sameAs"] = links

    return json.dumps(
        d,
        ensure_ascii=False
    ).replace("</", "<\\/")


# ---------------------------------------------------------------------
# SEO audit
# ---------------------------------------------------------------------

def seo_audit(pages, school):
    for p in pages:
        html = (DIST / p).read_text(
            encoding="utf-8"
        )

        # Title
        t = re.search(
            r"<title>(.*?)</title>",
            html,
            re.S,
        )

        if not t or not t.group(1).strip():
            warnings.append(
                f"SEO {p}: missing <title>"
            )

        # Meta description
        d = re.search(
            r'<meta name="description" content="([^"]*)"',
            html,
        )

        if not d:
            warnings.append(
                f"SEO {p}: missing meta description"
            )
        else:
            n = len(
                unescape(d.group(1))
            )

            if n < 70 or n > 160:
                warnings.append(
                    f"SEO {p}: meta description is "
                    f"{n} chars (aim for 70-160)"
                )

        # H1
        if len(
            re.findall(r"<h1[ >]", html)
        ) != 1:
            warnings.append(
                f"SEO {p}: page should have exactly one <h1>"
            )

        # Image alt
        if re.findall(
            r"<img(?![^>]*\balt=)[^>]*>",
            html,
        ):
            warnings.append(
                f"SEO {p}: image without alt attribute"
            )

        # Canonical
        if (
            school["site_url"]
            and 'rel="canonical"' not in html
        ):
            warnings.append(
                f"SEO {p}: missing canonical"
            )

        # Open Graph image
        if "og:image" not in html:
            warnings.append(
                "SEO: no og:image yet - set ogImage "
                "in school.json (1200x630 photo/logo) "
                "and siteUrl"
            )


# ---------------------------------------------------------------------
# Page URLs
# ---------------------------------------------------------------------

def url_for(filename):
    """Return a deployment-aware URL for a generated page."""
    if filename == "index.html":
        return site_path("/")
    return site_path(f"/{filename}")
def build():
    if DIST.exists():
        shutil.rmtree(DIST)

    DIST.mkdir()

    school = enrich_school(
        load("school.json")
    )

    if not school["site_url"]:
        warnings.append(
            "school.json siteUrl is empty: "
            "canonical, og:url, sitemap.xml are skipped "
            "until the production domain is set."
        )

    context = {
        "school": school,

        # Used by templates.
        "base_path": BASE_PATH,
        "site_path": site_path,

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

    env = Environment(
        loader=FileSystemLoader(str(SRC)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    pages = sorted(
        p.name
        for p in (SRC / "pages").glob("*.html")
    )

    # Generate HTML pages.
    for name in pages:
        html = env.get_template(
            f"pages/{name}"
        ).render(
            page=name,
            page_url=url_for(name),
            jsonld=(
                build_jsonld(school)
                if name in ("index.html", "contact.html")
                else ""
            ),
            **context,
        )

        (DIST / name).write_text(
            html,
            encoding="utf-8",
        )

    # -------------------------------------------------------------
    # Static assets
    # -------------------------------------------------------------

    # Documents are moved to /documents rather than
    # /static/documents.
    shutil.copytree(
        SRC / "static",
        DIST / "static",
        ignore=shutil.ignore_patterns(
            "documents",
            ".gitkeep",
        ),
    )

    docs_src = SRC / "static" / "documents"

    (DIST / "documents").mkdir()

    if docs_src.exists():
        for f in docs_src.glob("*"):
            if (
                f.is_file()
                and f.name != ".gitkeep"
            ):
                shutil.copy2(
                    f,
                    DIST / "documents" / f.name,
                )

    if not any(
        (DIST / "documents").iterdir()
    ):
        (DIST / "documents").rmdir()

    # -------------------------------------------------------------
    # robots.txt + sitemap.xml
    # -------------------------------------------------------------

    base = school["site_url"]

    robots = [
        "User-agent: *",
        "Allow: /",
    ]

    if base:
        robots.append(
            f"Sitemap: {base}/sitemap.xml"
        )

        urls = [
            p
            for p in pages
            if p != "404.html"
        ]

        today = date.today().isoformat()

        body = "\n".join(
            (
                "  <url>"
                f"<loc>{base}{url_for(p)}</loc>"
                f"<lastmod>{today}</lastmod>"
                "</url>"
            )
            for p in urls
        )

        (DIST / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + body
            + "\n</urlset>\n",
            encoding="utf-8",
        )

    (DIST / "robots.txt").write_text(
        "\n".join(robots) + "\n",
        encoding="utf-8",
    )

    # Truehost/Apache 404 handling.
    # GitHub Pages ignores this file.
    (DIST / ".htaccess").write_text(
        "ErrorDocument 404 /404.html\n",
        encoding="utf-8",
    )

    # Validate generated links.
    check_links(pages)

    # SEO checks.
    seo_audit(pages, school)

    print(
        f"Built {len(pages)} page(s) -> {DIST}"
    )

    seen = set()

    for w in warnings:
        if w not in seen:
            seen.add(w)
            print("WARNING:", w)


# ---------------------------------------------------------------------
# Link checker
# ---------------------------------------------------------------------

def check_links(pages):
    """Validate generated internal links against dist/."""

    ids = {}

    # Collect anchors for every page.
    for p in pages:
        html = (DIST / p).read_text(
            encoding="utf-8"
        )

        ids[p] = set(
            re.findall(
                r'\bid="([^"]+)"',
                html,
            )
        )

    # Check links.
    for p in pages:
        html = (DIST / p).read_text(
            encoding="utf-8"
        )

        for href in re.findall(
            r'href="([^"]+)"',
            html,
        ):

            # External/special URLs.
            if re.match(
                r"^(https?:|tel:|mailto:|#|javascript:)",
                href,
            ):
                if (
                    href.startswith("#")
                    and len(href) > 1
                    and href[1:] not in ids[p]
                ):
                    warnings.append(
                        f"{p}: dead in-page anchor {href}"
                    )

                continue

            path, _, frag = href.partition("#")

            # IMPORTANT:
            # GitHub Pages project sites have /ikingi
            # in front of every internal path.
            #
            # Strip that deployment prefix before checking
            # the actual file inside dist/.
            if BASE_PATH and (
                path == BASE_PATH
                or path.startswith(BASE_PATH + "/")
            ):
                path = path[len(BASE_PATH):] or "/"

            target = (
                "index.html"
                if path in ("", "/")
                else path.lstrip("/")
            )

            # Static files.
            if (
                target.startswith("static/")
                or target.startswith("documents/")
            ):
                if not (DIST / target).exists():
                    warnings.append(
                        f"{p}: missing file {href}"
                    )

                continue

            # HTML pages.
            if target not in ids:
                warnings.append(
                    f"{p}: link to page not built yet -> {href}"
                )

            elif (
                frag
                and frag not in ids[target]
            ):
                warnings.append(
                    f"{p}: dead anchor -> {href}"
                )


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    build()
    sys.exit(0)
