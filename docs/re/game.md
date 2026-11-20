# NOVA ～魅入られた肢体～ (Cat's Pro, PC-9801, 1993) — reverse engineering notes

Scope: the game itself — its scripts, disks, pictures and songs, and its other releases —
documented as the basis for running it on the Adv98X engine. Its engine, Adv98V 1.70.54 on
AdvBIOS 0.54, with the music driver and the plug-ins, is documented in the engine's
`docs/re/` (the engine's repository; in this one the submodule `engine/`), which was read from
this game's copy of those programs. The documents describe the original only; decisions about
the port belong elsewhere.

Source material (not in the repository; `make data` brings the files in and checks them against
`resources/inventory.tsv`): the four 2HD floppies of 1993-05-28 (D88), the Windows release of
1996 (`EVE.PCK`), the FM Towns CD of 1993, and the English translation by Fuzion (a hard-disk
image; only its 117 scripts differ from the Japanese release).

## Documents

| Document | Contents |
|---|---|
| [script-catalog.md](script-catalog.md) | every script, the route graphs of the three stories, maps, saves and unlocks, CG and music modes, the complete flag and variable tables, script bugs |
| [disks.md](disks.md) | which file is on which floppy, how scripts select disks, the rule that resolves every picture reference |
| [pictures.md](pictures.md) | the Windows release's Pi files and how they compare with the GPCs, `NV43A.GPC` on disks B and C, the table of all pictures |
| [songs.md](songs.md) | how the songs loop or end, the table of the song and effect files |
| [other-versions.md](other-versions.md) | the Windows release (EVE engine, script format, differences) and the FM Towns release (AdvTowns, archives, script dialect), the song ↔ CD track table |

## Tools

The game's own research tools are in `re-tools/`; they use the engine's tools (the engine's
`docs/re/README.md` lists those), which they find in `engine/` (or, in a tree that holds both,
next to them).

| Tool | Purpose | Verification |
|---|---|---|
| `re-tools/pi.py`, `re-tools/gpc_verify.py` | the Windows release's Pi decoder; the engine's GPC decoder against the original decoder under emulation and against the Pi files | bit-exact with the original decoder on all 103 distinct GPC files |
| `re-tools/evedis.py`, `evecmp.py`, `cdimg.py` | Windows scripts, release comparison, Towns CD image and archives | 118 Windows scripts fully covered |

## Regenerating

```sh
make data SRC="PATH/TO/pc-98 PATH/TO/EVE.PCK 'PATH/TO/Nova [TL-En by Fuzion].hdi'" DATA_PY=$EMU_PYTHON
$EMU_PYTHON re-tools/gpc_verify.py        # pictures against the original decoder and the Windows files
```

## Credits

Prior work this research builds on, read with thanks: SuperSakura by Kirinn Bunnylin (the Pi
format description, and its notes on the Windows release's EVE engine). The English text is
Fuzion's translation, whose scripts the engine plays with `--lang en`.
