# How to Juggle curriculum — mirrored from Juggling Lab basic_how to.jml
# Strings are {nl, fr, en}; siteswaps stay shared.

from i18n import pick, get_lang

SECTIONS = [
    {
        "id": "cascade3",
        "title_key": "section_cascade3",
        "title": {
            "nl": "3-cascade stap voor stap",
            "fr": "Cascade a 3 pas a pas",
            "en": "3-Cascade Step By Step",
        },
        "lessons": [
            {
                "name": {
                    "nl": "1 bal uit een 3-cascade",
                    "fr": "1 balle d'une cascade a 3",
                    "en": "1 Ball out of a 3-Cascade",
                },
                "pattern": "300",
                "bps": 3.0,
                "tip": {
                    "nl": "Gooi van rechts naar links, dan pauze. Zelfde worp, andere hand.",
                    "fr": "Lance de la droite vers la gauche, puis pause. Meme lancer, autre main.",
                    "en": "Throw from right to left, then pause. Same throw, other hand.",
                },
            },
            {
                "name": {
                    "nl": "Twee keer gooien",
                    "fr": "Lancer deux fois",
                    "en": "Throw Twice",
                },
                "pattern": "33022",
                "bps": 3.0,
                "tip": {
                    "nl": "Twee worpen, dan rust. Voel het ritme.",
                    "fr": "Deux lancers, puis repos. Sens le rythme.",
                    "en": "Two throws, then rest. Feel the rhythm.",
                },
            },
            {
                "name": {
                    "nl": "2 ballen uit een 3-cascade",
                    "fr": "2 balles d'une cascade a 3",
                    "en": "2 Balls out of a 3-Cascade",
                },
                "pattern": "330",
                "bps": 3.0,
                "tip": {
                    "nl": "Wissel: gooi, gooi dan de andere bal eronderdoor.",
                    "fr": "Echange: lance, puis lance l'autre balle en dessous.",
                    "en": "Exchange: throw, then throw the other ball under it.",
                },
            },
            {
                "name": {
                    "nl": "Drie keer gooien",
                    "fr": "Lancer trois fois",
                    "en": "Throw 3 Times",
                },
                "pattern": "[32]3322",
                "bps": 3.0,
                "tip": {
                    "nl": "Begin met een multiplex, dan drie cascade-worpen.",
                    "fr": "Commence par un multiplex, puis trois lancers en cascade.",
                    "en": "Start with a multiplex, then three cascade throws.",
                },
            },
            {
                "name": {
                    "nl": "3-cascade",
                    "fr": "Cascade a 3",
                    "en": "3-Cascade",
                },
                "pattern": "3",
                "bps": 3.0,
                "tip": {
                    "nl": "De klassieker: gooi altijd naar de lege hand.",
                    "fr": "Le classique: lance toujours vers la main vide.",
                    "en": "The classic: always throw to the empty hand.",
                },
            },
            {
                "name": {
                    "nl": "Langzamere 3-cascade",
                    "fr": "Cascade a 3 plus lente",
                    "en": "Slower 3-Cascade",
                },
                "pattern": "3",
                "bps": 2.2,
                "tip": {
                    "nl": "Zelfde patroon, trager - let op de bogen.",
                    "fr": "Meme figure, plus lent - regarde les arcs.",
                    "en": "Same pattern, slower - watch the peaks.",
                },
            },
        ],
    },
    {
        "id": "fountain4",
        "title_key": "section_fountain4",
        "title": {
            "nl": "4-fontein stap voor stap",
            "fr": "Fontaine a 4 pas a pas",
            "en": "4-Fountain Step By Step",
        },
        "lessons": [
            {
                "name": {
                    "nl": "2 in een hand",
                    "fr": "2 dans une main",
                    "en": "2 in One Hand",
                },
                "pattern": "40",
                "bps": 3.8,
                "tip": {
                    "nl": "Twee ballen alleen in de rechterhand (kolommen).",
                    "fr": "Deux balles dans la main droite seulement (colonnes).",
                    "en": "Two balls in the right hand only (columns).",
                },
            },
            {
                "name": {
                    "nl": "4-synchrone fontein",
                    "fr": "Fontaine synchrone a 4",
                    "en": "4-Synchronous Fountain",
                },
                "pattern": "(4,4)",
                "bps": 3.8,
                "tip": {
                    "nl": "Beide handen gooien samen; ballen blijven aan hun kant.",
                    "fr": "Les deux mains lancent ensemble; les balles restent de leur cote.",
                    "en": "Both hands throw together; balls stay on their side.",
                },
            },
            {
                "name": {
                    "nl": "4-fontein",
                    "fr": "Fontaine a 4",
                    "en": "4-Fountain",
                },
                "pattern": "4",
                "bps": 3.8,
                "tip": {
                    "nl": "Async fontein: even worpen, kolommen in dezelfde hand.",
                    "fr": "Fontaine async: lancers pairs, colonnes dans la meme main.",
                    "en": "Async fountain: even throws, same-hand columns.",
                },
            },
        ],
    },
    {
        "id": "cascade5",
        "title_key": "section_cascade5",
        "title": {
            "nl": "5-cascade stap voor stap",
            "fr": "Cascade a 5 pas a pas",
            "en": "5-Cascade Step By Step",
        },
        "lessons": [
            {
                "name": {
                    "nl": "2 ballen uit een 5-cascade",
                    "fr": "2 balles d'une cascade a 5",
                    "en": "2 Balls out of a 5-Cascade",
                },
                "pattern": "50500",
                "bps": 4.6,
                "tip": {
                    "nl": "Hoge worpen met pauzes - leer de 5-timing.",
                    "fr": "Lancers hauts avec pauses - apprends le rythme du 5.",
                    "en": "High throws with pauses - learn the 5 timing.",
                },
            },
            {
                "name": {
                    "nl": "Baby-jongleren",
                    "fr": "Jonglage bebe",
                    "en": "Baby Juggling",
                },
                "pattern": "52512",
                "bps": 4.6,
                "tip": {
                    "nl": "Drie ballen met 5-cascade-ritme (vereenvoudigd).",
                    "fr": "Trois balles au rythme de la cascade a 5 (simplifie).",
                    "en": "Three balls with 5-cascade rhythm (simplified).",
                },
            },
            {
                "name": {
                    "nl": "Chase",
                    "fr": "Chase",
                    "en": "Chase",
                },
                "pattern": "50505",
                "bps": 4.6,
                "tip": {
                    "nl": "Afwisselend 5-worpen en holds.",
                    "fr": "Alternance de 5 et de holds.",
                    "en": "Alternating 5s and holds.",
                },
            },
            {
                "name": {
                    "nl": "Flash",
                    "fr": "Flash",
                    "en": "Flash",
                },
                "pattern": "55500",
                "bps": 4.6,
                "tip": {
                    "nl": "Drie hoge worpen, dan twee lege beats.",
                    "fr": "Trois lancers hauts, puis deux temps vides.",
                    "en": "Three high throws, then two empty beats.",
                },
            },
            {
                "name": {
                    "nl": "4 van de 5 gooien",
                    "fr": "Lancer 4 sur 5",
                    "en": "Throw 4 out of 5",
                },
                "pattern": "[52][52]55022[22][22]",
                "bps": 2.5,
                "tip": {
                    "nl": "Vier props richting een 5-cascade (vereenvoudigd).",
                    "fr": "Quatre objets vers une cascade a 5 (simplifie).",
                    "en": "Four props toward a 5-cascade (simplified).",
                },
            },
            {
                "name": {
                    "nl": "4 ballen uit een 5-cascade",
                    "fr": "4 balles d'une cascade a 5",
                    "en": "4 Balls out of a 5-Cascade",
                },
                "pattern": "55550",
                "bps": 4.6,
                "tip": {
                    "nl": "Bijna klaar - vier ballen in 5-cascade-slots.",
                    "fr": "Presque - quatre balles dans les creneaux du 5.",
                    "en": "Almost there - four balls in 5-cascade slots.",
                },
            },
            {
                "name": {
                    "nl": "552",
                    "fr": "552",
                    "en": "552",
                },
                "pattern": "552",
                "bps": 4.6,
                "tip": {
                    "nl": "Bekend opstapje naar 5 ballen.",
                    "fr": "Figure courante pour preparer le 5.",
                    "en": "Common 5-ball lead-in pattern.",
                },
            },
            {
                "name": {
                    "nl": "5551",
                    "fr": "5551",
                    "en": "5551",
                },
                "pattern": "5551",
                "bps": 4.6,
                "tip": {
                    "nl": "Vier worpen en een hold - brug naar de cascade.",
                    "fr": "Quatre lancers puis un hold - pont vers la cascade.",
                    "en": "Four throws then a hold - bridge to the cascade.",
                },
            },
            {
                "name": {
                    "nl": "5-cascade",
                    "fr": "Cascade a 5",
                    "en": "5-Cascade",
                },
                "pattern": "5",
                "bps": 4.6,
                "tip": {
                    "nl": "Cascade met vijf ballen. Zelfde idee als 3, hogere worpen.",
                    "fr": "Cascade a cinq. Meme idee que le 3, lancers plus hauts.",
                    "en": "Five-ball cascade. Same idea as 3, higher throws.",
                },
            },
        ],
    },
]


def get_section(section_id):
    for section in SECTIONS:
        if section["id"] == section_id:
            return section
    return None


def localize_lesson(lesson, lang=None):
    """Return a shallow copy with name/tip resolved for lang."""
    if lang is None:
        lang = get_lang()
    return {
        "name": pick(lesson.get("name"), lang),
        "tip": pick(lesson.get("tip"), lang),
        "pattern": lesson.get("pattern"),
        "bps": lesson.get("bps", 3.0),
    }


def localize_section_title(section, lang=None):
    if lang is None:
        lang = get_lang()
    return pick(section.get("title"), lang)
