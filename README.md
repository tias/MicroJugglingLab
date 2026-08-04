# MicroJugglingLab (Fri3d Badge 2026)

**MicroJugglingLab** — animated juggling lessons for [MicroPythonOS](https://micropythonos.com/) on the Fri3d Camp 2026 badge. Lesson order and siteswaps follow [Juggling Lab](https://jugglinglab.org/)’s `basic_how to.jml` beginner list. This is a small MicroPython app with a lightweight siteswap animator — not a port of the full Juggling Lab engine.

Upstream Juggling Lab (Kotlin) lives in `jugglinglab/` for reference only. Desktop OS checkout lives in `MicroPythonOS/` (gitignored).

## App

```
org.microjugglinglab.solo/
├── MANIFEST.JSON
├── icon_64x64.png
├── main.py          # main menu (language + sections)
├── section.py       # lessons in one section
├── animate.py       # live animation
├── engine.py        # siteswap → ball positions
├── ui.py            # shared chrome (tabs / title / panel)
├── i18n.py          # NL | FR | EN strings + prefs
└── lessons.py       # curriculum
```

- Main menu with language switch **NL | FR | EN** (default EN), then a lesson track
- **3-cascade**, **3-Ball Tricks**, **4-fountain**, and **5-cascade** patterns
- Play / pause, ± playback speed, back
- Designed for ~320×240 touch UI

## Run locally (desktop)

No badge required. From this repo root:

```bash
./run_desktop.sh
```

This uses the in-repo `MicroPythonOS/` tree, symlinks `org.microjugglinglab.solo/` into its apps folder, and launches the app in an SDL window.

```bash
./run_desktop.sh --launcher          # OS launcher only
MPOS_ROOT=/other/MicroPythonOS ./run_desktop.sh   # override path
```

Edit files under `org.microjugglinglab.solo/`, then run `./run_desktop.sh` again to reload.

### One-time setup of `MicroPythonOS/`

```bash
git clone --recurse-submodules --depth 1 --shallow-submodules \
  https://github.com/MicroPythonOS/MicroPythonOS.git MicroPythonOS

# Download desktop binary from
#   https://github.com/MicroPythonOS/MicroPythonOS/releases
# Linux x64 example:
mkdir -p MicroPythonOS/lvgl_micropython/build
cp ~/Downloads/MicroPythonOS_x64_linux_*.elf \
  MicroPythonOS/lvgl_micropython/build/lvgl_micropy_unix
chmod +x MicroPythonOS/lvgl_micropython/build/lvgl_micropy_unix

./run_desktop.sh
```

Docs: [Running on desktop](https://docs.micropythonos.com/os-development/running-on-desktop/).

## Install on the badge (`mpremote`)

```bash
mpremote connect /dev/ttyACM0 cp -r org.microjugglinglab.solo/ :/apps/
mpremote connect /dev/ttyACM0 exec "from mpos import AppManager; AppManager.refresh_apps()"
mpremote connect /dev/ttyACM0 exec "from mpos import AppManager; AppManager.start_app('org.microjugglinglab.solo')"
```

Use your serial device if it is not `/dev/ttyACM0`. On Linux, your user usually needs to be in the `dialout` group.

## Bundle `.mpk` and publish on BadgeHub

```bash
chmod +x bundle_mpk.sh
./bundle_mpk.sh
# → dist/org.microjugglinglab.solo_0.2.0.mpk
```

Then on [badgehub.eu](https://badgehub.eu):

1. Create a project (once); set badge to **`mpos_api_0`** (MicroPythonOS).
2. Upload the `.mpk` as a release; version must match `MANIFEST.JSON`.
3. Refresh AppStore on the badge and install over Wi‑Fi.

Details: [Bundling Apps](https://docs.micropythonos.com/apps/bundling-apps/), [BadgeHub](https://docs.micropythonos.com/apps/badgehub/).

## Attribution

The MicroPythonOS app in `org.microjugglinglab.solo/` is based on [Juggling Lab](https://jugglinglab.org/) by Jack Boyce and contributors. Its How to Juggle lessons and siteswap strings come from `patterns/basic_how to.jml`; the animator was designed with reference to Juggling Lab’s GPL sources. This is a new MicroPython/LVGL implementation for the Fri3d Badge (not a port of the full Kotlin engine). Licensed under GPL-2.0, the same as Juggling Lab.

## License

- `jugglinglab/` — GPL-2.0 (upstream)
- `org.microjugglinglab.solo/` — GPL-2.0 (see `org.microjugglinglab.solo/LICENSE`)
