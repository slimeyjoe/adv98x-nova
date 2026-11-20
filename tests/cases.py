# SPDX-License-Identifier: GPL-3.0-or-later
"""NOVA's cases for the Adv98X engine's tests: what each of them plays, looks up, draws or hears
on this game. The engine's tests load this file (the engine's source/tools/gamedir.py cases())
and write nothing of the game themselves; casekit is the engine's vocabulary for it.

The references in docs/re/script-catalog.md (§) are this game's.
"""
import glob
import os

from casekit import DOWN, END, RESET, RET, RET_TO_CLICK, RIGHT, click, key, op

# ---- check_vm: the engine against the original interpreter ------------------------------------

# Where the dumped copy keeps its own state (inside resources/original), and those files: saves,
# unlocks and the player's name. They are the test inputs of the scenarios that need saves and
# are never packed; without them those scenarios are skipped.
SAVES_DIR = 'pc98/A'
DUMP_SAVES = ['FLAG0', 'FLAG1', 'FLAG2', 'FLAG3', 'FLAG4', 'FLAG5', 'NAME.DEF']

# name: (language, save files from the dump, keys)
SCENARIOS = {
    # title menu (menu2): 3 x down to "continue", Return, file No1 -> flag-load 0
    'continue': ('ja', DUMP_SAVES, [DOWN] * 3 + [RET, RET] + [RET] * 40),
    # "2nd story": an empty noun list selects at once
    # the 2nd / 3rd story start with name entry: Return alone takes the default name
    'story2': ('ja', DUMP_SAVES, [DOWN, RET] + [RET] * 40),
    'story3': ('ja', DUMP_SAVES, [DOWN, DOWN, RET] + [RET] * 40),
    # a new game on a fresh install; the name typed: a, ｶ, ﾞ, ﾊ, ﾟ, BS, ﾎ, ﾟ, Z, Return
    'newgame': ('ja', [], [RET, key(0x1D, 0x61), key(0x24, 0xB6), key(0x1A, 0xDE), key(0x17, 0xCA),
                           key(0x1B, 0xDF), key(0x0E, 0x08), key(0x2D, 0xCE), key(0x1B, 0xDF),
                           key(0x29, 0x5A), RET] + [RET] * 30),
    # continue, click SAVE on the 2nd-deck map (region 14), file No2 -> flag-save 1
    'save': ('ja', DUMP_SAVES, [DOWN] * 3 + [RET, RET, RET_TO_CLICK, click(550, 243), DOWN, DOWN, RET]
             + [RET] * 10),
    # continue, click a room of the map
    'map_click': ('ja', DUMP_SAVES, [DOWN] * 3 + [RET, RET, RET_TO_CLICK, click(120, 330)]
                  + [RET] * 30),
    'sound': ('ja', DUMP_SAVES, [DOWN] * 4 + [RET] + [DOWN, RET, DOWN, DOWN, RET]),
    'graphic': ('ja', DUMP_SAVES, [DOWN] * 5 + [RET] + [RET] * 12),
    # Sound mode (script-catalog.md §9): every song (verb 0, nouns 0-15), every effect (verb 1,
    # nouns 0-10); a key wait follows each choice
    'sound_all': ('ja', DUMP_SAVES, [DOWN] * 4 + [RET]
                  + [k for n in range(16) for k in [RET] + [RIGHT] * n + [RET, RET]]
                  + [k for n in range(11) for k in [RIGHT, RET] + [RIGHT] * n + [RET, RET]]),
    # Graphic mode: the 45 screens by key (verb 0), then automatically (verb 1, delay 100)
    'graphic_all': ('ja', DUMP_SAVES, [DOWN] * 5 + [RET] + [RET] + [RET] * 45 + [RIGHT, RET]),
    'continue_en': ('en', DUMP_SAVES, [DOWN] * 3 + [RET, RET] + [RET] * 40),
    # the reset button while a song plays in Sound mode, in the game, and in name entry
    'reset_sound': ('ja', DUMP_SAVES, [DOWN] * 4 + [RET, RET, RET, RESET]
                    + [DOWN] * 3 + [RET, RET] + [RET] * 40),
    'reset_game': ('ja', DUMP_SAVES, [DOWN] * 3 + [RET, RET, RET_TO_CLICK, RESET]
                   + [DOWN] * 4 + [RET] + [DOWN, RET, DOWN, DOWN, RET]),
    'reset_name': ('ja', [], [RET, key(0x1D, 0x61), key(0x24, 0xB6), RESET, RET, key(0x29, 0x5A), RET]
                   + [RET] * 30),
}

# Synthetic scenarios: test scripts run in place of the start script on both sides, for what
# NOVA reaches only late in the game. The plug-ins are loaded where NOVA loads them; NV01 is a
# picture with its palette, NV19 one drawn over it.
SHOW_NV01 = op(0xC9, '\\GPC\\NV01.GPC') + op(0xCF, 0, 3)


def palch_script():
    s = op(0xC8, 'PALCH.TCM', 8704) + SHOW_NV01
    s += op(0xCD, 8704, 14, 11, 9, 10, 6)          # NOVA's call: glide colour 14 to A9B
    s += op(0xCD, 8704, 3, 15, 0, 7)               # four arguments: at once
    s += op(0xD1, 2, 7) + op(0xCD, 8704, 5, 0, 15, 15, 1)   # at brightness 7, speed 1
    s += op(0xCD, 8704, 2, 1, 2, 3, 0)             # speed 0
    s += op(0xCD, 8704, 16, 1, 2, 3, 4) + op(0xCD, 8704, 2, 16, 2, 3)    # rejected
    return s + END


def whiteh_script():
    s = op(0xC8, 'WHITEH.TCM', 5376) + SHOW_NV01
    s += op(0xCD, 5376, 1, 8)                      # NOVA's call: to white, 8 frames a step
    s += SHOW_NV01 + op(0xCD, 5376, 0, 3)          # from white to the mailbox (zeros)
    s += SHOW_NV01 + op(0xCD, 5376, 2, 2)          # both, the second half one frame faster
    s += op(0xCD, 5376, 1, 0) + op(0xCD, 5376, 3, 1)     # speed 0; mode 3 rejected
    return s + END


def curtain_script():
    s = SHOW_NV01
    s += op(0xC6, 0, 0, 159, 99, 7)                # MON01: cover everything in colour 7
    s += op(0xC6, 20, 10, 100, 60, 15)             # uncover a part
    s += op(0xC6, 30, 30, 70, 80, 2)               # cover a part in colour 2
    return s + END


def acte1_script():
    def a(cmd):
        return op(0xCD, 256, cmd)
    s = op(0xC8, 'ACTE1.TCM', 256) + a('INIT') + SHOW_NV01
    s += a('COPY 0 10 50 20 40 0 50 200')          # within page 0 (the harness has one page)
    s += a('MOVE 5 100 10 30 8 110')                # overlapping: smears
    s += a('OVER 1,LOAD \\GPC\\NV19.GPC,OVER 0')     # a picture, colour 0 transparent
    s += a('GET 3 0 0 10 10,OVER 1,PUT 3 40 300,FREE 3,OVER 0')
    s += a('VIEW 10 10 60 300,GET 4 0 0 20 20,PUT 4 5 5,PUT 4 70 390,WAIT 3')
    s += a('GET 5 2 2 4 4, put 5 70 200,fREE 5')    # first letters only, any case
    return s + END


# name: (language, save files from the dump, keys, the script)
SYNTHETIC = {
    'acte1': ('ja', [], [], acte1_script),
    'curtain': ('ja', [], [], curtain_script),
    'palch': ('ja', [], [], palch_script),
    'whiteh': ('ja', [], [], whiteh_script),
}

# Routes (`make e2e`): a whole story each, played by the engine's exploring player with the story
# choices fixed, then replayed on both sides until the story's unlock file is written.
# The 2nd story's endings by design (script-catalog.md §5): L is the sum of the scored choices
L_MAX = ['NOVA2=0', '2D21=1', 'CAP=0', '2CLD=0', 'YUKA2=0', '2LEM=0', '2MAL=1']    # L = 8 -> 2A
L_MIN = ['NOVA2=1', '2D21=0', 'CAP=1', '2CLD=1', 'YUKA2=1', '2LEM=1', '2MAL=1']    # L = 0 -> 2C
# name: (language, save files from the dump, title menu item, menu choices, unlock file written,
#        the script that sets the ending's flag: the route must pass through it, §5, §8)
ROUTES = {}
for _l, _sfx in (('ja', ''), ('en', '_en')):
    ROUTES.update({
        'route1' + _sfx: (_l, [], 0, [], 'FLAG3', 'S025'),
        'route2a' + _sfx: (_l, ['FLAG3'], 1, L_MAX, 'FLAG4', 'RO04'),
        'route2b' + _sfx: (_l, ['FLAG3'], 1, ['2MAL=0'], 'FLAG4', 'HHMAL'),       # R217
        'route2c' + _sfx: (_l, ['FLAG3'], 1, L_MIN, 'FLAG4', 'RO04B'),
        'route3' + _sfx: (_l, ['FLAG3', 'FLAG4'], 2, [], 'FLAG5', '3H'),
    })


def interpreter_files(original, lang):
    """The files as the original interpreter finds them, by name: the game installed from its
    four disks (disk A's copy of a name wins, NV43A is disk B's as in the pack: docs/re/disks.md
    §4), the plug-ins, and for English Fuzion's scripts over the Japanese ones."""
    files = {}
    for d in 'DCBA':
        for f in glob.glob(os.path.join(original, 'pc98', d, '*', '*')):
            files[os.path.basename(f).upper()] = open(f, 'rb').read()
    for f in glob.glob(os.path.join(original, 'pc98', 'A', '*.TCM')):
        files[os.path.basename(f).upper()] = open(f, 'rb').read()
    if lang == 'en':
        for f in glob.glob(os.path.join(original, 'en', 'MES', '*.MES')):
            files[os.path.basename(f).upper()] = open(f, 'rb').read()
    files['NV43A.GPC'] = open(os.path.join(original, 'pc98', 'B', 'GPC', 'NV43A.GPC'), 'rb').read()
    return files


# ---- the other checks -----------------------------------------------------------------------

# check_pack: names looked up in every language (the start script, a picture, a script the
# translation replaces), besides the pack's own entries
PACK_LOOKUPS = ['RUN.MES', 'NV01.GPC', 'NOVA.MES']

# check_gpc: draws of representative pictures: (name, x in bytes or 65535 for the picture's
# own place, y, masked)
GPC_DRAWS = [('NV19.GPC', 65535, 0, 0), ('NV19.GPC', 65535, 0, 1), ('NVWIN.GPC', 65535, 0, 1),
             ('NV28B.GPC', 3, 17, 1), ('NV32A.GPC', 65535, 0, 0), ('NV32A.GPC', 40, 10, 0),
             ('CP.GPC', 65535, 0, 1), ('SAVE.GPC', 70, 390, 0), ('OPPAL.GPC', 65535, 0, 0)]

# check_run: scripts a run answering every wait with Return must reach:
# RUN -> MODE (title) -> "start from the beginning" -> NVOP (opening)
RUN_EXPECT = ['RUN', 'MODE', 'NVOP']

# stories.sh: a fresh install played through the stories in turn; each must end by writing its
# unlock file (script-catalog.md §3): FILE:title menu item, in play order
STORIES = ['FLAG3:0', 'FLAG4:1', 'FLAG5:2']

# run.sh: the song of the sound path's smoke test, and the autoplay schedule of the teardown
# run (it reaches ACTE1's blocks)
SMOKE_SONG = 'NV01'
TEARDOWN_AUTOPLAY = 'rand:11 shift:2000-30000'

# check_usd and re-tools/usdmodel.py: songs started at chosen timer phases (one with both
# timers coinciding)
USD_PHASE_SONGS = ('NV08', 'NV14', 'NVSE01', 'NV10')
