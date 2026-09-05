# books.nexomalabs.com

The reader-facing site for books published by **Nexoma Labs LLC**.

It exists to make the URLs printed inside the books resolve — the series page, the errata
page, the companion-code page, and the instructor-resources page — and to give each volume
a page that can be linked from a retailer listing.

---

## URLs this site owns

| URL | Page |
|-----|------|
| `/` | All Nexoma books |
| `/prompt-engineering-series/` | *Applied AI Engineering* — series overview |
| `/prompt-engineering-series/volume-1/` … `volume-4/` | One page per volume |
| `/prompt-engineering-series/errata/` | Errata index, all volumes |
| `/prompt-engineering-series/errata/volume-1/` … `volume-4/` | Errata per volume |
| `/prompt-engineering-series/companion/` | Companion lab code |
| `/prompt-engineering-series/instructors/` | Instructor resources |
| `/contact/` | Contact routes |

Every public URL ends in a slash, because that is the form printed in the books.

`/books/prompt-engineering-series/…` is also served here as a set of redirect stubs, so the
older `/books/`-prefixed form of any link still lands in the right place.

The books themselves print the subdomain form directly — the manuscript repository was
normalised to `books.nexomalabs.com/prompt-engineering-series/` and its `errata/` path — so
no redirect from `www.nexomalabs.com` is required.

---

## Build and publish

Python 3.9 or newer, standard library only — no dependencies, no package manager.

```bash
python3 build.py            # build into _site/
python3 build.py --serve    # build, then preview on http://localhost:8000
python3 check.py            # verify links, assets, alt text, and page metadata
python3 publish.py          # copy _site/ to the repository root, which Pages serves
```

The full loop after any content edit is:

```bash
python3 build.py && python3 check.py && python3 publish.py && git add -A && git commit
```

`_site/` is a scratch directory and is not committed. The generated pages **are**
committed at the repository root, because GitHub Pages serves this repository from the
`main` branch. `publish.py` only ever deletes files it wrote itself — it tracks them in
`.publish-manifest` — and refuses to touch `build.py`, `content/`, `templates/`,
`static/`, `tools/`, `.github/`, or `README.md`.

CI runs `publish.py --check` on every push and fails if the committed pages have drifted
from the sources, so the live site can never silently disagree with `content/`.

---

## Editing content

All copy lives in two JSON files. You should not need to touch HTML to update the site.

### `content/site.json`

Site-wide settings, the series description, and one entry per volume: title, subtitle,
status, difficulty, chapter list, formats, ISBNs, and buy links.

**To mark a volume as on sale**, set its `status` / `status_label` and add buy links:

```json
"status": "available",
"status_label": "Available now",
"status_note": "Paperback and Kindle editions are shipping.",
"buy_links": [
  { "label": "Buy on Amazon", "url": "https://www.amazon.com/dp/XXXXXXXXXX" }
]
```

Valid `status` values, which drive the badge colour, are `available`, `in-production`,
`in-development`, and `planned`. When `buy_links` is empty the page shows an honest
*"Not yet on sale"* state rather than a dead button.

**To add a cover**, drop the image in `static/img/covers/` and set `"cover":
"/img/covers/volume-1.png"` on that volume.

### `content/errata.json`

One record per volume. To publish a correction, add an entry to that volume's `entries`
array and update `last_reviewed`:

```json
{
  "id": "V1-001",
  "severity": "error",
  "location": "Chapter 7, page 214, second paragraph",
  "printings": "1st printing",
  "reported": "2026-08-01",
  "corrected": "2026-08-14",
  "incorrect": "The text as printed.",
  "correct": "The text as it should read.",
  "note": "Optional explanation."
}
```

An empty `entries` array renders *"No errata reported"* — which is a valid and required
state, since the errata URL is printed in the book and must resolve from day one.

`_example_entry` in that file is a template and is never rendered.

---

## Cover art

Volume I currently renders a placeholder. The artwork in the manuscript repository
(`volumes/volume-1/assets/cover/`) still carries the retired *"Prompt Engineering
Masterclass — The Complete 5-Volume Reference"* branding, which contradicts the current
four-volume *Applied AI Engineering* series identity, so it is deliberately not published
here. Replace it before release.

The Open Graph share card at `static/img/og-default.png` is generated from
`tools/og-card.html`:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --hide-scrollbars --window-size=1200,630 \
  --screenshot="$PWD/static/img/og-default.png" "file://$PWD/tools/og-card.html"
```

---

## Deployment

GitHub Pages serves the `main` branch root. Pushing committed, published pages is the
deployment — there is no build step on GitHub's side, and `.nojekyll` stops Jekyll from
reprocessing the output.

`.github/workflows/deploy.yml` does not deploy; it verifies. On every push and pull
request it rebuilds from source, runs `check.py`, and runs `publish.py --check`.

The custom domain is pinned by `CNAME`. DNS needs a `CNAME` record for `books` pointing
at `nexomalabs.github.io`.

### Switching to the GitHub Actions deployment source

If you would rather not commit generated pages, set **Settings → Pages → Build and
deployment → Source** to **GitHub Actions**, then replace the verify workflow with a
deploy job that uploads `_site` via `actions/upload-pages-artifact` and
`actions/deploy-pages`, and delete the published files from the repository root along
with `publish.py` and `.publish-manifest`. The current arrangement was chosen because it
needs no repository settings change and matches how `nexomalabs.github.io` is already
run.

---

## Layout

```text
build.py                  the generator — stdlib only
check.py                  link, asset, alt-text, and metadata verification
publish.py                copies _site/ to the repository root that Pages serves
content/site.json         site settings, series, volumes
content/errata.json       errata records
templates/base.html       the page shell (head, header, footer)
static/                   copied verbatim into the build: CSS, JS, images, CNAME
tools/og-card.html        source for the Open Graph share image
.publish-manifest         generated — the root files publish.py manages
```

Everything else at the repository root — `index.html`, `404.html`, `sitemap.xml`,
`robots.txt`, `css/`, `js/`, `img/`, `contact/`, `books/`, `prompt-engineering-series/` —
is generated. Edit `content/`, never those files.

Page bodies are composed in `build.py`, one function per page type. Adding a page means
adding a function and one `emit(...)` call.

---

© 2026 Nexoma Labs LLC.
