# NOVA for Adv98X

The PC-98 visual novel NOVA ～魅入られた肢体～ (Cat's Pro, 1993; Adv98V 1.70.54 on AdvBIOS 0.54)
on the Adv98X engine: this repository is the game, the engine is the submodule `engine/`
(`slimeyjoe/adv98x`, with lrvne as its own submodule `engine/source/lrvne`). Read the engine's
`engine/CLAUDE.md` for the engine, its tests and its rules; they hold here too.

## Where things are

- `game.py` — the game's description, read by the engine's tools (`engine/source/tools/
  gamedir.py` finds it): `PROFILE` (the pack's profile), `PACK` (what the pack takes from which
  release, kind and path; languages; the picture rule; our built-in messages), `ORIGINAL` (the
  interpreter, AdvBIOS, the start file, the plug-ins, where their data is), `IMPORT` (lrvne's
  inventory hooks: volume labels, the Windows release's PCK archive, scan's naming).
- `tests/cases.py` — what the engine's tests play on this game (scenarios, synthetic scripts,
  routes, stories, named pictures and songs), written with the engine's `tests/casekit.py`.
- `resources/` — our own tables (`inventory.tsv`, `scripts.tsv`, `music/*.tsv`); `original/`
  and `derived/` are made by `make data` and git-ignored.
- `docs/re/game.md` — index of the game's research: script catalogue, disks, pictures, songs,
  other releases. The engine's research (`engine/docs/re/`) was read from this game's copy of
  the original programs. `docs/game-data.md`: releases, media, import. `docs/plan.md`: what is
  left to do for the game.
- `re-tools/` — the game's research tools (`gpc_verify.py`, `pi.py`, `evedis.py`, `evecmp.py`,
  `cdimg.py`); they use the engine's (`engine/re-tools/`, `engine/source/tools/`).
- `dist/` — the player's notes; the engine's make takes them over its own in the release
  archives.
- `Makefile` — the engine's make with this directory as the game (`GAME_DIR`).

## Rules

- The engine's rules (`engine/CLAUDE.md`), above all: **no game data in the repository, ever**,
  and a public, pseudonymous repository (repo-local identity, `scripts/check-leaks.sh` hooks and
  `.git/info/leak-patterns`).
- What is particular to this game goes here, never into the engine: a fact about NOVA is data
  in `game.py` or a case in `tests/cases.py`. A change the engine needs is made in the engine's
  repository, with its tests, and recorded here by moving the submodule to the engine's commit
  (as the engine does with lrvne).
- The dumped copy's `FLAG0`–`FLAG5` and `NAME.DEF` are the previous owner's state: test inputs
  only, never packed, and never quoted.
