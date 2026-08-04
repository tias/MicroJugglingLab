# How to Juggle curriculum — mirrored from Juggling Lab basic_how to.jml
# JML-only lessons use their base siteswap so they animate on-device.

SECTIONS = [
    {
        "title": "3-Cascade Step By Step",
        "lessons": [
            {
                "name": "1 Ball out of a 3-Cascade",
                "pattern": "300",
                "bps": 3.0,
                "tip": "Throw from right to left, then pause. Same throw, other hand.",
            },
            {
                "name": "Throw Twice",
                "pattern": "33022",
                "bps": 3.0,
                "tip": "Two throws, then rest. Feel the rhythm.",
            },
            {
                "name": "2 Balls out of a 3-Cascade",
                "pattern": "330",
                "bps": 3.0,
                "tip": "Exchange: throw, then throw the other ball under it.",
            },
            {
                "name": "Throw 3 Times",
                "pattern": "[32]3322",
                "bps": 3.0,
                "tip": "Start with a multiplex, then three cascade throws.",
            },
            {
                "name": "3-Cascade",
                "pattern": "3",
                "bps": 3.0,
                "tip": "The classic: always throw to the empty hand.",
            },
            {
                "name": "Slower 3-Cascade",
                "pattern": "3",
                "bps": 2.0,
                "tip": "Same pattern, slower — watch the peaks.",
            },
        ],
    },
    {
        "title": "4-Fountain Step By Step",
        "lessons": [
            {
                "name": "2 in One Hand",
                "pattern": "40",
                "bps": 3.0,
                "tip": "Two balls in the right hand only (columns).",
            },
            {
                "name": "4-Synchronous Fountain",
                "pattern": "(4,4)",
                "bps": 3.0,
                "tip": "Both hands throw together; balls stay on their side.",
            },
            {
                "name": "4-Fountain",
                "pattern": "4",
                "bps": 3.0,
                "tip": "Async fountain: even throws, same-hand columns.",
            },
        ],
    },
    {
        "title": "5-Cascade Step By Step",
        "lessons": [
            {
                "name": "2 Balls out of a 5-Cascade",
                "pattern": "50500",
                "bps": 3.0,
                "tip": "High throws with pauses — learn the 5 timing.",
            },
            {
                "name": "Baby Juggling",
                "pattern": "52512",
                "bps": 3.0,
                "tip": "Three balls with 5-cascade rhythm (simplified).",
            },
            {
                "name": "Chase",
                "pattern": "50505",
                "bps": 3.0,
                "tip": "Alternating 5s and holds.",
            },
            {
                "name": "Flash",
                "pattern": "55500",
                "bps": 3.0,
                "tip": "Three high throws, then two empty beats.",
            },
            {
                "name": "Throw 4 out of 5",
                "pattern": "[52][52]55022[22][22]",
                "bps": 2.5,
                "tip": "Four props toward a 5-cascade (simplified).",
            },
            {
                "name": "4 Balls out of a 5-Cascade",
                "pattern": "55550",
                "bps": 3.0,
                "tip": "Almost there — four balls in 5-cascade slots.",
            },
            {
                "name": "552",
                "pattern": "552",
                "bps": 3.0,
                "tip": "Common 5-ball lead-in pattern.",
            },
            {
                "name": "5551",
                "pattern": "5551",
                "bps": 3.0,
                "tip": "Four throws then a hold — bridge to the cascade.",
            },
            {
                "name": "5-Cascade",
                "pattern": "5",
                "bps": 3.0,
                "tip": "Five-ball cascade. Same idea as 3, higher throws.",
            },
        ],
    },
]


def iter_lessons():
    """Yield (section_title, lesson_dict) for list building."""
    for section in SECTIONS:
        yield section["title"], None
        for lesson in section["lessons"]:
            yield section["title"], lesson
