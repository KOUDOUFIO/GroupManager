"""Recopie les traductions de translations_en.py dans le catalogue anglais.

Usage (depuis la racine du projet) :
    python manage.py makemessages -l en --no-wrap --no-location -i ".venv/*" -i "clients/*" -i "docker/*"
    python locale/fill_po.py
    python manage.py compilemessages -l en

Echoue (code 1) en listant les textes sans traduction, pour ne rien oublier.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from translations_en import EN  # noqa: E402

PO_PATH = Path(__file__).resolve().parent / "en" / "LC_MESSAGES" / "django.po"


def unquote(value):
    return re.sub(r'\\(["\\n])', lambda m: "\n" if m.group(1) == "n" else m.group(1), value)


def quote(value):
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def main():
    lines = PO_PATH.read_text(encoding="utf-8").splitlines()
    out, missing = [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^msgid "(.*)"$', line)
        if not m or m.group(1) == "":
            out.append(line)
            i += 1
            continue
        msgid = unquote(m.group(1))
        out.append(line)
        i += 1
        if lines[i].startswith("msgid_plural"):
            out.append(lines[i])
            i += 1
            value = EN.get(msgid)
            if not isinstance(value, tuple):
                missing.append(msgid)
                value = ("", "")
            while i < len(lines) and lines[i].startswith("msgstr["):
                i += 1
            out.append(f'msgstr[0] "{quote(value[0])}"')
            out.append(f'msgstr[1] "{quote(value[1])}"')
        else:
            value = EN.get(msgid)
            if not isinstance(value, str):
                missing.append(msgid)
                value = ""
            out.append(f'msgstr "{quote(value)}"')
            i += 1
    # makemessages marque les entrees devinees "fuzzy" : elles seraient ignorees.
    text = "\n".join(out) + "\n"
    text = re.sub(r"^#, fuzzy\n(?!msgid \"\"\n)", "", text, flags=re.M)
    text = re.sub(r"^#\| .*\n", "", text, flags=re.M)
    PO_PATH.write_text(text, encoding="utf-8")
    if missing:
        print(f"{len(missing)} texte(s) sans traduction dans translations_en.py :")
        for msgid in missing:
            print("  -", msgid)
        sys.exit(1)
    print("Toutes les traductions sont renseignees.")


if __name__ == "__main__":
    main()
