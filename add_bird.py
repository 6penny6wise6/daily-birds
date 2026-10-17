#!/usr/bin/env python3
"""Add, replace, or remove a day's bird in birds.json.

Examples:
  python3 add_bird.py --date 2026-10-31 --name "Barn Owl" --scientific "Tyto alba" \
      --fact "Barn Owls can find mice in total darkness by sound alone." \
      [--source https://www.allaboutbirds.org/guide/Barn_Owl/] \
      [--question "How do Barn Owls hunt in the dark?" --answer "By hearing."] \
      [--photo-url https://commons.wikimedia.org/wiki/File:Something.jpg]
  python3 add_bird.py --remove 2026-10-31

The photo comes from Wikimedia Commons. With no --photo-url it uses the bird's
Wikipedia lead photo, then falls back to a Commons search. Only CC BY, CC BY-SA,
CC0 and public domain images are accepted. Add --push to commit and push.
"""
import argparse, datetime, html, io, json, os, re, subprocess, sys, urllib.parse, urllib.request

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "birds.json")
PHOTOS = os.path.join(HERE, "photos")
UA = "DailyBirdsBot/1.0 (https://github.com/6penny6wise6/daily-birds)"
COMMONS = "https://commons.wikimedia.org/w/api.php"
WIKI = "https://en.wikipedia.org/w/api.php"
OK_LICENSE = re.compile(r"^(cc[ -]?by(-sa)?( \d(\.\d)?)?( [a-z]{2,3})?|cc0( 1\.0)?|public domain|pd(-[\w.-]+)?)$", re.I)


def get(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def api(base, **params):
    params.update(format="json", formatversion="2")
    return json.loads(get(base, params))


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def file_title_from_url(url):
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path)
    name = path.rsplit("/", 1)[-1]
    if name.startswith("File:"):
        name = name[5:]
    return "File:" + name.replace("_", " ")


def image_info(title):
    d = api(COMMONS, action="query", titles=title, prop="imageinfo",
            iiprop="url|extmetadata|mime|size", iiurlwidth="1400")
    pages = d["query"]["pages"]
    if not pages or "imageinfo" not in pages[0]:
        return None
    ii = pages[0]["imageinfo"][0]
    md = ii.get("extmetadata", {})
    lic = strip_html(md.get("LicenseShortName", {}).get("value", ""))
    artist = strip_html(md.get("Artist", {}).get("value", "")) or "Unknown"
    desc = strip_html(md.get("ImageDescription", {}).get("value", "")).lower()
    cats = md.get("Categories", {}).get("value", "").lower()
    return {
        "title": pages[0]["title"], "mime": ii.get("mime", ""), "width": ii.get("width", 0),
        "thumb": ii.get("thumburl") or ii["url"], "page": ii["descriptionurl"],
        "license": lic, "artist": re.sub(r"\s+", " ", re.sub(r"\(?https?://\S+\)?", "", artist)).strip()[:120] or "Unknown",
        "ai": ("ai-generated" in cats or "ai generated" in desc or "midjourney" in desc
               or "stable diffusion" in desc),
    }


def acceptable(info):
    return (info and info["mime"] in ("image/jpeg", "image/png", "image/webp")
            and info["width"] >= 800 and OK_LICENSE.match(info["license"]) and not info["ai"])


def candidates(name, scientific):
    for q in (name, scientific):
        if not q:
            continue
        try:
            d = api(WIKI, action="query", titles=q, redirects=1, prop="pageimages",
                    piprop="name", pilicense="free")
            p = d["query"]["pages"][0]
            if p.get("pageimage"):
                yield "File:" + p["pageimage"].replace("_", " ")
        except Exception:
            pass
    d = api(COMMONS, action="query", list="search", srnamespace=6, srlimit=20,
            srsearch=f'"{scientific or name}" filetype:bitmap')
    for r in d["query"]["search"]:
        t = r["title"].lower()
        if any(w in t for w in ("map", "range", "egg", "skeleton", "drawing", "illustration", "stamp")):
            continue
        yield r["title"]


def fetch_photo(name, scientific, photo_url=None):
    titles = [file_title_from_url(photo_url)] if photo_url else candidates(name, scientific)
    for t in titles:
        info = image_info(t)
        if acceptable(info) and (photo_url or info["artist"] != "Unknown"):
            break
        if photo_url:
            sys.exit(f"Rejected {t}: license '{info and info['license']}' or format/size not allowed")
    else:
        sys.exit("No freely licensed photo found. Pass --photo-url with a Commons file page.")
    img = Image.open(io.BytesIO(get(info["thumb"]))).convert("RGB")
    if img.width > 1200:
        img = img.resize((1200, round(img.height * 1200 / img.width)), Image.LANCZOS)
    rel = f"photos/{slugify(name)}.jpg"
    out = os.path.join(HERE, rel)
    for q in (85, 80, 75, 70, 65, 60):
        img.save(out, "JPEG", quality=q, optimize=True, progressive=True)
        if os.path.getsize(out) <= 300_000:
            break
    print(f"photo: {info['title']} | {info['license']} | {info['artist']} | {os.path.getsize(out)//1024} KB")
    return rel, info


def load():
    if os.path.exists(DATA):
        with open(DATA) as f:
            return json.load(f)
    return []


def save(birds):
    birds.sort(key=lambda b: b["date"])
    with open(DATA, "w") as f:
        json.dump(birds, f, indent=2, ensure_ascii=False)
        f.write("\n")


def push(msg):
    subprocess.run(["git", "-C", HERE, "add", "-A"], check=True)
    subprocess.run(["git", "-C", HERE, "commit", "-m", msg], check=True)
    subprocess.run(["git", "-C", HERE, "push"], check=True)


def main():
    ap = argparse.ArgumentParser(description="Add or remove a day's bird.")
    ap.add_argument("--date"); ap.add_argument("--name"); ap.add_argument("--scientific")
    ap.add_argument("--fact"); ap.add_argument("--source", default="")
    ap.add_argument("--question"); ap.add_argument("--answer")
    ap.add_argument("--photo-url"); ap.add_argument("--remove", metavar="DATE")
    ap.add_argument("--push", action="store_true", help="git commit and push afterwards")
    a = ap.parse_args()
    birds = load()

    if a.remove:
        datetime.date.fromisoformat(a.remove)
        left = [b for b in birds if b["date"] != a.remove]
        if len(left) == len(birds):
            sys.exit(f"No bird on {a.remove}")
        save(left)
        print(f"removed {a.remove}")
        if a.push:
            push(f"Remove bird for {a.remove}")
        return

    for k in ("date", "name", "scientific", "fact"):
        if not getattr(a, k):
            ap.error(f"--{k} is required")
    datetime.date.fromisoformat(a.date)
    if bool(a.question) != bool(a.answer):
        ap.error("--question and --answer go together")
    rel, info = fetch_photo(a.name, a.scientific, a.photo_url)
    entry = {
        "date": a.date, "name": a.name, "scientific": a.scientific, "photo": rel,
        "photo_credit": info["artist"], "photo_license": info["license"],
        "photo_source_url": info["page"], "fact": a.fact,
        "source": a.source or "https://en.wikipedia.org/wiki/" + urllib.parse.quote(a.name.replace(" ", "_")),
    }
    if a.question:
        entry["question"], entry["answer"] = a.question, a.answer
    replaced = any(b["date"] == a.date for b in birds)
    birds = [b for b in birds if b["date"] != a.date] + [entry]
    save(birds)
    print(("replaced" if replaced else "added") + f" {a.date}: {a.name}")
    if a.push:
        push(f"{'Replace' if replaced else 'Add'} bird for {a.date}: {a.name}")


if __name__ == "__main__":
    main()
