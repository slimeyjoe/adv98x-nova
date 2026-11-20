# SPDX-License-Identifier: GPL-3.0-or-later
"""NOVA ～魅入られた肢体～ (Cat's Pro, 1993) for the Adv98X engine: the game's description.

The engine's tools read this file (they find a game by it: the engine's source/tools/gamedir.py).
It is data, in Python's syntax: what the pack takes from which of the player's files, and the
original files the engine's research tools and tests work on. Paths are inside a release of
resources/inventory.tsv, as `gamedata.py import` puts them under resources/original/<release>/.
"""

# What makes the engine run this game: the pack's profile (the engine's engine/game/profile.c
# has the keys). The id names the saves' directory; `start` is the script the game's start file
# (NV.INI) runs, as that file names it; `modules` the plug-ins the game loads, which the engine
# provides natively.
PROFILE = {
    'id': 'nova',
    'title': 'NOVA ～魅入られた肢体～',
    'lang': 'ja',
    'modules': 'CHGFONTH,PALCH,WHITEH,INPUTNAM,ACTE1',
    'start': '\\MES\\RUN.MES',
}

# What the pack holds (the engine's source/tools/mkpack.py). A part takes the inventory's rows
# of a release and kind whose path starts with `prefix` (and ends with `suffix`).
PACK = {
    # the backend takes <program>.pak, else the only .pak next to the program
    'name': 'nova.pak',
    # the original's language first
    'languages': ('ja', 'en'),
    # every picture once, under its name: the four disks hold copies; where copies of a name
    # differ, `choice` names the disk (the path's first directory) taken (docs/re/disks.md §4)
    'pictures': {'release': 'pc98', 'kind': 'image', 'suffix': '.GPC',
                 'choice': {'NV43A': 'B'}},
    'songs': {'release': 'pc98', 'kind': 'music', 'prefix': 'A/'},
    'click_maps': {'release': 'pc98', 'kind': 'map hit table', 'prefix': 'A/'},
    # the scripts per language; a language with `fallback` takes that language's script where
    # it has none of its own (Fuzion's translation replaces 117 of the 118)
    'scripts': {
        'ja': {'release': 'pc98', 'kind': 'script', 'prefix': 'A/MES/'},
        'en': {'release': 'en', 'kind': 'script', 'prefix': 'MES/', 'fallback': 'ja'},
    },
    # the interpreter's three built-in messages (save failed, nothing saved there, load failed)
    # in the languages other than the original's, which has the interpreter's own
    'messages': {
        'en': ('Could not save.', 'Nothing is saved there.', 'Could not load.'),
    },
}

# The original program, as the player's copy has it.
ORIGINAL = {
    'release': 'pc98',
    # NV.OVL: the built-in messages, as script fragments (docs/re/interpreter.md)
    'interpreter': {'path': 'A/NV.OVL', 'messages_at': (0xD95B, 0xD9E3)},
    # NV.OV1, AdvBIOS: the default mouse pointer (01AB:09D8; docs/re/advbios.md §6.2)
    'bios': {'path': 'A/NV.OV1', 'cursor_at': 0x1AB0 + 0x9D8},
    # NV.INI, the start file
    'start': {'path': 'A/NV.INI'},
}
