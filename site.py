#!/usr/bin/env python3
"""Builds the apps site and publishes installers. Standard library only.

  python3 site.py build                             Render the site into _site/
  python3 site.py serve                             Build, then preview on localhost:8000
  python3 site.py new my-app "My App"               Start a new app in apps/my-app/
  python3 site.py release my-app android app.apk    Upload an installer, record it, push
"""
import argparse
import datetime
import hashlib
import html
import http.server
import json
import functools
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
APPS = ROOT / "apps"
OUT = ROOT / "_site"
REPO = "yzqhrmn/apps"
SITE_URL = "https://yzqhrmn.dev/"
SITE_NAME = "Ayaz Apps"
SITE_LINE = "Small tools for phones and Macs. Download one and try it."
FONTS = (
    "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:"
    "opsz,wght@12..96,500;12..96,700&display=swap"
)
PLATFORM_LABELS = {"android": "Android", "ios": "iPhone", "mac": "Mac", "windows": "Windows", "web": "Web"}
esc = html.escape


def load_apps():
    apps = []
    for path in sorted(APPS.glob("*/app.json")):
        app = json.loads(path.read_text())
        app["slug"] = path.parent.name
        app["icon"] = next(path.parent.glob("icon.*")).name
        apps.append(app)
    apps.sort(key=lambda a: a.get("updated", ""), reverse=True)
    return sorted(apps, key=lambda a: a.get("order", 99))


def format_size(num_bytes):
    if num_bytes < 1024 * 1024:
        return f"{max(1, round(num_bytes / 1024))} KB"
    return f"{num_bytes / 1024 / 1024:.0f} MB" if num_bytes >= 10 * 1024 * 1024 else f"{num_bytes / 1024 / 1024:.1f} MB"


def format_date(iso):
    date = datetime.date.fromisoformat(iso)
    return f"{date.strftime('%B')} {date.day}, {date.year}"


def versioned(name):
    """Asset path with a content hash, so a new design is never mixed with a cached old file."""
    return f"assets/{name}?v={hashlib.sha256((ROOT / 'assets' / name).read_bytes()).hexdigest()[:8]}"


def page(title, description, body, base="", image=None, url=SITE_URL):
    og_image = f'<meta property="og:image" content="{esc(image)}">' if image else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(url)}">
{og_image}
<meta name="theme-color" content="#f6f3ec" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#14161b" media="(prefers-color-scheme: dark)">
<link rel="icon" href="{base}assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}" media="print" onload="this.media='all'">
<link rel="stylesheet" href="{base}{versioned('style.css')}">
<script src="{base}{versioned('site.js')}" defer></script>
</head>
<body>
<header class="top"><a class="brand" href="{base or './'}">{esc(SITE_NAME)}</a></header>
{body}
<footer class="foot">
  <p>Built by Ayaz with Claude.</p>
  <p><a href="https://github.com/{REPO}">Source of this site</a></p>
</footer>
</body>
</html>
"""


def tags(app):
    return "".join(f'<li>{esc(PLATFORM_LABELS[p["id"]])}</li>' for p in app["platforms"])


def home(apps):
    used = [key for key in PLATFORM_LABELS if any(p["id"] == key for a in apps for p in a["platforms"])]
    filters = "".join(
        f'<button type="button" data-filter="{key}" aria-pressed="false">{esc(PLATFORM_LABELS[key])}</button>'
        for key in used
    )
    rows = "".join(f"""
    <li class="app" data-platforms="{' '.join(p['id'] for p in a['platforms'])}" style="--accent:{esc(a['accent'])}">
      <a href="{esc(a['slug'])}/">
        <img src="{esc(a['slug'])}/{esc(a['icon'])}" alt="" width="96" height="96">
        <span class="app-text">
          <span class="app-name">{esc(a['name'])}</span>
          <span class="app-line">{esc(a['tagline'])}</span>
          <ul class="tags">{tags(a)}</ul>
        </span>
        <span class="go" aria-hidden="true">→</span>
      </a>
    </li>""" for a in apps)
    body = f"""<main>
  <section class="intro">
    <h1>Apps we made.</h1>
    <p>{esc(SITE_LINE)}</p>
  </section>
  <div class="filters" role="group" aria-label="Filter by platform">
    <button type="button" data-filter="all" aria-pressed="true">All</button>{filters}
  </div>
  <ul class="apps">{rows}
  </ul>
  <p class="empty" hidden>Nothing for this platform yet.</p>
</main>"""
    return page(SITE_NAME, SITE_LINE, body)


def download(platform):
    label = PLATFORM_LABELS[platform["id"]]
    needs = esc(platform.get("requires", ""))
    if not platform.get("url"):
        return f"""<div class="dl off" data-platform="{platform['id']}">
        <strong>{esc(label)}</strong><span>{needs}</span>
        <small>{esc(platform.get('note', 'Not available yet.'))}</small>
      </div>"""
    detail = " · ".join(x for x in (esc(format_size(platform["size"])), needs) if x)
    note = f"<small>{esc(platform['note'])}</small>" if platform.get("note") else ""
    return f"""<a class="dl" data-platform="{platform['id']}" href="{esc(platform['url'])}">
        <strong>Download for {esc(label)}</strong><span>{detail}</span>{note}
      </a>"""


def gallery(app):
    shots = sorted(p.name for p in (APPS / app["slug"] / "shots").glob("*.jpg"))
    if not shots:
        return ""
    sizes = [(1400, 896) if name.startswith("mac") else (540, 1200) for name in shots]
    thumbs = "".join(
        f'<li><a href="shots/{esc(name)}"{" aria-current=true" if number == 1 else ""} '
        f'aria-label="Show screenshot {number}" data-width="{width}" data-height="{height}">'
        f'<img src="shots/{esc(name)}" alt="" width="{width}" height="{height}"></a></li>'
        for number, (name, (width, height)) in enumerate(zip(shots, sizes), 1)
    )
    collage = f'<ul class="thumbs">{thumbs}</ul>' if len(shots) > 1 else ""
    single = "" if collage else " single"
    return f"""<section class="gallery{single}" aria-label="Screenshots">
    <div class="stage"><img src="shots/{esc(shots[0])}" alt="{esc(app['name'])} screenshot" width="{sizes[0][0]}" height="{sizes[0][1]}"></div>
    {collage}
  </section>"""


def app_page(app):
    features = "".join(
        f'<li><h3>{esc(f["title"])}</h3><p>{esc(f["text"])}</p></li>' for f in app["features"]
    )
    sections = []
    for key, heading, tag in (("setup", "Getting started", "ol"), ("limits", "Good to know", "ul")):
        if app.get(key):
            items = "".join(f"<li>{esc(item)}</li>" for item in app[key])
            sections.append(f"<section><h2>{heading}</h2><{tag} class='steps'>{items}</{tag}></section>")
    hashes = "".join(
        f'<dt>{esc(p["file"])}</dt><dd><code>{p["sha256"]}</code></dd>'
        for p in app["platforms"] if p.get("sha256")
    )
    checksums = f"<details class='sums'><summary>File checksums (SHA-256)</summary><dl>{hashes}</dl></details>" if hashes else ""
    body = f"""<main class="detail" style="--accent:{esc(app['accent'])}">
  <a class="back" href="../">← All apps</a>
  <section class="hero">
    <img src="{esc(app['icon'])}" alt="" width="144" height="144">
    <div>
      <h1>{esc(app['name'])}</h1>
      <p class="line">{esc(app['tagline'])}</p>
      <p class="meta">Version {esc(app['version'])} · Updated {esc(format_date(app['updated']))}</p>
    </div>
  </section>
  <section class="downloads" aria-label="Downloads">{''.join(download(p) for p in app['platforms'])}</section>
  {gallery(app)}
  <p class="about">{esc(app['description'])}</p>
  <section><h2>What it does</h2><ul class="features">{features}</ul></section>
  {''.join(sections)}
  {checksums}
</main>"""
    url = f"{SITE_URL}{app['slug']}/"
    image = f"{url}{app['icon']}" if not app["icon"].endswith(".svg") else None
    return page(f"{app['name']} · {SITE_NAME}", app["tagline"], body, base="../", image=image, url=url)


def build(_args=None):
    apps = load_apps()
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    (OUT / "index.html").write_text(home(apps))
    for app in apps:
        folder = OUT / app["slug"]
        folder.mkdir()
        shutil.copy(APPS / app["slug"] / app["icon"], folder)
        if (APPS / app["slug"] / "shots").is_dir():
            shutil.copytree(APPS / app["slug"] / "shots", folder / "shots")
        (folder / "index.html").write_text(app_page(app))
    missing = page(
        f"Page not found · {SITE_NAME}", "This page does not exist.",
        f'<main class="intro"><h1>Nothing here.</h1><p><a href="{SITE_URL}">Back to all apps</a></p></main>',
    )
    (OUT / "404.html").write_text(missing)
    (OUT / ".nojekyll").touch()
    print(f"Built {len(apps)} apps into {OUT}")


def serve(_args):
    build()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
    print("Preview at http://localhost:8000")
    http.server.ThreadingHTTPServer(("127.0.0.1", 8000), handler).serve_forever()


def new(args):
    if not re.fullmatch(r"[a-z0-9-]+", args.slug):
        sys.exit("Use lowercase letters, numbers and dashes for the folder name.")
    folder = APPS / args.slug
    if folder.exists():
        sys.exit(f"{folder} already exists.")
    folder.mkdir(parents=True)
    today = datetime.date.today().isoformat()
    app = {
        "name": args.name,
        "tagline": "One sentence on what it does.",
        "description": "A short paragraph for the app's page.",
        "version": "1.0",
        "updated": today,
        "accent": "#3b5bdb",
        "platforms": [{"id": "android", "requires": "Android 11 or later"}],
        "features": [{"title": "Main feature", "text": "What it does for you."}],
        "setup": [],
        "limits": [],
    }
    (folder / "app.json").write_text(json.dumps(app, indent=2) + "\n")
    print(f"Created {folder}/app.json. Add an icon.png or icon.svg next to it, then edit the text.")


def run(*command, check=True):
    return subprocess.run(command, cwd=ROOT, check=check, capture_output=True, text=True)


def release(args):
    if args.platform not in PLATFORM_LABELS:
        sys.exit(f"Platform must be one of: {', '.join(PLATFORM_LABELS)}")
    path = APPS / args.slug / "app.json"
    source = pathlib.Path(args.file).expanduser().resolve()
    app = json.loads(path.read_text())
    app["version"] = args.version or app["version"]
    tag = f"{args.slug}-v{app['version']}"
    label = re.sub(r"[^A-Za-z0-9]", "", app.get("file_label", app["name"]))
    name = f"{label}-{app['version']}-{args.platform}{source.suffix}"
    staged = OUT.parent / ".upload" / name
    staged.parent.mkdir(exist_ok=True)
    shutil.copy(source, staged)

    if run("gh", "release", "view", tag, "--repo", REPO, check=False).returncode != 0:
        run("gh", "release", "create", tag, "--repo", REPO, "--title", f"{app['name']} {app['version']}", "--notes", "")
    run("gh", "release", "upload", tag, str(staged), "--repo", REPO, "--clobber")
    shutil.rmtree(staged.parent)

    platform = next((p for p in app["platforms"] if p["id"] == args.platform), None)
    if platform is None:
        platform = {"id": args.platform}
        app["platforms"].append(platform)
    platform.update(
        url=f"https://github.com/{REPO}/releases/download/{tag}/{name}",
        file=name,
        size=source.stat().st_size,
        sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    )
    app["updated"] = datetime.date.today().isoformat()
    path.write_text(json.dumps(app, indent=2, ensure_ascii=False) + "\n")
    print(f"Uploaded {name}")

    if not args.no_push:
        run("git", "add", str(path))
        run("git", "commit", "-m", f"Release {app['name']} {app['version']} for {PLATFORM_LABELS[args.platform]}")
        run("git", "push")
        print("Pushed. The site updates in about a minute.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build").set_defaults(run=build)
    commands.add_parser("serve").set_defaults(run=serve)
    new_parser = commands.add_parser("new")
    new_parser.add_argument("slug")
    new_parser.add_argument("name")
    new_parser.set_defaults(run=new)
    release_parser = commands.add_parser("release")
    release_parser.add_argument("slug")
    release_parser.add_argument("platform")
    release_parser.add_argument("file")
    release_parser.add_argument("--version")
    release_parser.add_argument("--no-push", action="store_true", help="Update app.json without committing")
    release_parser.set_defaults(run=release)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
