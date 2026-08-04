# MicroPythonOS — Juggle How-To (Fri3d Badge 2026)

Animated **How to Juggle** lessons for [MicroPythonOS](https://micropythonos.com/) on the Fri3d Camp 2026 badge. Lesson order and siteswaps follow [Juggling Lab](https://jugglinglab.org/)’s `basic_how to.jml` beginner list. This is a small MicroPython app with a lightweight siteswap animator — not a port of the full Juggling Lab engine.

Upstream Juggling Lab (Kotlin) lives in `jugglinglab/` for reference only.

## App

```
org.jugglinglab.howto/
├── MANIFEST.JSON
├── icon_64x64.png
├── main.py          # lesson list (launcher)
├── animate.py       # live animation
├── engine.py        # siteswap → ball positions
└── lessons.py       # curriculum
```

- **3-cascade**, **4-fountain**, and **5-cascade** step-by-step patterns
- Play / pause, ± speed, back
- Designed for ~320×240 touch UI

## Install on the badge (`mpremote`)

```bash
mpremote connect /dev/ttyACM0 cp -r org.jugglinglab.howto/ :/apps/
mpremote connect /dev/ttyACM0 exec "from mpos import AppManager; AppManager.refresh_apps()"
mpremote connect /dev/ttyACM0 exec "from mpos import AppManager; AppManager.start_app('org.jugglinglab.howto')"
```

Use your serial device if it is not `/dev/ttyACM0`. On Linux, your user usually needs to be in the `dialout` group.

## Optional: test on desktop MicroPythonOS

If you have a [MicroPythonOS desktop](https://docs.micropythonos.com/os-development/running-on-desktop/) checkout:

```bash
# from your MicroPythonOS tree
ln -s /path/to/mps_juggling_lab/org.jugglinglab.howto internal_filesystem/apps/org.jugglinglab.howto
./scripts/run_desktop.sh
```

Open **Juggle How-To** from the launcher. Edit the app files and restart the desktop OS to iterate. Still smoke-test on the real badge before publishing — timing and layout are tuned for 320×240.

## Bundle `.mpk` and publish on BadgeHub

```bash
chmod +x scripts/bundle_mpk.sh
./scripts/bundle_mpk.sh
# → dist/org.jugglinglab.howto_0.1.0.mpk
```

Then on [badgehub.eu](https://badgehub.eu):

1. Create a project (once); set badge to **`mpos_api_0`** (MicroPythonOS).
2. Upload the `.mpk` as a release; version must match `MANIFEST.JSON`.
3. Refresh AppStore on the badge and install over Wi‑Fi.

Details: [Bundling Apps](https://docs.micropythonos.com/apps/bundling-apps/), [BadgeHub](https://docs.micropythonos.com/apps/badgehub/).

## Attribution

The MicroPythonOS app in `org.jugglinglab.howto/` is based on [Juggling Lab](https://jugglinglab.org/) by Jack Boyce and contributors. Its How to Juggle lessons and siteswap strings come from `patterns/basic_how to.jml`; the animator was designed with reference to Juggling Lab’s GPL sources. This is a new MicroPython/LVGL implementation for the Fri3d Badge (not a port of the full Kotlin engine). Licensed under GPL-2.0, the same as Juggling Lab.

## License

- `jugglinglab/` — GPL-2.0 (upstream)
- `org.jugglinglab.howto/` — GPL-2.0 (see `org.jugglinglab.howto/LICENSE`)
