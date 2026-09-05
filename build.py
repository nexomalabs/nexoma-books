#!/usr/bin/env python3
"""Build books.nexomalabs.com from content/*.json + templates/ + static/.

Standard library only. Run:  python3 build.py  [--out _site]  [--serve]

Every page is emitted as <path>/index.html so that public URLs end in a slash,
which is what is printed in the books.
"""

import argparse
import datetime
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
TEMPLATES = os.path.join(ROOT, "templates")
STATIC = os.path.join(ROOT, "static")

YEAR = datetime.date.today().year
TODAY = datetime.date.today().isoformat()

_pages = []  # (url_path, changefreq, priority) for the sitemap


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def e(text):
    """Escape a value for HTML text/attribute context."""
    return html.escape(str(text), quote=True)


def read_json(name):
    with open(os.path.join(CONTENT, name), encoding="utf-8") as fh:
        return json.load(fh)


def read_template(name):
    with open(os.path.join(TEMPLATES, name), encoding="utf-8") as fh:
        return fh.read()


def paragraphs(items, cls="muted"):
    return "\n".join('<p class="%s">%s</p>' % (cls, e(p)) for p in items)


def write_page(out, url_path, html_text, changefreq="monthly", priority="0.6",
               in_sitemap=True):
    """Write html_text to <out>/<url_path>/index.html (or a bare file path)."""
    rel = url_path.strip("/")
    if rel.endswith(".html") or rel.endswith(".xml") or rel.endswith(".txt"):
        dest = os.path.join(out, rel)
    else:
        dest = os.path.join(out, rel, "index.html") if rel else os.path.join(out, "index.html")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(html_text)
    if in_sitemap:
        _pages.append(("/" + rel + "/" if rel and not os.path.splitext(rel)[1] else "/" + rel,
                       changefreq, priority))
    return dest


# --------------------------------------------------------------------------
# shell
# --------------------------------------------------------------------------

def render_shell(base, site, *, title, description, path, content,
                 og_image=None, robots="index,follow", og_type="website",
                 head_extra=""):
    canonical = site["base_url"].rstrip("/") + path
    image = og_image or (site["base_url"].rstrip("/") + "/img/og-default.png")
    out = base
    for key, value in (
        ("{{title}}", e(title)),
        ("{{description}}", e(description)),
        ("{{canonical}}", e(canonical)),
        ("{{og_image}}", e(image)),
        ("{{og_type}}", e(og_type)),
        ("{{robots}}", e(robots)),
        ("{{year}}", str(YEAR)),
        ("{{head_extra}}", head_extra),
        ("{{content}}", content),
    ):
        out = out.replace(key, value)
    return out


def crumbs(items):
    """items: list of (label, href or None)."""
    parts = []
    for label, href in items:
        if href:
            parts.append('<a href="%s">%s</a>' % (e(href), e(label)))
        else:
            parts.append('<span aria-current="page">%s</span>' % e(label))
    return ('<div class="wrap"><nav class="crumbs" aria-label="Breadcrumb">'
            + '<span aria-hidden="true">/</span>'.join(parts)
            + "</nav></div>")


def jsonld(payload):
    return ('<script type="application/ld+json">%s</script>'
            % json.dumps(payload, indent=2, ensure_ascii=False))


# --------------------------------------------------------------------------
# reusable fragments
# --------------------------------------------------------------------------

def status_badge(vol):
    return '<span class="badge badge-%s">%s</span>' % (
        e(vol["status"]), e(vol["status_label"]))


def cover_block(vol, series_slug):
    if vol.get("cover"):
        return ('<div class="cover-frame"><img src="%s" alt="Front cover of %s, Volume %s: %s" '
                'loading="lazy" /></div>'
                % (e(vol["cover"]), e("Applied AI Engineering"), e(vol["roman"]), e(vol["title"])))
    return ('<div class="cover-placeholder" role="img" aria-label="Cover art for Volume %s, %s, is in design">'
            '<div>'
            '<span class="cp-label">Volume %s</span>'
            '<span class="cp-title">%s</span>'
            '<span class="cp-rule" aria-hidden="true"></span>'
            '<span class="cp-note">Cover in design</span>'
            '</div></div>'
            % (e(vol["roman"]), e(vol["title"]), e(vol["roman"]), e(vol["title"])))


def volume_card(series, vol):
    href = "/%s/%s/" % (series["slug"], vol["slug"])
    return """<a class="vol-card" href="{href}">
  <span class="vol-num">Volume {roman}</span>
  <h3>{title}</h3>
  <p class="vol-sub">{subtitle}</p>
  <div class="vol-foot">
    <span>{chapters} chapters</span>
    {badge}
  </div>
</a>""".format(href=e(href), roman=e(vol["roman"]), title=e(vol["title"]),
                subtitle=e(vol["subtitle"]), chapters=e(vol["chapter_count"]),
                badge=status_badge(vol))


def buy_actions(vol, site):
    """Buy buttons when links exist; an honest 'not yet on sale' notice otherwise."""
    links = vol.get("buy_links") or []
    if links:
        return "".join('<a class="btn btn-primary" href="%s" rel="noreferrer">%s</a>'
                       % (e(l["url"]), e(l["label"])) for l in links)
    return ('<span class="btn btn-primary" aria-disabled="true">Not yet on sale</span>'
            '<a class="btn btn-secondary" href="/contact/">Get release updates</a>')


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------

def page_home(site, series_list):
    series = series_list[0]
    cards = "\n".join(volume_card(series, v) for v in series["volumes"])
    total_chapters = sum(v["chapter_count"] for v in series["volumes"])

    content = """
<section class="hero wrap">
  <div class="hero-split">
    <div>
      <p class="eyebrow">Nexoma Labs LLC &middot; Publishing</p>
      <h1>Engineering books,<br />written by engineers.</h1>
      <p class="lead">{tagline} Practitioner titles that treat AI work as an engineering
      discipline &mdash; specified, tested, reviewed, and operated, not improvised.</p>
      <div class="actions">
        <a class="btn btn-primary" href="/{slug}/">Explore the series</a>
        <a class="btn btn-secondary" href="/{slug}/errata/">Errata</a>
      </div>
    </div>
    <div>
      <div class="stats">
        <div class="stat"><span class="n">1</span><span class="l">Series</span></div>
        <div class="stat"><span class="n">4</span><span class="l">Volumes</span></div>
        <div class="stat"><span class="n">{chapters}</span><span class="l">Chapters</span></div>
      </div>
    </div>
  </div>
</section>

<section class="section section-line">
  <div class="wrap">
    <h2 class="section-title">{series_title}</h2>
    <p class="section-sub">{short}</p>
    <div class="grid grid-4">
{cards}
    </div>
    <div class="actions">
      <a class="btn btn-secondary" href="/{slug}/">Series overview &rarr;</a>
    </div>
  </div>
</section>

<section class="section section-line">
  <div class="wrap">
    <h2 class="section-title">For readers</h2>
    <p class="section-sub">Everything printed in the back of the books lives here.</p>
    <div class="grid grid-3">
      <div class="card">
        <h3>Errata</h3>
        <p class="muted small">Confirmed corrections, listed per volume and per printing,
        with the date each one was folded into the source.</p>
        <a class="btn btn-secondary btn-sm" href="/{slug}/errata/">View errata</a>
      </div>
      <div class="card">
        <h3>Companion code</h3>
        <p class="muted small">Every laboratory in the books runs from a clean checkout of
        the companion repository, and is tested in CI.</p>
        <a class="btn btn-secondary btn-sm" href="/{slug}/companion/">Companion code</a>
      </div>
      <div class="card">
        <h3>Instructor resources</h3>
        <p class="muted small">Slide decks, syllabi, teaching notes, question banks, and
        assessment keys &mdash; free to verified instructors.</p>
        <a class="btn btn-secondary btn-sm" href="/{slug}/instructors/">Request access</a>
      </div>
    </div>
  </div>
</section>
""".format(tagline=e(site["tagline"]) + ".", slug=e(series["slug"]),
           chapters=total_chapters, series_title=e(series["title"]),
           short=e(series["short_description"]), cards=cards)

    ld = jsonld({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": site["publisher"],
        "url": site["base_url"],
        "sameAs": [site["parent_site"], site["github_org"], site["youtube"]],
    })
    return content, ld


def page_series(site, series):
    cards = "\n".join(volume_card(series, v) for v in series["volumes"])
    prog = "\n".join(
        '<div class="prog-row"><span class="pv">{v}</span>'
        '<span class="pverb">{verb}</span>'
        '<span class="pline">{line}</span></div>'.format(
            v=e(p["volume"]), verb=e(p["verb"]), line=e(p["line"]))
        for p in series["progression"])
    boards = "\n".join(
        '<tr><th>{name}</th><td><em>{q}</em></td></tr>'.format(
            name=e(b["name"]), q=e(b["question"]))
        for b in series["methodology"]["boards"])
    total_chapters = sum(v["chapter_count"] for v in series["volumes"])

    content = crumbs([("Books", "/"), (series["title"], None)]) + """
<section class="hero wrap">
  <p class="eyebrow">Series</p>
  <h1>{title}</h1>
  <p class="lead"><strong>{tagline}</strong> &mdash; a four-volume practitioner series by
  {author}, published by Nexoma Labs LLC.</p>
  <div class="actions">
    <a class="btn btn-primary" href="/{slug}/volume-1/">Start with Volume I</a>
    <a class="btn btn-secondary" href="/{slug}/errata/">Errata</a>
    <a class="btn btn-secondary" href="/{slug}/companion/">Companion code</a>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="stats">
      <div class="stat"><span class="n">4</span><span class="l">Standalone volumes</span></div>
      <div class="stat"><span class="n">{chapters}</span><span class="l">Chapters</span></div>
      <div class="stat"><span class="n">{edition}</span><span class="l">Edition</span></div>
      <div class="stat"><span class="n">EN</span><span class="l">Language</span></div>
    </div>
  </div>
</section>

<section class="section section-line">
  <div class="wrap">
    <h2 class="section-title">Why this series exists</h2>
    <div style="max-width:70ch">{desc}</div>
  </div>
</section>

<section class="section section-line">
  <div class="wrap">
    <h2 class="section-title">The four volumes</h2>
    <p class="section-sub">Each volume is a standalone book with its own ISBN, glossary,
    index, labs, and companion resources. Chapter numbering restarts at 1 in every volume.</p>
    <div class="grid grid-4">
{cards}
    </div>
  </div>
</section>

<section class="section section-line">
  <div class="wrap">
    <h2 class="section-title">Competency progression</h2>
    <p class="section-sub">Each volume assumes mastery of the one before it, while staying
    self-contained through explicit cross-references and a prerequisites appendix.</p>
    <div class="progression">
{prog}
    </div>
  </div>
</section>

<section class="section section-line">
  <div class="wrap">
    <div class="hero-split">
      <div>
        <h2 class="section-title">Signature methodology: {method}</h2>
        <p class="muted">{msummary}</p>
        <div class="callout">
          <p class="callout-title">Governing rule</p>
          <p class="muted small">{mrule}</p>
        </div>
      </div>
      <div class="card">
        <h3>Two boards, two questions</h3>
        <table class="meta-table">
{boards}
        </table>
      </div>
    </div>
  </div>
</section>

<section class="section section-line">
  <div class="wrap">
    <h2 class="section-title">Who it is for</h2>
    <div class="grid grid-3">
      <div class="card"><h3>Primary audience</h3><p class="muted small">{a_primary}</p></div>
      <div class="card"><h3>Also for</h3><p class="muted small">{a_secondary}</p></div>
      <div class="card"><h3>Not for</h3><p class="muted small">{a_not}</p></div>
    </div>
  </div>
</section>
""".format(title=e(series["title"]), tagline=e(series["tagline"]),
           author=e(series["author"]), slug=e(series["slug"]),
           chapters=total_chapters, edition="1st",
           desc=paragraphs(series["description"]), cards=cards, prog=prog,
           method=e(series["methodology"]["name"]),
           msummary=e(series["methodology"]["summary"]),
           mrule=e(series["methodology"]["rule"]), boards=boards,
           a_primary=e(series["audience"]["primary"]),
           a_secondary=e(series["audience"]["secondary"]),
           a_not=e(series["audience"]["not"]))

    ld = jsonld({
        "@context": "https://schema.org",
        "@type": "BookSeries",
        "name": series["title"],
        "alternativeHeadline": series["tagline"],
        "description": series["short_description"],
        "author": {"@type": "Person", "name": series["author"]},
        "publisher": {"@type": "Organization", "name": site["publisher"]},
        "numberOfItems": len(series["volumes"]),
        "url": "%s/%s/" % (site["base_url"].rstrip("/"), series["slug"]),
    })
    return content, ld


def page_volume(site, series, vol, errata_for_volume):
    chapters = "\n".join("<li>%s</li>" % e(c) for c in vol["chapters"])
    outcomes = ""
    if vol.get("outcomes"):
        outcomes = """
<section class="section section-line">
  <div class="wrap">
    <h2 class="section-title">What you will be able to do</h2>
    <ul class="check" style="max-width:70ch">
{items}
    </ul>
  </div>
</section>""".format(items="\n".join("<li>%s</li>" % e(o) for o in vol["outcomes"]))

    rows = [
        ("Series", "%s, Volume %s" % (series["title"], vol["roman"])),
        ("Author", series["author"]),
        ("Publisher", site["publisher"]),
        ("Edition", series["edition"]),
        ("Chapters", str(vol["chapter_count"])),
        ("Difficulty", vol["difficulty"]),
        ("Formats", ", ".join(vol["formats"])),
        ("Status", vol["status_label"]),
    ]
    if vol.get("lab_count"):
        rows.insert(5, ("Laboratories", str(vol["lab_count"])))
    if vol.get("isbn_print"):
        rows.append(("ISBN (print)", vol["isbn_print"]))
    if vol.get("isbn_epub"):
        rows.append(("ISBN (EPUB)", vol["isbn_epub"]))
    meta_rows = "\n".join("<tr><th>%s</th><td>%s</td></tr>" % (e(k), e(v)) for k, v in rows)

    n_errata = len(errata_for_volume.get("entries", []))
    errata_line = ("No errata reported." if n_errata == 0
                   else "%d correction%s listed." % (n_errata, "" if n_errata == 1 else "s"))

    content = crumbs([("Books", "/"), (series["title"], "/%s/" % series["slug"]),
                      ("Volume %s" % vol["roman"], None)]) + """
<section class="hero wrap">
  <div class="hero-split">
    <div>
      <p class="eyebrow">{series_title} &middot; Volume {roman}</p>
      <h1>{title}</h1>
      <p class="lead">{subtitle}</p>
      <p style="margin-top:1rem">{badge} <span class="muted small">{status_note}</span></p>
      <div class="actions">{buy}</div>
    </div>
    <div>{cover}</div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="hero-split">
      <div>
        <h2 class="section-title">About this volume</h2>
        {blurb}
        <div class="callout">
          <p class="callout-title">Mission</p>
          <p class="muted small">{mission}</p>
        </div>
        <p class="muted small"><strong>Prerequisites.</strong> {prereq}</p>
      </div>
      <div class="card">
        <h3>Details</h3>
        <table class="meta-table">
{meta_rows}
        </table>
      </div>
    </div>
  </div>
</section>
{outcomes}
<section class="section section-line">
  <div class="wrap">
    <h2 class="section-title">Contents</h2>
    <p class="section-sub">{nchapters} chapters. Chapter numbering restarts at 1 in every
    volume; cross-volume references are written as <em>Volume III, Chapter 4</em>.</p>
    <ol class="chapters" style="max-width:70ch">
{chapters}
    </ol>
  </div>
</section>

<section class="section section-line">
  <div class="wrap">
    <div class="grid grid-3">
      <div class="card">
        <h3>Errata</h3>
        <p class="muted small">{errata_line}</p>
        <a class="btn btn-secondary btn-sm" href="/{slug}/errata/{vslug}/">Volume {roman} errata</a>
      </div>
      <div class="card">
        <h3>Companion code</h3>
        <p class="muted small">Every laboratory runs from a clean checkout and is tested in CI.</p>
        <a class="btn btn-secondary btn-sm" href="/{slug}/companion/">Companion code</a>
      </div>
      <div class="card">
        <h3>Teaching this volume?</h3>
        <p class="muted small">Slides, syllabi, teaching notes, and assessment keys are free
        to verified instructors.</p>
        <a class="btn btn-secondary btn-sm" href="/{slug}/instructors/">Instructor resources</a>
      </div>
    </div>
  </div>
</section>
""".format(series_title=e(series["title"]), roman=e(vol["roman"]), title=e(vol["title"]),
           subtitle=e(vol["subtitle"]), badge=status_badge(vol),
           status_note=e(vol["status_note"]), buy=buy_actions(vol, site),
           cover=cover_block(vol, series["slug"]), blurb=paragraphs(vol["blurb"]),
           mission=e(vol["mission"]), prereq=e(vol["prerequisites"]),
           meta_rows=meta_rows, outcomes=outcomes, nchapters=vol["chapter_count"],
           chapters=chapters, errata_line=e(errata_line), slug=e(series["slug"]),
           vslug=e(vol["slug"]))

    book_ld = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": "%s: %s" % (series["title"], vol["title"]),
        "alternativeHeadline": vol["subtitle"],
        "bookEdition": series["edition"],
        "numberOfPages": None,
        "inLanguage": "en-US",
        "author": {"@type": "Person", "name": series["author"]},
        "publisher": {"@type": "Organization", "name": site["publisher"]},
        "isPartOf": {"@type": "BookSeries", "name": series["title"]},
        "position": vol["number"],
        "description": vol["mission"],
        "url": "%s/%s/%s/" % (site["base_url"].rstrip("/"), series["slug"], vol["slug"]),
    }
    if vol.get("isbn_print"):
        book_ld["isbn"] = vol["isbn_print"]
    book_ld = {k: v for k, v in book_ld.items() if v is not None}
    return content, jsonld(book_ld)


def erratum_html(item):
    def field(label, value, cls=""):
        if not value:
            return ""
        return ('<div><dt>%s</dt><dd class="%s">%s</dd></div>'
                % (e(label), cls, e(value)))

    tail = []
    if item.get("printings"):
        tail.append("Affects: %s" % item["printings"])
    if item.get("reported"):
        tail.append("Reported %s" % item["reported"])
    if item.get("corrected"):
        tail.append("Corrected in source %s" % item["corrected"])

    return """<div class="erratum">
  <div class="erratum-head">
    <span class="erratum-id">{eid}</span>
    <span class="erratum-loc">{loc}</span>
    <span class="badge">{sev}</span>
  </div>
  <dl>
    {incorrect}
    {correct}
    {note}
  </dl>
  <p class="muted small" style="margin:.75rem 0 0">{tail}</p>
</div>""".format(eid=e(item.get("id", "")), loc=e(item.get("location", "")),
                 sev=e(item.get("severity", "correction")),
                 incorrect=field("Printed", item.get("incorrect"), "was"),
                 correct=field("Should read", item.get("correct"), "now"),
                 note=field("Note", item.get("note")),
                 tail=e(" \u00b7 ".join(tail)))


def page_errata_index(site, series, errata, by_volume):
    policy = "\n".join("<li>%s</li>" % e(p) for p in errata["policy"])
    rows = []
    for vol in series["volumes"]:
        entries = by_volume.get(vol["slug"], {}).get("entries", [])
        n = len(entries)
        rows.append("""<a class="vol-card" href="/{slug}/errata/{vslug}/">
  <span class="vol-num">Volume {roman}</span>
  <h3>{title}</h3>
  <p class="vol-sub">{subtitle}</p>
  <div class="vol-foot">
    <span>{count}</span>
    <span class="badge {cls}">{label}</span>
  </div>
</a>""".format(slug=e(series["slug"]), vslug=e(vol["slug"]), roman=e(vol["roman"]),
                title=e(vol["title"]), subtitle=e(vol["subtitle"]),
                count=("No errata reported" if n == 0
                       else "%d correction%s" % (n, "" if n == 1 else "s")),
                cls="badge-available" if n == 0 else "badge-in-production",
                label="Clean" if n == 0 else "Corrections"))

    content = crumbs([("Books", "/"), (series["title"], "/%s/" % series["slug"]),
                      ("Errata", None)]) + """
<section class="hero wrap">
  <p class="eyebrow">{series_title}</p>
  <h1>Errata</h1>
  <p class="lead">Confirmed corrections to the published text, listed by volume. This page
  is the authoritative record referenced in the back of every book in the series.</p>
</section>

<section class="section">
  <div class="wrap">
    <div class="grid grid-4">
{rows}
    </div>
    <p class="muted small" style="margin-top:1.25rem">Last reviewed {reviewed}.</p>
  </div>
</section>

<section class="section section-line">
  <div class="wrap">
    <div class="hero-split">
      <div>
        <h2 class="section-title">How errata are handled</h2>
        <ul class="check" style="max-width:66ch">
{policy}
        </ul>
      </div>
      <div class="card">
        <h3>Report an error</h3>
        <p class="muted small">Email <a href="mailto:{errata_email}">{errata_email}</a> with
        the volume, printing, page number, and the text as printed. A photograph or a copied
        line is ideal.</p>
        <p class="muted small">Errors in the companion lab code are tracked as issues in the
        <a href="{repo}" rel="noreferrer">companion repository</a> rather than on this page.</p>
        <a class="btn btn-secondary btn-sm" href="mailto:{errata_email}?subject=Errata%20report">Email an errata report</a>
      </div>
    </div>
  </div>
</section>
""".format(series_title=e(series["title"]), rows="\n".join(rows),
           reviewed=e(errata.get("last_reviewed", TODAY)), policy=policy,
           errata_email=e(site["errata_email"]), repo=e(series["companion_repo"]))
    return content, ""


def page_errata_volume(site, series, vol, record):
    entries = record.get("entries", [])
    if entries:
        body = "\n".join(erratum_html(item) for item in entries)
        summary = "%d confirmed correction%s." % (len(entries), "" if len(entries) == 1 else "s")
    else:
        body = """<div class="errata-empty">
  <p><strong>No errata reported.</strong></p>
  <p class="small">No errors have been confirmed in this volume. If you have found one,
  please <a href="mailto:{email}?subject=Errata%20%E2%80%94%20Volume%20{roman}">report it</a>
  &mdash; it will be verified against the manuscript source and listed here.</p>
</div>""".format(email=e(site["errata_email"]), roman=e(vol["roman"]))
        summary = "No errata reported."

    content = crumbs([("Books", "/"), (series["title"], "/%s/" % series["slug"]),
                      ("Errata", "/%s/errata/" % series["slug"]),
                      ("Volume %s" % vol["roman"], None)]) + """
<section class="hero wrap">
  <p class="eyebrow">{series_title} &middot; Volume {roman}</p>
  <h1>Errata &mdash; {title}</h1>
  <p class="lead">{subtitle}</p>
  <p class="muted small">{summary} Last reviewed {reviewed}.</p>
</section>

<section class="section">
  <div class="narrow" style="width:min(880px,calc(100% - 2.5rem))">
{body}
  </div>
</section>

<section class="section section-line">
  <div class="wrap">
    <div class="grid grid-3">
      <div class="card">
        <h3>Report an error</h3>
        <p class="muted small">Include the volume, printing, page number, and the text as
        printed.</p>
        <a class="btn btn-secondary btn-sm" href="mailto:{email}?subject=Errata%20%E2%80%94%20Volume%20{roman}">Email {email}</a>
      </div>
      <div class="card">
        <h3>All volumes</h3>
        <p class="muted small">Errata for the rest of the series.</p>
        <a class="btn btn-secondary btn-sm" href="/{slug}/errata/">Errata index</a>
      </div>
      <div class="card">
        <h3>This volume</h3>
        <p class="muted small">Contents, prerequisites, and formats.</p>
        <a class="btn btn-secondary btn-sm" href="/{slug}/{vslug}/">Volume {roman}</a>
      </div>
    </div>
  </div>
</section>
""".format(series_title=e(series["title"]), roman=e(vol["roman"]), title=e(vol["title"]),
           subtitle=e(vol["subtitle"]), summary=e(summary),
           reviewed=e(record.get("last_reviewed", TODAY)), body=body,
           email=e(site["errata_email"]), slug=e(series["slug"]), vslug=e(vol["slug"]))
    return content, ""


def page_companion(site, series):
    content = crumbs([("Books", "/"), (series["title"], "/%s/" % series["slug"]),
                      ("Companion code", None)]) + """
<section class="hero wrap">
  <p class="eyebrow">{series_title}</p>
  <h1>Companion code</h1>
  <p class="lead">Every laboratory in the series ships as runnable code. Each lab runs from
  a clean checkout, pins its dependencies, and is tested in continuous integration.</p>
  <div class="actions">
    <a class="btn btn-primary" href="{repo}" rel="noreferrer">Open the repository</a>
    <a class="btn btn-secondary" href="{org}" rel="noreferrer">All Nexoma repositories</a>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="grid grid-3">
      <div class="card">
        <h3>What is in it</h3>
        <ul class="check">
          <li>One directory per chapter, per volume</li>
          <li>Datasets and shared fixtures</li>
          <li>Reference solutions</li>
          <li>A test suite per lab</li>
        </ul>
      </div>
      <div class="card">
        <h3>Requirements</h3>
        <p class="muted small">Python 3.12. Dependencies are pinned per lab. Labs that call a
        hosted model read the API key from the environment and never from a checked-in file.</p>
      </div>
      <div class="card">
        <h3>Licence</h3>
        <p class="muted small">Companion lab code is licensed under the MIT License. The
        manuscript itself is all rights reserved, &copy; {year} Nexoma Labs LLC.</p>
      </div>
    </div>

    <h2 class="section-title" style="margin-top:2.5rem">Get started</h2>
    <pre><code>git clone {repo}.git
cd {repo_name}
python3 -m venv .venv &amp;&amp; source .venv/bin/activate
pip install -r requirements.txt
pytest</code></pre>
    <p class="muted small">Found a problem in the code? Open an issue in the repository.
    Problems in the printed text go to <a href="/{slug}/errata/">errata</a> instead.</p>
  </div>
</section>
""".format(series_title=e(series["title"]), repo=e(series["companion_repo"]),
           repo_name=e(series["companion_repo"].rstrip("/").rsplit("/", 1)[-1]),
           org=e(site["github_org"]), year=YEAR, slug=e(series["slug"]))
    return content, ""


def page_instructors(site, series):
    content = crumbs([("Books", "/"), (series["title"], "/%s/" % series["slug"]),
                      ("Instructors", None)]) + """
<section class="hero wrap">
  <p class="eyebrow">{series_title}</p>
  <h1>Instructor resources</h1>
  <p class="lead">Slide decks, syllabi, teaching notes, question banks, and assessment keys
  are available <strong>free to verified instructors</strong>.</p>
</section>

<section class="section">
  <div class="wrap">
    <div class="hero-split">
      <div>
        <h2 class="section-title">How to request access</h2>
        <p class="muted">Email <a href="mailto:{email}">{email}</a> <strong>from your
        institutional address</strong> and tell us:</p>
        <ul class="check" style="max-width:60ch">
          <li>Your institution and department</li>
          <li>The course the book will be used in</li>
          <li>Expected enrolment</li>
          <li>Term and start date</li>
        </ul>
        <p class="muted small">Requests from personal email addresses cannot be verified and
        will not be fulfilled. Assessment keys are distributed only after verification, and
        are not to be posted to a public course site or a shared drive.</p>
        <div class="actions">
          <a class="btn btn-primary" href="mailto:{email}?subject=Instructor%20resource%20request">Request instructor access</a>
        </div>
      </div>
      <div class="card">
        <h3>What the package contains</h3>
        <table class="meta-table">
          <tr><th>Syllabi</th><td>Semester, quarter, and intensive formats</td></tr>
          <tr><th>Slides</th><td>One deck per chapter, PDF and PPTX</td></tr>
          <tr><th>Teaching notes</th><td>Per chapter, with timing and discussion prompts</td></tr>
          <tr><th>Assessments</th><td>Quizzes, midterm, final, and a practical brief</td></tr>
          <tr><th>Keys</th><td>Separate answer keys and rubrics</td></tr>
          <tr><th>Question bank</th><td>Bloom-tagged, for building your own exams</td></tr>
        </table>
        <p class="muted small" style="margin-top:1rem">Packaged per volume. Volume I is
        available now; later volumes ship with each release.</p>
      </div>
    </div>
  </div>
</section>

<section class="section section-line">
  <div class="wrap">
    <div class="callout">
      <p class="callout-title">Adopting the series for a course?</p>
      <p class="muted small">Tell us your enrolment when you write &mdash; we can advise on
      volume sequencing, which chapters map to a one-term course, and how the laboratories
      fit an assessed practical component.</p>
    </div>
  </div>
</section>
""".format(series_title=e(series["title"]), email=e(site["instructor_email"]))
    return content, ""


def page_contact(site):
    content = crumbs([("Books", "/"), ("Contact", None)]) + """
<section class="hero wrap">
  <p class="eyebrow">Nexoma Labs LLC</p>
  <h1>Contact</h1>
  <p class="lead">Reach the right address and you will get a faster answer.</p>
</section>

<section class="section">
  <div class="wrap">
    <div class="grid grid-2">
      <div class="card">
        <h3>General enquiries</h3>
        <p class="muted small">Questions about the books, availability, and formats.</p>
        <a class="btn btn-secondary btn-sm" href="mailto:{contact}">{contact}</a>
      </div>
      <div class="card">
        <h3>Errata</h3>
        <p class="muted small">Errors in the printed or digital text. Include the volume,
        printing, and page number.</p>
        <a class="btn btn-secondary btn-sm" href="mailto:{errata}">{errata}</a>
      </div>
      <div class="card">
        <h3>Instructors</h3>
        <p class="muted small">Teaching resources and course adoption. Write from your
        institutional address.</p>
        <a class="btn btn-secondary btn-sm" href="mailto:{instructor}">{instructor}</a>
      </div>
      <div class="card">
        <h3>Rights, permissions, and press</h3>
        <p class="muted small">Translation rights, bulk orders, licensing, and review copies.</p>
        <a class="btn btn-secondary btn-sm" href="mailto:{publishing}">{publishing}</a>
      </div>
    </div>

    <h2 class="section-title" style="margin-top:2.5rem">Elsewhere</h2>
    <ul class="check">
      <li><a href="{parent}" rel="noreferrer">{parent_label}</a> &mdash; the company site</li>
      <li><a href="{github}" rel="noreferrer">GitHub</a> &mdash; companion code and open-source tools</li>
      <li><a href="{youtube}" rel="noreferrer">YouTube</a> &mdash; talks and walkthroughs</li>
    </ul>
  </div>
</section>
""".format(contact=e(site["contact_email"]), errata=e(site["errata_email"]),
           instructor=e(site["instructor_email"]), publishing=e(site["publishing_email"]),
           parent=e(site["parent_site"]),
           parent_label=e(site["parent_site"].replace("https://", "")),
           github=e(site["github_org"]), youtube=e(site["youtube"]))
    return content, ""


def page_404(site, series):
    content = """
<section class="hero wrap center" style="padding-top:5rem">
  <p class="eyebrow">404</p>
  <h1>That page is not here.</h1>
  <p class="lead" style="margin:0 auto">The link may be out of date, or the page may have
  moved. Everything printed in the books lives under the links below.</p>
  <div class="actions" style="justify-content:center">
    <a class="btn btn-primary" href="/{slug}/">Series overview</a>
    <a class="btn btn-secondary" href="/{slug}/errata/">Errata</a>
    <a class="btn btn-secondary" href="/">All books</a>
  </div>
</section>
""".format(slug=e(series["slug"]))
    return content, ""


def redirect_page(site, target, title):
    """A meta-refresh + canonical redirect stub for legacy printed URLs."""
    url = target if target.startswith("http") else site["base_url"].rstrip("/") + target
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<link rel="canonical" href="{url}" />
<meta name="robots" content="noindex,follow" />
<meta http-equiv="refresh" content="0; url={target}" />
<script>location.replace("{target}");</script>
<style>body{{font-family:system-ui,sans-serif;background:#050816;color:#fff;display:grid;place-items:center;min-height:100vh;margin:0;text-align:center;padding:2rem}}a{{color:#3b82f6}}</style>
</head>
<body>
<p>This page has moved.<br /><a href="{target}">Continue to {url}</a></p>
</body>
</html>
""".format(title=e(title), url=e(url), target=e(target))


# --------------------------------------------------------------------------
# sitemap / robots
# --------------------------------------------------------------------------

def write_sitemap(out, site):
    base = site["base_url"].rstrip("/")
    urls = []
    for path, changefreq, priority in _pages:
        urls.append(
            "  <url>\n    <loc>%s%s</loc>\n    <lastmod>%s</lastmod>\n"
            "    <changefreq>%s</changefreq>\n    <priority>%s</priority>\n  </url>"
            % (base, path, TODAY, changefreq, priority))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    with open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(xml)

    robots = ("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % base)
    with open(os.path.join(out, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(robots)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def build(out):
    data = read_json("site.json")
    errata = read_json("errata.json")
    site = data["site"]
    series_list = data["series"]
    base_tpl = read_template("base.html")

    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)

    # static assets, verbatim
    for name in os.listdir(STATIC):
        src = os.path.join(STATIC, name)
        dst = os.path.join(out, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    def emit(path, title, description, content, ld="", **kw):
        page = render_shell(base_tpl, site, title=title, description=description,
                            path=path, content=content, head_extra=ld, **kw)
        write_page(out, path, page, **{})
        return page

    series = series_list[0]
    slug = series["slug"]

    # index errata records by volume slug
    by_volume = {}
    for record in errata["books"]:
        if record.get("series") == slug:
            by_volume[record["volume"]] = record

    # --- home
    content, ld = page_home(site, series_list)
    emit("/", "Nexoma Books — Applied AI Engineering by Dr. Ahmed AlSalih",
         site["description"], content, ld)
    _pages[-1] = ("/", "weekly", "1.0")

    # --- series
    content, ld = page_series(site, series)
    emit("/%s/" % slug,
         "%s — %s | Nexoma Books" % (series["title"], series["tagline"]),
         series["short_description"], content, ld)
    _pages[-1] = ("/%s/" % slug, "weekly", "0.9")

    # --- volumes
    for vol in series["volumes"]:
        record = by_volume.get(vol["slug"], {"entries": []})
        content, ld = page_volume(site, series, vol, record)
        emit("/%s/%s/" % (slug, vol["slug"]),
             "Volume %s: %s — %s | Nexoma Books" % (vol["roman"], vol["title"], series["title"]),
             "%s %s" % (vol["subtitle"] + ".", vol["mission"]),
             content, ld, og_image=(site["base_url"].rstrip("/") + vol["cover"]) if vol.get("cover") else None,
             og_type="book")
        _pages[-1] = ("/%s/%s/" % (slug, vol["slug"]), "weekly", "0.9")

    # --- errata
    content, ld = page_errata_index(site, series, errata, by_volume)
    emit("/%s/errata/" % slug,
         "Errata — %s | Nexoma Books" % series["title"],
         "Confirmed corrections to %s, listed by volume and printing." % series["title"],
         content, ld)
    _pages[-1] = ("/%s/errata/" % slug, "weekly", "0.8")

    for vol in series["volumes"]:
        record = by_volume.get(vol["slug"], {"entries": []})
        content, ld = page_errata_volume(site, series, vol, record)
        emit("/%s/errata/%s/" % (slug, vol["slug"]),
             "Errata — Volume %s: %s | Nexoma Books" % (vol["roman"], vol["title"]),
             "Confirmed corrections to %s, Volume %s: %s."
             % (series["title"], vol["roman"], vol["title"]),
             content, ld)
        _pages[-1] = ("/%s/errata/%s/" % (slug, vol["slug"]), "weekly", "0.7")

    # --- companion / instructors / contact
    content, ld = page_companion(site, series)
    emit("/%s/companion/" % slug,
         "Companion code — %s | Nexoma Books" % series["title"],
         "Runnable laboratories and reference solutions for %s." % series["title"],
         content, ld)

    content, ld = page_instructors(site, series)
    emit("/%s/instructors/" % slug,
         "Instructor resources — %s | Nexoma Books" % series["title"],
         "Slide decks, syllabi, teaching notes, question banks, and assessment keys, "
         "free to verified instructors.", content, ld)

    content, ld = page_contact(site)
    emit("/contact/", "Contact — Nexoma Books",
         "How to reach Nexoma Labs LLC about the books, errata, instructor resources, "
         "rights, and permissions.", content, ld)

    # --- 404 (GitHub Pages serves /404.html)
    content, ld = page_404(site, series)
    page = render_shell(base_tpl, site, title="Page not found — Nexoma Books",
                        description="That page could not be found.", path="/404.html",
                        content=content, robots="noindex,follow")
    write_page(out, "404.html", page, in_sitemap=False)

    # --- legacy printed URLs (www.nexomalabs.com/books/prompt-engineering-series/...)
    # Mirrored here so a /books/* path on this host also resolves.
    for src, dst, title in [
        ("/books/", "/", "Nexoma Books"),
        ("/books/%s/" % slug, "/%s/" % slug, series["title"]),
        ("/books/%s/errata/" % slug, "/%s/errata/" % slug, "Errata"),
        ("/books/%s/errata" % slug, "/%s/errata/" % slug, "Errata"),
    ]:
        write_page(out, src, redirect_page(site, dst, title), in_sitemap=False)
    for vol in series["volumes"]:
        write_page(out, "/books/%s/%s/" % (slug, vol["slug"]),
                   redirect_page(site, "/%s/%s/" % (slug, vol["slug"]),
                                 "Volume %s" % vol["roman"]),
                   in_sitemap=False)

    write_sitemap(out, site)

    n = sum(len(files) for _, _, files in os.walk(out))
    print("Built %d files into %s" % (n, out))
    print("Pages in sitemap: %d" % len(_pages))
    return out


def main():
    ap = argparse.ArgumentParser(description="Build books.nexomalabs.com")
    ap.add_argument("--out", default=os.path.join(ROOT, "_site"))
    ap.add_argument("--serve", action="store_true",
                    help="serve the built site on http://localhost:8000")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    out = build(args.out)

    if args.serve:
        import http.server
        import socketserver
        import functools
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=out)
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", args.port), handler) as httpd:
            print("Serving %s at http://localhost:%d/  (Ctrl-C to stop)" % (out, args.port))
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
