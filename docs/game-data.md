# The game data

The repository carries none of the game: no original files, no pictures, no script text, no
music. Adv98X is built from your own copies of the releases; the tools check every file against
`resources/inventory.tsv` (name, size, md5) and refuse anything else.

## What you need

| Release | Used for | Where it comes from |
|---|---|---|
| PC-98, 1993-05-28 (four 2HD floppies, disks A–D) | everything: scripts, pictures, music, click maps | floppy images (D88, FDI, raw), a hard-disk image or an installed copy |
| English translation by Fuzion | the English scripts (`--lang en`) | its hard-disk image (only the 117 scripts that differ are taken) |
| Windows release, 1996 (`EVE.PCK`) | research only (comparisons, Pi pictures); not needed to play | the CD |

A file is recognised by name and md5 wherever it is found, so any mix of images, archives and
directories works.

## Import, derive, pack

```sh
cd source
make data SRC="path/to/pc-98 path/to/EVE.PCK 'path/to/Nova [TL-En by Fuzion].hdi'" \
          DATA_PY=$EMU_PYTHON
make pack
```

* `make data` runs `tools/gamedata.py import` (files into `resources/original/<release>/`, the
  PC-98 disks kept apart as `pc98/A`..`pc98/D`) and `tools/gamedata.py derive` (unpacked
  executables, script listings, PNGs of the pictures, plug-in listings and reference music
  recordings into `resources/derived/`; the parts needing `capstone`, `unicorn`, `pillow` or
  `numpy` run with `DATA_PY` and are skipped with a note without it). The engine only needs the
  import; the derived files are for the research documents and the tests.
* `make pack` builds `build/nova.pak` with `tools/mkpack.py`: every picture once under its bare
  name (the one name with two different files, `NV43A`, takes disk B's — both show the same
  picture, `docs/re/disks.md` §4), the songs, the click maps, the Japanese and English scripts,
  the fonts (from the X.Org bitmap fonts in `source/fonts/x11`) and the game profile. The
  pack's contents are described in `tools/mkpack.py` and `engine/pack/pack.h`.
* `make data-clean` removes `resources/original/` and `resources/derived/`; `make distclean`
  also `build/`.

## What is never packed

Disk A of the dumped copy holds the previous owner's state: `FLAG0`–`FLAG5` (saves and the
unlocks of the 2nd/3rd story) and `NAME.DEF` (the player name). They are imported as test inputs
and marked in the inventory; `mkpack.py` refuses them and `tests/check_pack.py` checks that none
is in the pack. A new install therefore starts like a new copy of the game: no saves, only "start"
on the title menu, and name entry on the first new game.

## Saves

The engine keeps the original's files, with the original's 256-byte contents, in its storage
directory (`$XDG_DATA_HOME/adv98x/nova`, default `~/.local/share/adv98x/nova`; `--storage DIR`
chooses another): `FLAG0`–`FLAG9` and `NAME.DEF`. Files from a PC-98 copy can be put there and
are used as they are.
