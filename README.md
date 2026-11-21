# NOVA ～魅入られた肢体～ for Adv98X

**NOVA ～魅入られた肢体～** (Cat's Pro, PC-9801, 1993) on [Adv98X](https://github.com/slimeyjoe/adv98x), a
portable engine for PC-9801 games made with Adv98V 1.70.54, the adventure-game engine of Tuneup and
Ides. It runs the original scripts unmodified — the Japanese ones and the English translation by
Fuzion — and reproduces the PC-98 release faithfully: text, pictures, palette effects, menus, click
maps, saves, name entry and the FM music. It builds for desktops with SDL3 (Linux, macOS) and for
the Amiga family (AmigaOS 3.x, WarpOS, AROS).

**Adults only.** The game contains explicit sexual content.

This is an unofficial fan port. It contains none of the original program code, and **it does
not include the game itself**. You need your own copy of the PC-98 release (and, for English,
Fuzion's translation); the build turns it into the data file the engine plays.

This repository is the game: its description for the engine (`game.py`), the inventory of its
files (`resources/inventory.tsv`), its own research (`docs/re/game.md`), the cases the engine's
tests play on it (`tests/cases.py`), and the player's notes (`dist/`). The engine is the
submodule `engine/`, which has lrvne as its own.

**Status:** the game plays through, in Japanese and English: its three stories and all five
endings, the title's modes (sound and graphic), saves, name entry and the plug-ins (bold text,
palette glides, white fades, screen blocks). Verified against the original interpreter and
AdvBIOS running under emulation: every story and ending, in both languages, plays to the same
memory, screen, saves and sound calls as the original (`make e2e`), and 18 shorter scenarios
are compared the same way in `make test`. Not yet tuned by ear and eye (music balance, timing
feel). The engine's research was read from this game's copy of Adv98V and AdvBIOS.

## What you need

* **The original PC-98 game**: the four floppy disk images (D88, ...), a hard-disk image or the
  installed files; for English, Fuzion's translation (its hard-disk image). Every file is
  checked against the inventory, so any complete copy works. [docs/game-data.md](docs/game-data.md)
  lists what is accepted.
* **Python 3** (the standard library is enough to import the game and build the pack).
* **A C99 and C++14 compiler, GNU Make 4, pkg-config and SDL3** for the desktop build.

## Quick start

**Just to play:** take the Adv98X program for your system (the engine's release archive) and
this game's pack-building kit (`adv98x-nova-<version>-kit.zip`, from the releases here), then
`python3 makepak.py <your copies...>` in the kit: it needs nothing but Python 3, and writes
`build/nova.pak`. The kit's ReadMe says the rest.

**From the source:**

```sh
git clone --recurse-submodules https://github.com/slimeyjoe/adv98x-nova
cd adv98x-nova
make data SRC=~/nova/disks      # import your copy (directories, images or archives)
make pack                       # build/nova.pak
make TARGET=sdl3                # build/sdl3/adv98x
build/sdl3/adv98x --pak build/nova.pak             # Japanese
build/sdl3/adv98x --pak build/nova.pak --lang en   # English
```

All `make` targets are the engine's, run with this directory as the game: `make test`,
`make e2e`, `make TARGET=sdl3 dist`, `make dist-src`, ... (the engine's README lists them).
The tests that compare with the original under emulation need a Python with unicorn and
capstone (`EMU_PYTHON=...`). The dumped copy's own saves (`FLAG0`–`FLAG5`, `NAME.DEF`) are test
inputs of some scenarios, which are skipped without them.

## Playing

Without `--pak`, the program takes `adv98x.pak`, else the only `.pak` next to it, then in the
current directory. Saves go to `$XDG_DATA_HOME/adv98x/nova` (by default
`~/.local/share/adv98x/nova`; `--storage DIR` puts them elsewhere), as the original's files:
files from a PC-98 copy can be put there.

The keyboard is the PC-98's: Return and Space go on, the cursor keys move in menus, Esc cancels,
Shift held skips text; the Kana key of a JIS keyboard or Scroll Lock toggles kana input for name
entry. The mouse works as on the PC-98. F11 or Alt+Return: fullscreen; F12: the next scaling;
Shift+Esc: quit at once.

Each ending stays on its last screen for ever, as on the PC-98, where the player switched the
machine off. Press **Ctrl+Shift+R** to return to the title; the stories an ending unlocks are
then on the title menu.

## Credits

The story, text, pictures and music of *NOVA ～魅入られた肢体～* are © 1993 Cat's Pro; the original runs on
Adv98V and AdvBIOS by Tuneup and Ides, with K. Kondo's music driver. This port is not affiliated
with or endorsed by any of them or their successors. The English text is Fuzion's translation,
played from the player's own copy of it. The engine, this description and the research were made
for this port; prior work they build on is credited in [docs/re/game.md](docs/re/game.md) and in
the engine's `docs/re/README.md`.

GPL-3.0-or-later ([LICENSE](LICENSE)) for our own files.
