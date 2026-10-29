"""Mirror Will's master CV (Word) into data/cv.json, which build.py renders as cv.html.

Usage:  python3 scripts/update_cv.py [path/to/Mair_CV_<date>.docx]
        python3 scripts/build.py

With no path it reads the newest OneDrive/CV/Mair_CV_*.docx (the single dated master CV).
The Word file is the source of truth; never edit data/cv.json by hand.

Web-only rules (everything else is copied as written):
  - no email address, birthplace or citizenship (masthead lines dropped)
  - no named co-lead of the Healthy Aging Initiative (willmair.com rule)
  - plain hyphens instead of en and em dashes (Will's writing rule)
"""
import html, json, pathlib, re, sys, zipfile
from xml.etree import ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
CV_DIR = pathlib.Path.home() / "Library/CloudStorage/OneDrive-HarvardUniversity/CV"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

REDACT = [r"\s*\(co-lead L\. Kubzansky\)"]


def clean(s):
    s = s.replace(" ", " ")
    s = re.sub(r"\s—\s([^—.;]{1,200}?)\s—\s", r", \1, ", s)  # paired em dashes -> commas
    s = re.sub(r"\s*—\s*", "; ", s)                           # single em dash -> semicolon
    return s.replace("–", "-")


def runs_html(p, rels):
    """(when, body_html, bold_only) for a paragraph; when = text before the first tab, if any."""
    parts, when, seen_tab = [], None, False

    def emit(r, href=None):
        nonlocal when, seen_tab
        rpr = r.find(W + "rPr")
        b = rpr is not None and rpr.find(W + "b") is not None
        i = rpr is not None and rpr.find(W + "i") is not None
        for n in r:
            if n.tag == W + "tab":
                if not seen_tab:
                    seen_tab, when = True, "".join(t for t, *_ in parts).strip()
                    parts.clear()
                else:
                    parts.append((" ", False, False, None))
            elif n.tag == W + "t" and n.text:
                parts.append((n.text, b, i, href))

    for n in p:
        if n.tag == W + "r":
            emit(n)
        elif n.tag == W + "hyperlink":
            href = rels.get(n.get(R + "id"))
            for r in n.iter(W + "r"):
                emit(r, href)
    # merge neighbouring runs with the same formatting
    merged = []
    for t, b, i, href in parts:
        if merged and merged[-1][1:] == [b, i, href]:
            merged[-1][0] += t
        else:
            merged.append([t, b, i, href])
    out, texts = [], [m for m in merged if m[0].strip()]
    for t, b, i, href in merged:
        s = html.escape(t, quote=False)
        if b and s.strip():
            s = f"<strong>{s}</strong>"
        if i and s.strip():
            s = f"<em>{s}</em>"
        if href:
            label = t.strip()
            cls = ' class="cv-pill"' if re.match(r"(PubMed|Preprint|bioRxiv|Research Square)", label) else ""
            lead = " " if t.startswith(" ") else ""
            s = f'{lead}<a{cls} href="{html.escape(href)}" target="_blank" rel="noopener">{html.escape(clean(label))}</a>'
        out.append(s)
    body = clean("".join(out).strip())
    body = re.sub(r"(?<![/\w])(scholar\.google\.com/\S+?)(?=[\s<]|$)", r'<a href="https://\1" target="_blank" rel="noopener">Google Scholar</a>', body)
    for pat in REDACT:
        body = re.sub(pat, "", body)
    bold_only = bool(texts) and all(m[1] for m in texts)
    return (clean(when) if when is not None else None), body, bold_only


def plain(el):
    return "".join(n.text or "" for n in el.iter(W + "t")).strip()


def sentence_case(s):
    s = s.strip().lower()
    return s[:1].upper() + s[1:]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def parse(path):
    z = zipfile.ZipFile(path)
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("word/_rels/document.xml.rels"))
            if r.get("TargetMode") == "External"}
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    cv = {"source": path.name, "name": "", "tagline": "", "updated": "", "glance": [], "sections": []}
    sec = None
    for el in body:
        if el.tag == W + "tbl":
            for row in el.iter(W + "tr"):  # "at a glance" panel: label cell, text cell
                paras = [runs_html(p, rels)[1] for p in row.iter(W + "p")]
                paras = [x for x in paras if x]
                if len(paras) >= 2:
                    cv["glance"].append({"label": sentence_case(re.sub(r"<[^>]+>", "", paras[0])), "html": " ".join(paras[1:])})
            continue
        if el.tag != W + "p":
            continue
        text = plain(el)
        if not text:
            continue
        ppr = el.find(W + "pPr")
        heading = ppr is not None and ppr.find(W + "pBdr") is not None
        if sec is None and not heading:
            if not cv["name"]:
                cv["name"] = text
            elif not cv["tagline"]:
                cv["tagline"] = clean(text)
            elif m := re.search(r"Last updated (.+)$", text):
                cv["updated"] = m.group(1).strip()
            continue  # other masthead lines (address, email, birthplace) are not published
        if heading:
            title = sentence_case(text)
            sec = {"title": title, "id": slug(title), "blocks": []}
            cv["sections"].append(sec)
            continue
        when, h, bold_only = runs_html(el, rels)
        if when is not None:
            sec["blocks"].append({"type": "entry", "when": when, "html": h})
        elif bold_only and len(text) < 90:
            sec["blocks"].append({"type": "sub", "title": clean(text)})
        else:
            sec["blocks"].append({"type": "para", "html": h})
    return cv


def main():
    if len(sys.argv) > 1:
        path = pathlib.Path(sys.argv[1])
    else:
        found = sorted(CV_DIR.glob("Mair_CV_*.docx"))
        if not found:
            sys.exit(f"No Mair_CV_*.docx in {CV_DIR}")
        path = found[-1]
    cv = parse(path)
    out = ROOT / "data" / "cv.json"
    out.write_text(json.dumps(cv, ensure_ascii=False, indent=1) + "\n")
    n = sum(1 for s in cv["sections"] for b in s["blocks"] if b["type"] == "entry")
    print(f"{path.name} -> data/cv.json: {len(cv['sections'])} sections, {n} entries, updated {cv['updated']}")


if __name__ == "__main__":
    main()
