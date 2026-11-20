# NOVA on Adv98X — what is left

The engine's plan (the engine's `docs/engine-plan.md`) built Adv98X on this game: every story
and all five endings, in Japanese and English, play to the same memory, screen, saves and sound
calls as the original interpreter under emulation (`make e2e`). What is left for the game:

- **A play-test** of the SDL3 build by a person (text speed, fades, music balance, the feel of
  the mouse and the menus); findings that are the engine's become engine fixes with a case here
  (`tests/cases.py`) where the original can be compared.
- **The pack-building kit**: `game.py`, the tables and the engine's and lrvne's stdlib-only
  tools in one archive, so a player builds `nova.pak` from their copy without a compiler.
- **CD-DA music**, optional: `resources/music/cd-tracks.tsv` maps the PC-98 songs to the
  tracks of the FM Towns CD (`docs/re/other-versions.md`); it needs the engine to play a track
  in place of a song.
- **A Polish translation**, as a separate effort: its tools, and the open question of the
  player's name (the engine must not preclude either answer).
