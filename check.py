#!/usr/bin/env python3
"""Verify the built site: every internal href/src resolves, images have alt text,
each page has a title, description, and canonical URL. Exits non-zero on failure."""

import os
import re
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_site")

HREF = re.compile(r'(?:href|src)="([^"]+)"')
IMG = re.compile(r"<img\b[^>]*>", re.I)
ALT = re.compile(r'\balt="', re.I)


def resolves(url):
    if url.startswith(("http://", "https://", "mailto:", "#", "data:", "tel:")):
        return True
    path = url.split("#", 1)[0].split("?", 1)[0]
    if not path:
        return True
    if not path.startswith("/"):
        return None  # relative links are not used on this site
    target = os.path.join(OUT, path.lstrip("/"))
    if os.path.isfile(target):
        return True
    if os.path.isdir(target) and os.path.isfile(os.path.join(target, "index.html")):
        return True
    return False


def main():
    problems = []
    checked = 0
    for root, _, files in os.walk(OUT):
        for name in files:
            if not name.endswith(".html"):
                continue
            full = os.path.join(root, name)
            rel = "/" + os.path.relpath(full, OUT)
            text = open(full, encoding="utf-8").read()
            checked += 1

            for url in HREF.findall(text):
                ok = resolves(url)
                if ok is False:
                    problems.append("%s -> broken link %s" % (rel, url))
                elif ok is None:
                    problems.append("%s -> relative link %s (use absolute paths)" % (rel, url))

            for tag in IMG.findall(text):
                if not ALT.search(tag):
                    problems.append("%s -> <img> without alt: %s" % (rel, tag[:70]))

            if "/books/" in rel:
                continue  # redirect stubs are intentionally minimal
            for needle, label in (("<title>", "title"),
                                  ('name="description"', "meta description"),
                                  ('rel="canonical"', "canonical")):
                if needle not in text:
                    problems.append("%s -> missing %s" % (rel, label))

    if problems:
        print("FAIL — %d problem(s) across %d pages:" % (len(problems), checked))
        for p in problems:
            print("  " + p)
        return 1
    print("OK — %d pages, all internal links and assets resolve." % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
