# UI chrome strings and language prefs (NL | FR | EN; default EN).

try:
    import ujson as json
except ImportError:
    import json

import os

# Button order on the main menu (left → right)
LANGS = ("nl", "fr", "en")
LANG_LABELS = {"nl": "NL", "fr": "FR", "en": "EN"}
DEFAULT_LANG = "en"

_PREF_CANDIDATES = (
    "apps/org.jugglinglab.howto/lang.json",
    "/apps/org.jugglinglab.howto/lang.json",
    "lang.json",
)

_current = None

STRINGS = {
    "app_title": {
        "nl": "Leer jongleren",
        "fr": "Apprendre a jongler",
        "en": "How to Juggle",
    },
    "tagline": {
        "nl": "Kies een taal en een lesreeks",
        "fr": "Choisis une langue et une serie",
        "en": "Pick a language and a lesson track",
    },
    "section_cascade3": {
        "nl": "3-cascade stap voor stap",
        "fr": "Cascade a 3 pas a pas",
        "en": "3-Cascade Step By Step",
    },
    "section_fountain4": {
        "nl": "4-fontein stap voor stap",
        "fr": "Fontaine a 4 pas a pas",
        "en": "4-Fountain Step By Step",
    },
    "section_cascade5": {
        "nl": "5-cascade stap voor stap",
        "fr": "Cascade a 5 pas a pas",
        "en": "5-Cascade Step By Step",
    },
    "back": {
        "nl": "Terug",
        "fr": "Retour",
        "en": "Back",
    },
    "pause": {
        "nl": "Pauze",
        "fr": "Pause",
        "en": "Pause",
    },
    "play": {
        "nl": "Speel",
        "fr": "Lecture",
        "en": "Play",
    },
    "lessons_header": {
        "nl": "Lessen",
        "fr": "Lecons",
        "en": "Lessons",
    },
}


def normalize_lang(lang):
    if lang in LANGS:
        return lang
    return DEFAULT_LANG


def _pref_path_existing():
    for path in _PREF_CANDIDATES:
        try:
            os.stat(path)
            return path
        except OSError:
            continue
    return None


def _pref_path_writable():
    existing = _pref_path_existing()
    if existing:
        return existing
    # Prefer app folder when present
    for path in _PREF_CANDIDATES:
        parent = path.rsplit("/", 1)[0] if "/" in path else "."
        try:
            if parent in (".", ""):
                return path
            os.stat(parent)
            return path
        except OSError:
            continue
    return "lang.json"


def load_lang():
    global _current
    if _current is not None:
        return _current
    path = _pref_path_existing()
    if path:
        try:
            with open(path, "r") as f:
                data = json.loads(f.read())
            _current = normalize_lang(data.get("lang"))
            return _current
        except (OSError, ValueError, TypeError, KeyError):
            pass
    _current = DEFAULT_LANG
    return _current


def save_lang(lang):
    global _current
    lang = normalize_lang(lang)
    _current = lang
    path = _pref_path_writable()
    try:
        with open(path, "w") as f:
            f.write(json.dumps({"lang": lang}))
    except OSError:
        pass
    return lang


def set_lang(lang):
    return save_lang(lang)


def get_lang():
    return load_lang()


def t(key, lang=None):
    """Translate a chrome string key."""
    if lang is None:
        lang = get_lang()
    lang = normalize_lang(lang)
    entry = STRINGS.get(key)
    if not entry:
        return key
    if isinstance(entry, str):
        return entry
    return entry.get(lang) or entry.get(DEFAULT_LANG) or key


def pick(field, lang=None):
    """Pick a localized field from a str or {lang: str} map."""
    if lang is None:
        lang = get_lang()
    lang = normalize_lang(lang)
    if field is None:
        return ""
    if isinstance(field, str):
        return field
    return field.get(lang) or field.get(DEFAULT_LANG) or ""
