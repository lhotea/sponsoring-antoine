#!/usr/bin/env python3
"""Check that every translated string on the page resolves in every language.

The page translates itself at runtime: elements carry a data-i18n="<key>"
attribute and setLang() looks that key up in the I18N dictionary. A key that
is missing from one language silently leaves the German default on screen, so
this catches it before it ships.

Run locally with:

    python3 scripts/check-i18n.py
"""

import json
import pathlib
import re
import sys

PAGE = pathlib.Path(__file__).resolve().parent.parent / "index.html"

# Keys setLang() looks up directly rather than through a data-i18n attribute.
EXTRA_KEYS = {"meta.title"}


def load_dictionaries(html):
    match = re.search(r"const I18N = (\{.*?\n\});", html, re.S)
    if not match:
        sys.exit("could not find the I18N dictionary in index.html")

    blob = match.group(1)
    # The language keys are bare identifiers (de:, fr:, en:) — JSON wants them quoted.
    blob = re.sub(r'^(\s*)([A-Za-z_][\w-]*)(\s*):', r'\1"\2"\3:', blob, flags=re.M)
    # Tolerate a trailing comma before a closing brace.
    blob = re.sub(r",(\s*\})", r"\1", blob)

    try:
        return json.loads(blob)
    except json.JSONDecodeError as exc:
        sys.exit(f"the I18N dictionary did not parse as JSON: {exc}")


def main():
    html = PAGE.read_text(encoding="utf-8")
    used = set(re.findall(r'data-i18n="([^"]+)"', html)) | EXTRA_KEYS
    dicts = load_dictionaries(html)
    langs = sorted(dicts)

    if not langs:
        sys.exit("the I18N dictionary defines no languages")

    problems = []
    for lang in langs:
        missing = sorted(used - set(dicts[lang]))
        if missing:
            problems.append(f"{lang} is missing {len(missing)} key(s): " + ", ".join(missing))

    shared = set.intersection(*(set(dicts[lang]) for lang in langs))
    for lang in langs:
        only_here = sorted(set(dicts[lang]) - shared)
        if only_here:
            problems.append(
                f"{lang} defines key(s) the other languages do not: " + ", ".join(only_here)
            )

    print(f"page:      {PAGE.name}")
    print(f"languages: {', '.join(langs)}")
    print(f"keys used: {len(used)}")

    unused = sorted(shared - used)
    if unused:
        # Not a failure: a leftover key is harmless, just dead weight.
        print(f"note:      {len(unused)} key(s) defined but unused: " + ", ".join(unused))

    if problems:
        print("\nFAILED")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nOK — every key resolves in every language")
    return 0


if __name__ == "__main__":
    sys.exit(main())
