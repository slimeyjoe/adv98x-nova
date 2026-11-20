# SPDX-License-Identifier: GPL-3.0-or-later
"""NOVA ～魅入られた肢体～ (Cat's Pro, 1993) for the Adv98X engine: the game's description.

The engine's tools read this file (they find a game by it: the engine's source/tools/gamedir.py).
It is data, in Python's syntax: what the pack takes from which of the player's files, and the
original files the engine's research tools and tests work on. Paths are inside a release of
resources/inventory.tsv, as `gamedata.py import` puts them under resources/original/<release>/.
"""
import os
import struct

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
    'songs': {'release': 'pc98', 'kind': 'music', 'prefix': 'A/MUS/'},
    'click_maps': {'release': 'pc98', 'kind': 'map hit table', 'prefix': 'A/CLM/'},
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
    # the plug-ins (.TCM), which the engine replaces with native modules
    'plugins': {'release': 'pc98', 'kind': 'plug-in code', 'prefix': 'A/'},
    # other executables `gamedata.py derive` unpacks for the research
    'unpack': ('A/INSTH.EXE',),
}


# ---- the import -------------------------------------------------------------------------------
# The engine's source/tools/gamedata.py runs lrvne's import framework (lrvne's tools/lrvne/
# inventory.py) with these hooks. Releases (the inventory's first column):
#   pc98   the four 2HD floppies of 1993-05-28, kept per disk (pc98/A/..., pc98/B/GPC/...): the
#          same name can hold different data on different disks
#   win    members of the Windows 1996 EVE.PCK (research only; optional)
#   en     the scripts of the English translation by Fuzion (the files that differ; optional)
# A file is recognised by name + md5 wherever it is found, so a hard-disk install of the
# Japanese release supplies the pc98 rows too. The dumped copy's own state (its saves and the
# player's name, never packed) is optional: the tests that need it are skipped without it.

FLOPPY_LABEL = 'NOVA____98'     # volume labels NOVA____98A .. D


# the Windows release's archive ("PCK Version 1.00")

def _rol_words(b):
    o = bytearray(len(b))
    for i in range(0, len(b) & ~1, 2):
        w = b[i] | b[i + 1] << 8
        w = (w << 1 | w >> 15) & 0xFFFF
        o[i], o[i + 1] = w & 255, w >> 8
    return bytes(o)


def is_pck(d):
    return len(d) >= 0x4000 and _rol_words(d[:16]) == b'PCK Version 1.00'


def pck_members(d):
    """(name, data) of every member. The first 0x4000 bytes (header + 511 entries of 32 bytes)
    are stored with every 16-bit word rotated right by one bit; member data is plain."""
    head = _rol_words(d[:0x4000])
    for p in range(0x20, 0x4000, 32):
        name = head[p:p + 16].split(b'\0')[0].strip()
        if not name:            # a free slot, or the entry after the last member
            continue
        off, size = struct.unpack_from('<II', head, p + 16)
        yield name.decode('ascii'), d[off:off + size]


def read_pck(data):
    """The archive as lrvne's sources read one of a game's own format: its members, or None
    when the file is not a PCK archive."""
    return list(pck_members(data)) if is_pck(data) else None


# scan (maintenance: rows for what a source holds)

def kind_of(path):
    ext = os.path.splitext(path)[1].upper()
    return {'.MES': 'script', '.GPC': 'image', '.USO': 'music', '.TCM': 'plug-in code',
            '.CLM': 'map hit table', '.PI': 'image (Pi)', '.EVE': 'script (EVE)',
            '.WAV': 'sound effect', '.CDF': 'map hit table', '.OVL': 'engine', '.OV1': 'engine',
            '.COM': 'engine loader', '.INI': 'engine start script', '.EXE': 'installer',
            '.SYS': 'boot', '.DEF': 'default name'}.get(ext, 'save' if 'FLAG' in path.upper() else 'other')


def scan_row(entry, _data):
    label = entry.volume_label
    if label.startswith(FLOPPY_LABEL):
        release, path = 'pc98', label[-1] + '/' + entry.inner_path
    elif entry.kind == 'container':
        release, path = 'win', entry.inner_path
    else:
        release, path = os.environ.get('SCAN_RELEASE', 'en'), entry.inner_path
    return {'path': path, 'release': release, 'mtime': entry.mtime, 'kind': kind_of(path)}


# lrvne's inventory.Hooks
IMPORT = {
    'dest_path': lambda row: row.get('release') + '/' + row.name,
    'required': lambda row: row.get('release') == 'pc98' and 'never packed' not in row.get('kind'),
    'group': lambda row: row.get('release'),
    'scan_row': scan_row,
    'containers': {'.pck': read_pck},
}
