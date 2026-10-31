# Ayaz Apps

Live at https://yzqhrmn.github.io/apps/. Every push to `main` rebuilds the site.

Each app is a folder in `apps/` holding `app.json`, an `icon.png` or `icon.svg`, and
optional screenshots as `shots/*.jpg`, shown in filename order.
Installers live on GitHub Releases, so the repository stays small.

## Add an app

```bash
python3 site.py new my-app "My App"
```

Edit `apps/my-app/app.json`, add an icon, then commit and push.

## Publish an installer

```bash
python3 site.py release my-app android path/to/app.apk
```

The platform is `android`, `ios`, `mac`, `windows` or `web`. Add `--version 1.1` for a new
version. This uploads the file, records its size and checksum, and pushes the change.

## Preview locally

```bash
python3 site.py serve
```
