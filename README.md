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
older `/books/`-prefixed form of any printed link still lands in the right place.

> **Redirect still required on the main site.** The books print
> `www.nexomalabs.com/books/prompt-engineering-series/` and
> `www.nexomalabs.com/books/prompt-engineering-series/errata`. Those paths live on the
> `www` host, not here. Add a redirect from `www.nexomalabs.com/books/*` to
> `books.nexomalabs.com/*` in the `nexomalabs.github.io` repository before Volume I ships.

---

## Build

Python 3.9 or newer, standard library only — no dependencies, no package manager.

```bash
python3 build.py            # build into _site/
python3 build.py --serve    # build, then serve on http://localhost:8000
python3 check.py            # verify links, assets, alt text, and page metadata
```

`_site/` is generated and is not committed. CI rebuilds it on every push.

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

GitHub Pages, built by `.github/workflows/deploy.yml` on every push to `main`.

Pull requests build and run `check.py` but do not deploy.

**One-time setup:** in the repository settings, set **Pages → Build and deployment →
Source** to **GitHub Actions**, then point a `CNAME` DNS record for
`books` at `nexomalabs.github.io`. The `CNAME` file in `static/` is copied into the build
output and pins the custom domain.

---

## Layout

```text
build.py                  the generator — stdlib only
check.py                  link, asset, alt-text, and metadata verification
content/site.json         site settings, series, volumes
content/errata.json       errata records
templates/base.html       the page shell (head, header, footer)
static/                   copied verbatim into the build: CSS, JS, images, CNAME
tools/og-card.html        source for the Open Graph share image
```

Page bodies are composed in `build.py`, one function per page type. Adding a page means
adding a function and one `emit(...)` call.

---

© 2026 Nexoma Labs LLC.
