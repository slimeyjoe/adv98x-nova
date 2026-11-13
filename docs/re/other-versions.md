# Other releases

The analysis in this directory is of the **PC-9801 floppy release** (1993, Adv98V 1.70.54). Two
other releases were examined as far as they matter to the port: as cross-checks of the PC-98 data
and as sources of optional extras.

| | PC-98 floppies (1993-05) | FM Towns CD (1993-07) | Windows 95 CD (1996-12) |
|---|---|---|---|
| Engine | `NV.OVL` = Adv98V 1.70.54 (Tuneup) + AdvBIOS | `NOVA.EXP` = "AdvTowns for CD" (Tuneup / Ides), the same interpreter family | `EVE.EXE`, an unrelated MFC program ("EVE" engine) |
| Scripts | 118 `.MES` + `NV.INI` | 118 `.MES` of the same names in a dialect of the format (§3.4); text identical | 118 `.EVE`, a different byte code (§2.3); scenario text identical |
| Container | loose files on 4 disks | 19 archives `NOVA.000`–`NOVA.012` (§3.3) | one archive `EVE.PCK` |
| Pictures | 102 GPC (4 bit planes) | 105 GPC, a packed-pixel variant (§3.5); 100 of 101 common pictures pixel-identical | 123 Pi; the PC-98 pictures plus 30 new full screens (§2.5) |
| Music | 17 `.USO` (FM, `MUS/`) | CD audio, tracks 2–18 | CD audio, tracks 2–18: the Towns recordings |
| Effects | 11 `NVSE*.USO` (FM) | 7 PCM samples (`NOVA.SE`) + CD tracks 19–22 | the same 7 samples as WAV + CD tracks 19–22 |
| Click maps | 4 `.CLM`, 8×8-pixel cells | the same 4 files, byte-identical | 4 `.CDF`, 4×4-pixel cells (§2.6) |
| Saves | `A:\FLAG0`–`5` | user floppy `A:\FLAGDISK.013`, `NOVA.FLX`, `NOVA.NAM` | `EVE.EVS` + `FILE%04d.EVD` |

Marks: **verified** = read in code or checked on all the data by a tool in this repository;
**inferred** = strong evidence, not proven. Tools (stdlib only, run with `python3 -I`):

| Tool | Purpose |
|---|---|
| `re-tools/evedis.py` | lists / checks / exports the Windows `.EVE` scripts |
| `re-tools/evecmp.py` | compares the Windows and the Towns scripts with the PC-98 scripts; holds the Towns `.MES` dialect parser |
| `re-tools/cdimg.py` | CD image: track table, ISO 9660, audio tracks; AdvTowns archives, pictures and samples |

Generated listings and comparison tables hold game text and live under `resources/derived/`
(`scripts-win/`, `compare-win/`, `compare-towns/`; not committed).

## 1. Sources

| Release | What was examined | Notes |
|---|---|---|
| Windows | `NOVA_Miirareta_Shitai.rar` | A fan repack ("Patched by AyuanX, 2023-07-13", `_Readme.txt`): `EVE.EXE` / `EVE_Win9x.EXE` are patched (no-CD, colour depth, locale, timing; the two differ in 67 bytes), `wincd.dll` / `palgdi.dll` are the patcher's, and the CD audio is supplied as `MUSIC/Track02`–`22.ogg`. `EVE.PCK` (2 529 048 bytes) is taken as original; its 253 members are in `resources/original/win/`. PE time stamp of the EXE: 1996-12-03. Extras: `_Wallpapers/` — 34 BMP, 640×400, 8-bit with 15–16 colours used, dated 1996-11-14: event pictures `Nv12`…`Nv50` from the original CD (per the readme). |
| FM Towns | `Nova [CD].7z` → CloneCD image `Nova.img/.ccd/.cue/.sub` | 466 930 800 bytes = 198 525 sectors of 2352 bytes (44:07:00). ISO 9660 volume `IDES_013`, publisher `IDES`, preparer "FUJITSU LTD HYPER MEDIA DEVELOPMENT CENTER", created 1993-07-14 16:35; all files dated 1993-07-14 16:20:34. |

## 2. Windows release

### 2.1 Engine (**verified** in `EVE_Win9x.EXE` unless marked)

`EVE.EXE` is a 32-bit MFC application (classes `CEVEDoc`, `CEVEView`, `CMainFrame`; window title
"NOVA for Windows95"; 640×400 client area, 256-colour palette or window mode). It opens `EVE.PCK`,
starts `start.eve`, plays CD audio through MCI (`cdaudio`) and wave files, and keeps its state in
*named variables*: a table of 960 entries of 24 bytes at 0x460BE0 (in-use flag, name, value at
+14h; lookup 0x40B560, read 0x40B6B0, write 0x40B640). An unknown name reads as 0. Engine settings
are variables too, with bracketed names: `[WindowMode]`, `[PaletteMode]`, `[TextColor]` (default
25), `[BgColor]` (10), `[ShadowColor]` (11), `[WhiteColor]` (25), `[SelColorR/G/B]` (255),
`[UnSelColorR/G/B]` (127), `[repeatCDAUDIO]`, `[repeatWAVE]`; the text frame is `TextX1`, `TextY1`,
`TextX2`, `TextY2`.

SuperSakura's notes (Kirinn Bunnylin, `doc/scr/eve.md`) identify the engine as "EVE", supposedly a
"Multimedia Script Processor" by Neural, also used by *Tenshitachi no Hohoemi*, *Majokko
Paradise*, *Cat's Part 1* and *Kurayami*; they give no format details. Everything below was worked
out here from the executable and the data.

### 2.2 `EVE.PCK` (recap; reader: `source/tools/diskimg.py`, **verified**)

"PCK Version 1.00": the first 0x4000 bytes (a 32-byte header and 511 directory entries of 32
bytes: 16-byte name, u32 offset, u32 size) are stored with every 16-bit word rotated right by one
bit; member data is plain. 253 members: 118 `.EVE`, 123 `.PI`, 7 `.WAV`, 4 `.CDF` and one empty
entry with a blank name.

### 2.3 `.EVE` scripts (**verified**: interpreter 0x40BFD0, tables 0x40D1C0 / 0x40D288; `evedis.py check`)

Every byte of the file is stored inverted (`NOT`; loader 0x40B9B0). The plain file is a flat
sequence of instructions without header or end marker: a 16-bit little-endian opcode followed by
its operands. Operand kinds:

| Kind | Encoding |
|---|---|
| `w` | 16-bit little-endian word (reader 0x40BA80) |
| `j` | a `w` that is an offset into the same file: a jump target |
| `s` | NUL-terminated Shift-JIS string (0x40BAB0) |
| `n` | number, written as a string: a decimal literal if it starts with a digit, `+` or `-`; otherwise the name of a variable whose value is taken (0x40BAE0) |
| `e` | condition (0x40BBD0): comparison `n n w`, then a connector word: 0 ends, 1 = AND, 2 = OR followed by another comparison. Comparison codes (0x40BB30), for operands a b in file order: 1 a = b, 2 a < b, 3 a ≤ b, 4 a > b, 5 a ≥ b, 8 a ≠ b; 6 and 7 are never true. AND is evaluated as a product, OR as a bitwise OR, left to right without precedence |

`evedis.py check` decodes all 118 scripts (432 284 bytes, 18 715 instructions) with every byte
accounted for and every jump target on an instruction boundary. "Uses" below counts those
instructions; names are ours.

| Op | Name | Operands | Effect | Uses |
|---|---|---|---|---|
| 00 | end | – | return to the calling script (`call-script`), or end of the program | 1 |
| 10 | text | s | print a line in the text frame; `%s` = the player's name; 0Dh = line break | 6974 |
| 11 | text-frame | n n n n | `TextX1 TextY1 TextX2 TextY2` := the operands (pixels) | 283 |
| 12 | text-color | w n | sets the text colour to n (the word is read and ignored) | 52 |
| 13 | text-raw | s | like `text` through a second print routine (0x4085A0): used for titles and screen labels (**inferred**: no speaker tag handling / no page wait) | 24 |
| 14 | text-pos | n n | cursor position (**inferred**) | 2 |
| 21, 73 | nop | – | nothing | 0 |
| 30 | wait | w s | sub-command w: 1 = wait for a click on the map loaded by `map-load` and store its region number in variable s; 2 = wait for a key after text, then clear; 3 = name entry, s is the default name; 4 = wait for a key (used in the picture-viewer branches). s is `return` except for 3 (1–2 **inferred** from use, 3–4 **inferred**) | 6524 |
| 40 | delay | n | wait n × 10 timer units | 212 |
| 41 | delay-ms | n | wait n timer units (the unit was not established) | 399 |
| 50 | menu-begin | – | start collecting menu items | 69 |
| 51 | menu-item | w s j w [e] | item with text s; the item's code follows and ends at j. Second word ≠ 0: the item exists only if e holds. First word: item selected initially (−1 = none) | 185 |
| 52 | menu-jump | j | jump (written at the end of an item's code) | 184 |
| 53 | menu-run | – | lay the items out in the text frame, let the player choose, continue in the chosen item's code | 69 |
| 60 | switch | n | push n on the switch stack | 11 |
| 61 | case | n j | if the top of the switch stack ≠ n: jump to j | 67 |
| 62 | case-end | j | jump | 67 |
| 63 | switch-end | – | pop the switch stack | 11 |
| 64, 66, 68, 6C | jump | j | unconditional jumps (the compiler's `else`, loop ends …); only 66 and 68 occur | 140 |
| 65, 67, 6E | if | e j | jump to j if e is false (65 `if`: 203, 67 loop head: 18, 6E: 0) | 221 |
| 69 | until | e j | jump to j if e is true | 0 |
| 6A–6D | cycle | 6A w; 6B j w [e]; 6C j; 6D – | "next alternative each time": 6A stores its own counter in the script and increments it, 6B registers an alternative, 6D runs alternative (counter mod count). The counterpart of Adv98's `branch-cycle` | 0 |
| 70 | set | s n | variable s := n | 129 |
| 71 | calc | n n n w s | variable s := a op b; op 1 +, 2 −, 3 /, 4 × (the third number is read and unused) | 6 |
| 80 | image | w w w s | load and draw picture s at x, y (FFFFh = the picture's own position); third word = transparent colour index (FFFFh = opaque) (**inferred** from the two draw paths 0x403090 / 0x403310) | 997 |
| 81 | map-load | s | load a `.CDF` click map | 11 |
| 82 | goto-script | s | load script s and run it from the start | 215 |
| 83 | call-script | s | the same, remembering the position to return to with `end` | 0 |
| 90 | effect | n [n] | screen effect n; sub-commands 1–8, 50–52, 60, 61, 70–73, 80 take one more number, others take none and do nothing (table 0x40D380). Used: 1 (369), 2 (475), 3, 4, 5, 6 (403), 7, 8, 51, 70–73. Not analysed; from use: 1 = bring the loaded picture on screen, 2 = fade out, 70–73 = text-window open / close variants that use the text frame (**inferred**) | 1396 |
| 91, 92 | effect-91, effect-92 | n n; n n n n n | further drawing calls (0x403C90, 0x404ED0) | 0 |
| C0 | play | w n \| w s | w = 0: play CD track n; w = 1: play wave file s | 158 |
| C1 | stop | w | 0: stop the CD; 1: stop the wave | 122 |
| C2 | repeat | w w | 0: `[repeatCDAUDIO]` := second word; 1: `[repeatWAVE]` := it | 167 |
| D0 | title | s | passes s to the view (0x408860; window caption, **inferred**) | 0 |
| D1 | mkdir | s | create a directory (the save path). The repack's EXE has this handler patched out | 3 |
| D2 | sys-save | – | write `EVE.EVS` | 1 |
| D3 | sys-load | – | read `EVE.EVS` | 1 |
| D4 | sys-get | s n | variable s := system value n | 3 |
| D5 | sys-set | n n | system value a := b | 10 |
| D7 | reset | n | n = 0: clear all variables and set the engine defaults | 1 |

49 opcodes are dispatched, 36 occur in NOVA. The scripts are compiler output: control flow is
structured (`if`/`else`, `switch`, menus, one `while`-style loop per menu script on the variable
`exit`), and all 118 files use the same idioms.

Variables used by the scripts: `f17` … `f913` and `f1003`–`f1005` are the PC-98 flags of the same
numbers (**verified** by `evecmp.py`: the same flags are set and tested in the same scripts);
`gmode` is PC-98 variable A, `L` and `U` are L and U; `exit` and `return` replace the PC-98 menu
variables S / V / N.

`START.EVE` replaces PC-98 `RUN.MES`: it creates `\Program Files\Cat's Pro\NOVA\`, reads
`EVE.EVS`, resets the variables, shows `bl.pi` and the logo `cp.pi` with CD track 2, and goes to
`MODE.EVE`.

### 2.4 Scripts compared with the PC-98 (`evecmp.py win`, **verified**)

117 scripts pair by name (PC-98 `RUN` ↔ Windows `START` are the 118th). Text is compared line by
line after normalising the brackets of the speaker tag (PC-98 `［＊＊＊］` printed separately,
Windows `【%s】` in the same string), the name placeholder and white space:

| | Lines |
|---|---|
| equal | 6934 (of these 182 menu items) |
| differing | 28 |
| only PC-98 | 305 |
| only Windows | 218 |

**The scenario is the same text.** No scene was added or removed and nothing was censored: every
dialogue script, including all the adult scenes (`3H*`, `HH*`, `H`, `YUH*`), compares equal line
for line. What differs:

* **Small edits** (about 15 lines): a typo fix (`SELC`: 以外 → 意外), punctuation (`NTH`, `S010A`),
  a dropped colon after a tag (`RO01`), one long sentence split in two (`NOVA`), and the recap in
  `S010` reworded (three sentences about the order in which the crew woke up).
* **Map screens** (`MAP1–4`, `2MAP*`): Windows adds the prompt "移動したい場所をカーソルで選択して下さい。"
  and merges or extends a few room descriptions; the PC-98 save dialogue inside the map scripts
  (picture `SAVE`, variable U, "セーブするファイルを選んで下さい") is gone, because saving is an engine
  menu on Windows.
* **Typed-out computer screens**: the PC-98 draws WISE's terminal and the "AREA-…" display
  character by character as text (20–25 text steps each in `201`, `202`, `203`, `D11`, `S021`,
  `WAL3`, `D21`, `S015`); Windows shows new pictures instead (`NV56A`, `AREA`).
* **Staff roll** (`END`): 23 text screens on the PC-98, pictures `NV99A`–`NV99R`, `NV99CPY`,
  `NV99SC1`, `NV99SC2A/B/C`, `NV99SC3` on Windows; `END.EVE` also records the ending reached
  (`sys-set 1` / `2`) and returns to `START`.
* **Opening** (`NVOP`) and **title menu** (`MODE`): re-done for the engine (new pictures `NVOP01`,
  `NVOP02`, `HSS01`, `HSS02`; name entry by keyboard; no "continue" items — loading is an engine
  menu).
* **Music cues**: identical after the mapping of §4 except in six scripts: `201`–`203` play track
  20 (PC-98 effect 9) where the PC-98 plays effect 10; `D23` uses effect 5 where the PC-98 has 7
  and once more; `2D21` lacks one effect 7; `MAP2` does not restart song 1.
* **Flags**: the same assignments and tests everywhere except the save / mode machinery above, one
  duplicated `f900 = 1` in `D32` and a missing `f100 = 0` in `S015`.
* **Jumps**: the PC-98 scripts `202`, `2MAP1B`, `HHKEI`, `HHLEM`, `HHNAT` name scripts that do not
  exist (`2MAP1C`→ present, `2MAP2C`, `2MAP3B`: see `compare-win/summary.tsv`); the Windows scripts
  do not carry those references.

### 2.5 Pictures (see graphics-formats.md §5 for the Pi format and the pixel comparison)

Which pictures the scripts load (`evecmp.py`; counts = scripts):

| Only loaded by Windows | Where | Instead of |
|---|---|---|
| `NV12 NV15 NV16 NV32 NV40 NV41 NV48 NV51 NV55` | the scripts that load the halves on PC-98 | PC-98 `…A` + `…B` half pictures, merged to full screens |
| `NV56A` | `201 202 203 D11 S021 WAL3` | typed-out terminal text |
| `AREA` | `D21 S015` | typed-out text |
| `NVOP01 NVOP02 HSS01 HSS02` | `NVOP` | opening drawn by script on PC-98 |
| `NV99A`–`NV99R`, `NV99CPY`, `NV99SC1`, `NV99SC2A/B/C`, `NV99SC3` | `END` | staff roll as text over `NV99` |
| `BL` (black screen) | 25 scripts | PC-98 fades and clears |
| `NV04` | `RO02B` | PC-98 loads `NV01L` there |

Only loaded by the PC-98: `NVWIN` (the text-window frame, 101 scripts; Windows draws its window
itself and uses `MAPWIN` / `NVWIN.PI` only on maps), `SAVE`, `NV99`, `NV01` in `D22`, `MAP2` in
`2MAP1B/C`, and the half pictures. `NV19A.GPC` exists on the PC-98 disks but no script of any
release loads it.

### 2.6 `.CDF` click maps (**verified** against the `.CLM` files)

`MAP1`–`MAP4.CDF`: 16 000 bytes = 160 × 100 cells of 4×4 pixels, one byte per cell, row by row, no
header; the byte is the region number (0 = none) that `wait 1` stores. The PC-98 `.CLM` holds the
same regions at 8×8 pixels (80 × 50 nibbles, advbios.md §6.3). The region numbers are the same
sets (map 1: 1–4, map 2: 1–14, map 3: 1–4, map 4: 1–2), and no cell maps to conflicting regions;
the CDF only has finer edges (cells where the 2×2 CDF block is not uniform: 67, 128, 36, 16 of
4000). The port can use the CLM tables as they are.

### 2.7 Sound

* **Effects**: `NVSE01`, `03`–`08.WAV`: mono, 8-bit, 19 193 Hz (01, 03, 06, 08) or 9 591 Hz (04,
  05, 07). They are the FM Towns samples of `NOVA.SE` converted (sign-magnitude → unsigned), equal
  sample for sample except that the last sample is forced to 80h (**verified**). The scripts set
  `[repeatWAVE]` before each: 01, 04, 05, 06, 07 loop, 03 and 08 play once — the same as the loop
  fields of the Towns samples.
* **CD audio**: 21 tracks, 2–22, all used by the scripts. The repack's Ogg files have exactly the
  lengths of the Towns CD's tracks, and decoded they correlate with the Towns audio at 0.995–0.999
  (tracks 2, 3, 19, 22 checked): the Windows CD carried the Towns recordings (**verified** to the
  precision a lossy copy allows). Mapping: §4.

### 2.8 Save files

* `EVE.EVS` (1276 = 4FCh bytes, read to / written from 0x44AA58, **verified**): 256 bytes for the
  player's name (Shift-JIS, NUL-terminated; "ヒデキチ" is used when the file is missing) and 255
  32-bit system values, the ones `sys-get` / `sys-set` address. NOVA uses values 0–2:
  `MODE.EVE` copies them to `f1003`–`f1005` (which title-menu entries are unlocked), `END.EVE` and
  others set them. The repack's file has the name "カイル" and values 0–2 = 1 (everything open).
* `FILE%04d.EVD`: a saved game, DD2Ch = 56 620 bytes written from 0x44AF58 followed by more data
  (0x40B320); listed in the engine's load / save dialogue with date and a caption. Not analysed —
  the port has no use for it.

## 3. FM Towns release

### 3.1 Disc (`cdimg.py tracks`, **verified**)

One session, 22 tracks: track 1 is MODE1 data, sectors 0–8999 (2:00; the file system uses 5358
blocks, the rest is padding), tracks 2–22 are audio, sectors 9000–198 524 (42:07). The `.cue` and
the `.ccd` agree; no index 0 / pregap is recorded for the audio tracks, the gaps are part of the
tracks (each starts with 0.14–0.55 s and ends with about 2 s of digital silence). Track lengths:
§4. `cdimg.py wav IMAGE n OUT.wav` exports a track, `cdimg.py audio IMAGE` prints length, peak,
silence and MD5 per track.

### 3.2 Files (`cdimg.py ls`: 44 files, 10 871 127 bytes)

| Path | Size | What |
|---|---|---|
| `IO.SYS`, `CONFIG.SYS`, `AUTOEXEC.BAT`, `TBIOS.SYS/.BIN`, `TOWNS.SYS`, `SYS/CTL.SYS`, `RUN386.EXE`, `DRIVE_R.IMG`, `T_TOOL/*`, `HCOPY/COCO.EXE` | | bootable Towns OS (MS-DOS + Phar Lap `RUN386`); `COCO` is Fujitsu's "Code of Co-native OS" loader |
| `ADVSHELL.EXE` | 6 240 | started by `AUTOEXEC.BAT` (`AdvShell -NotExit`); runs the `.EXP` programs (**inferred**) |
| `LOGOMAIN.EXP`, `MEMCHECK.EXP` | 8 070, 894 | logo and memory check (Tuneup / Ides) |
| `MENU/MENU.EXP`, `MENU.INI`, `MENU.000` | 38 781, 813, 78 463 | launcher: start the game, format the user disk (`FORMAT*.MES`), return to the OS (`RETURN.MES`); an AdvTowns program with its own archive |
| `NOVA/NOVA.EXP`, `NOVA.INI` | 39 292, 176 | the game interpreter and its start script |
| `NOVA/NOVA.000` – `NOVA.012` | 8.6 MB | 19 archives (the extension is a hexadecimal number 000–012h) |
| `NOVA.TXT` | 1 024 | copyright notice: "「ＮＯＶＡ」 Copyright(C) 1993 ＣＡＴ’Ｓ ＰＲＯ." |
| `PADDING1.DAT`, `PADDING2.DAT` | | filler |

`NOVA.EXP` is a Phar Lap `P3` flat-model program with the notices "Copyright(C) 1991,93 Tuneup."
and "Copyright(C) 1991,93 Ides."; `NOVA.INI` announces "AdvTowns for CD … Copyright(C) Ides
1991,93". Tuneup is the author of Adv98V: this is the Towns port of the same interpreter
(**inferred** from the notices and from the script format, §3.4; the code was not disassembled).
The plug-ins the PC-98 loads from `.TCM` files are built in — the executable contains the names
`acte1.tcm`, `chgfonth.tcm`, `mousenam.tcm`, `palch.tcm`, `whiteh.tcm`, and the scripts "load" them
into numbered slots (`load-mem "acte1.tcm" 1`; `exec-mem 1 "…"`). `mousenam.tcm` replaces
`InputNam.tcm`: the name is entered with the mouse on an on-screen keyboard (`KEY_0/A/H/K.GPC`).
Saves go to a user floppy: `A:\FLAGDISK.013` (disk label check; 013 is also the volume number
`IDES_013`), `A:\NOVA.FLX`, `A:\NOVA.NAM`.

### 3.3 AdvTowns archives (`cdimg.py arc-ls` / `arc-extract`, **verified** on all 20 archives)

A table of 16-byte entries — 12 bytes of NUL-padded lower-case name, u32 offset — ending where the
first member starts; the last entry has an empty name and the file size. Members are stored
unpacked. `NOVA.000`–`012` hold 514 members = 232 distinct names: 118 `.mes`, 105 `.gpc`, 4
`.clm`, and in `NOVA.000` the tables `nova.dir`, `nova.fmb`, `nova.pmb`, `nova.cdt`, `nova.se`.
Members of one name are identical in every archive that has them (**verified**): each archive is
a self-contained part of the game (its scripts and every picture they need), so that playing
does not seek across the disc (**inferred**). `nova.dir` is the index: an 8-byte name, then 122
records of 8-byte script name + u16 archive number. A script changes archive with `D5 n "NOVA.0xx"`.

### 3.4 Scripts (`evecmp.py towns-check`, `evecmp.py towns`)

The `.MES` files are Adv98 scripts in a dialect. 20 of the 118 are byte-identical to the PC-98
files; the others differ in these encodings (**inferred** from byte comparison with the PC-98
files; **verified** in that the adapted parser — `TownsScript` in `evecmp.py`, a subclass of
`mes.Script` — covers every byte of all 124 scripts and both `.INI` files and reproduces the
PC-98 structure):

| Item | PC-98 | Towns |
|---|---|---|
| variable token | 2 bytes (index and 4-bit value packed, mes-format.md §2) | 3 bytes: `10h + op` (0 set / equal, 2 add / ≥, 4 subtract / ≤), index × 2, value |
| `sound` (D0) | `"file.USO"`, `se "file"`, numbers | a two-letter device first: `cd n` = CD track via `nova.cdt`, `se n` = sample n of `nova.se`; `fm` / `pm` / `cd` / `se "file"` load the tables (in `NOVA.INI`); the plain numbers (0 stop, 1 play, 2 fade) as on PC-98 |
| D5 | `decrypt key` | `D5 n "file"`: open archive n (0 = `NOVA.000`, 1 = the directory) |
| `load-mem` / `exec-mem` | address in the interpreter's segment | slot number of a built-in plug-in |
| `wait` (AB) in some scripts | `wait` | `proc 0` (a procedure defined once), 43 places |

Flag tokens, text, numbers, blocks and all other opcodes are unchanged. The three defects of the
PC-98 scripts (mes-format.md §6) are present unchanged.

Comparison with the PC-98 scripts (same method as §2.4): **7206 lines equal, 11 differing, 50
only PC-98, 3 only Towns**, all of the differences in two scripts: `MODE` (the title menu: the
name-entry prompt and the save-slot texts are replaced by the Towns versions) and `END` (the staff
roll credits "Sound Arrangement AKIRA / YOSHIHITO HATA" and "Sound Produce MUSE" where the PC-98
has "Sound Effects by KIYOTAKA SATO" and "Sound System by MUSE"). Pictures loaded, flags and
jumps are the same in every script; the music cues are the same in every script after the mapping
of §4 (0 scripts differ). `RUN.MES` additionally clears variables A–Z. Six scripts exist only on
the Towns disc, in `MENU.000`: `MENU`, `START`, `FORMAT`, `FORMAT1`, `FORMAT2`, `RETURN`.

The Towns release is therefore an independent witness for the PC-98 script data: where the Windows
scripts deviate (§2.4), the Towns scripts side with the PC-98.

### 3.5 Pictures (`cdimg.py gpc-cmp` / `gpc-png`, **verified**)

The `.gpc` files are not the PC-98 container: no signature; 16 palette words `0x0GRB`; u16 width,
height, x, y, k; then the stream. The stream uses the PC-98 GPC's zero-suppression coding
(graphics-formats.md §3), but a row is a filter byte + width/2 bytes of packed pixels (low nibble
= left pixel, the Towns VRAM layout) instead of four bit planes, and two values are stored as
exponents: row interleave step = 1 << (k − 1), and horizontal XOR step = 1 << (f − 1) for a
filter byte f > 0. With that, every stream is consumed exactly, and **100 of the 101 pictures that
have a PC-98 namesake decode to the same pixels, palette and position**. The exception is `NVWIN`
(the text window: 640×104 at (0,296) on Towns, 528×103 at (56,297) on PC-98). `NV19A` is missing
on the Towns disc (it is unused). Towns-only pictures: `KEY_0`, `KEY_A`, `KEY_H`, `KEY_K`
(on-screen keyboard, 184×132) and in `MENU.000` the launcher's `MAIN` (640×400: the cabin of
`NV00` with a character added — art that is in no other release), `SELECT`, and 15 labels of
240×40.

The click maps `MAP1`–`MAP4.CLM` are byte-identical to the PC-98 files.

### 3.6 Sound (`cdimg.py se-wav`, **verified** unless marked)

* `nova.se` (125 523 bytes): u16 count (7), 7 × (u8 0, u32 offset), then per sample a 32-byte FM
  Towns `SND` header (name, id, length, loop start, loop length, rate word = Hz × 0.098, adjust,
  base note 60) and 8-bit sign-magnitude PCM. Samples 0–6 are named `NVSE01`, `NVSE03`, `NVSE04`,
  `NVSE05`, `NVSE06`, `NSE07` (sic), `NVSE08`; rate words 1881 (19.2 kHz) and 940 (9.6 kHz);
  22 791, 45 498, 10 178, 6 537, 7 280, 10 478, 22 500 bytes. `NVSE03` and `NVSE08` have loop
  length 0 (one-shot), the others loop over their whole length.
* `nova.cdt` (23 bytes): a count (22) and 22 disc track numbers: `02 03 … 16h 02`. `sound cd n`
  plays entry n: disc track n + 1 for n = 1–21 (**inferred**: it makes all cues agree with the
  Windows release, whose scripts name disc tracks directly).
* `nova.fmb` (6 152 bytes), `nova.pmb` (52 260 bytes): FM Towns FM and PCM instrument banks
  (headers `MARINE  SE08C`, `MARINE SE15`). They are loaded by `NOVA.INI`, but no script plays
  anything through them (no `sound fm` / `pm` with a number): the music is CD audio only
  (**inferred**; they may serve the built-in key click or nothing).

## 4. Music mapping

`evecmp.py` pairs, script by script, what the PC-98 starts with `sound "\MUS\x.USO"` with what the
other release starts at the same place. The pairing is one-to-one in all 117 (Windows) / 118
(Towns) scripts apart from the six Windows deviations of §2.4, and agrees with the three sound
tests (`SOUND.MES`, Towns `SOUND.MES`, `SOUND.EVE`, which list the songs as No. 01–16 and the
effects as No. 01–11) (**verified**). The table is also in `resources/music/cd-tracks.tsv`.

| PC-98 file | Towns | Windows | CD track | Length | Loop | PC-98 uses |
|---|---|---|---|---|---|---|
| `CATS.USO` (logo) | `cd 1` | `play 0 2` | 2 | 0:13 | no | 1 |
| `NV01.USO` | `cd 2` | `play 0 3` | 3 | 2:36 | yes | 6 |
| `NV02.USO` | `cd 3` | `play 0 4` | 4 | 2:19 | yes | 4 |
| `NV03.USO` | `cd 4` | `play 0 5` | 5 | 2:12 | yes | 4 |
| `NV04.USO` | `cd 5` | `play 0 6` | 6 | 2:27 | yes | 9 |
| `NV05.USO` | `cd 6` | `play 0 7` | 7 | 2:09 | yes | 2 |
| `NV06.USO` | `cd 7` | `play 0 8` | 8 | 2:22 | yes | 3 |
| `NV07.USO` | `cd 8` | `play 0 9` | 9 | 2:47 | yes | 3 |
| `NV08.USO` | `cd 9` | `play 0 10` | 10 | 2:37 | yes | 3 |
| `NV09.USO` | `cd 10` | `play 0 11` | 11 | 1:43 | yes (once in `END`) | 2 |
| `NV10.USO` | `cd 11` | `play 0 12` | 12 | 2:31 | yes | 2 |
| `NV11.USO` | `cd 12` | `play 0 13` | 13 | 3:51 | yes | 2 |
| `NV12.USO` | `cd 13` | `play 0 14` | 14 | 2:56 | yes | 9 |
| `NV13.USO` | `cd 14` | `play 0 15` | 15 | 2:00 | yes | 12 |
| `NV14.USO` | `cd 15` | `play 0 16` | 16 | 1:51 | yes | 5 |
| `NV15.USO` | `cd 16` | `play 0 17` | 17 | 2:39 | yes | 3 |
| `NV16.USO` | `cd 17` | `play 0 18` | 18 | 2:02 | yes | 2 |
| `NVSE01.USO` | `se 0` | `NVSE01.WAV` | – | 1.19 s | yes | 11 |
| `NVSE02.USO` | `cd 18` | `play 0 19` | 19 | 0:08 | no | 3 |
| `NVSE03.USO` | `se 1` | `NVSE03.WAV` | – | 2.37 s | no | 18 |
| `NVSE04.USO` | `se 2` | `NVSE04.WAV` | – | 1.06 s | yes | 3 |
| `NVSE05.USO` | `se 3` | `NVSE05.WAV` | – | 0.68 s | yes | 9 |
| `NVSE06.USO` | `se 4` | `NVSE06.WAV` | – | 0.38 s | yes | 7 |
| `NVSE07.USO` | `se 5` | `NVSE07.WAV` | – | 1.09 s | yes | 10 |
| `NVSE08.USO` | `se 6` | `NVSE08.WAV` | – | 1.17 s | no | 3 |
| `NVSE09.USO` | `cd 19` | `play 0 20` | 20 | 0:09 | no | 3 |
| `NVSE10.USO` | `cd 20` | `play 0 21` | 21 | 0:08 | no | 12 |
| `NVSE11.USO` (music box) | `cd 21` | `play 0 22` | 22 | 2:27 | no | 8 |

Rule: song `NVnn` = disc track nn + 2. "Loop" is what the Windows scripts set in
`[repeatCDAUDIO]` / `[repeatWAVE]` before starting the item (where a script sets nothing, the
value of the previous script stays). Lengths include the silence at both ends of each track
(§3.1). The CD tracks are new arrangements of the PC-98 songs (the Towns staff roll credits a
"Sound Arrangement", §3.4), not recordings of the FM versions (**inferred**; not compared by ear).

## 5. What the port can use

* **Confidence in the PC-98 data.** Two independent releases carry the same scenario: all Towns
  scripts and all Windows dialogue scripts match the PC-98 text line for line, the Towns pictures
  match pixel for pixel, the flags are the same numbers. Differences found by `evecmp.py` in a
  future translation or edit of the PC-98 scripts are therefore real.
* **Optional CD music.** With `resources/music/cd-tracks.tsv` the port can play a CD track (from a
  user-supplied rip of either CD: track numbers and lengths are the same) wherever a script
  starts `NVnn.USO` / `CATS.USO`, and tracks 19–22 for effects 2, 9, 10, 11. The loop column says
  what to repeat. The PC-98 `sound` controls (0 stop, 1 play, 2 fade) apply unchanged — the Towns
  scripts use exactly those with the CD.
* **Optional sampled effects.** The seven WAVs (or the Towns samples) can replace
  `NVSE01/03–08.USO`; loop flags as in §4.
* **Optional pictures.** The Windows full-screen merges save nothing (the halves are identical
  art). Real additions are `NV56A` and `AREA` (replacing typed text — the port can keep the PC-98
  text effect), the opening pictures, and the picture staff roll; using any of them means
  following the Windows script at that point, not the PC-98 one. The 34 BMP wallpapers are the
  event pictures again.
* **Finer click maps** are not needed: the CDF regions equal the CLM regions.
* **Not useful:** the EVE engine's save files; the Towns launcher and its user-disk handling.

## 6. Open questions

* EVE: the meaning of the `effect` sub-commands and of the second operand; the time unit of
  `delay` / `delay-ms`; `text-raw` versus `text`; `wait 4`; the transparent-colour reading of the
  third word of `image`. None is needed unless the Windows scripts are to be run.
* EVE: the `.EVD` save layout; whether the original (unpatched) `EVE.EXE` differs in the script
  interpreter (the repack patches `mkdir` at least).
* Towns: the dialect table of §3.4 comes from the data, not from `NOVA.EXP`; opcodes that NOVA
  does not use may differ further. The role of `nova.fmb` / `nova.pmb`. The purpose of
  `DRIVE_R.IMG` and `ADVSHELL.EXE` in detail.
* Whether the original Windows CD's audio is bit-identical to the Towns CD's (only a lossy copy
  was available), and whether the Towns audio tracks have index-0 pregaps on the real disc.
* By ear: how the CD arrangements relate to the FM songs (tempo, loop points) — relevant if the
  port wants to cross-fade or loop the CD tracks seamlessly.
