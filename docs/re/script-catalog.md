# NOVA script catalogue and route graph

All 119 scripts of the PC-98 release: the 118 files of `A:\MES\` and the start script `NV.INI`.
Everything here was read from the parsed scripts (`source/tools/mes.py`); the tables behind it are
made by `re-tools/mesgraph.py` (run it without arguments) and land in `resources/derived/scripts/`:

| File | Contents |
|---|---|
| `transitions.tsv`, `transitions.dot` | every `mes-jump` and `flag-load` with the conditions on the way to it (segment conditions, `if` alternatives, menu choice) |
| `summary.tsv` | one line per script: size, segments, text, pictures, music, flags, variables, menus, saves, plug-ins, successors |
| `flagrefs.tsv` | every flag / variable assignment and test with offset and context |
| `pictures.tsv` | every `image-file` reference resolved to a disk (see [disks.md](disks.md)) |
| `skeleton/*.txt` | each script reduced to control flow, state changes and file operations |
| `reach.txt` | reachability, missing targets, dead code, asset checks |

`resources/scripts.tsv` (committed) is the short table: script, story, role, size, successors.

Conventions: **verified** = read in the bytecode (offsets are file offsets in the Japanese script);
**inferred** = a reading of what the code is for, or of the story, not proven. Script format and
interpreter: the engine's `docs/re/mes-format.md`, `docs/re/interpreter.md`; AdvBIOS calls:
its `docs/re/advbios.md`. Flags are written R*n*, variables by letter. Menu choices are given in
English paraphrase with a short quotation of the original where that helps to find the place; story
characterisations are **inferred** (the English translation in `resources/derived/scripts-en/`
was used to read the story quickly; the Japanese scripts are the reference).

## 1. Overview (verified)

| | |
|---|---|
| Scripts | 119: 7 system, 54 of the 1st story, 43 of the 2nd, 15 of the 3rd |
| Size | 382 764 bytes; largest `WAL3` 10 787, smallest `RUN` 149 |
| Text | 12 713 text runs, 157 312 characters, 6 560 key waits |
| Transitions | 234: 225 `mes-jump` (217 live, 8 dead code) + 9 load edges; all 119 scripts are reachable from `NV.INI` |
| Menus | 67 `menu` + 3 `menu2` (`MODE`, `SOUND`, `H`) |
| Flags | 95 distinct flags in the scripts (§11); variables A, C, L, N, S, U, V (§12) |
| Pictures | 1 038 `image-file` statements, 101 distinct names, all found ([disks.md](disks.md)) |
| Music | 159 `sound "file"` statements, all 28 files of `A:\MUS\` are used |

Every story script starts with the same prologue (**verified**): `set-drive 0 0`, `set-drive 1 n`,
`menu-step`, `screen-mode 3 0 0`, `define-proc` for slots 0–6 or so (text window save / restore through
`ACTE1.TCM`, name tags, line pause; 110 scripts define slot 6), `load-mem "ACTE1.tcm" 256` + `exec-mem 256 "INIT"`,
`load-mem "ChgFontH.tcm" 8448` + `exec-mem 8448 1`. A script is therefore self-contained: it can be
entered from a save or directly, which is what makes "load = restart the saved script" work.

The story is a chain of scripts. A script ends in `mes-jump`; choices are `menu` followed either by
`if [S==n]` blocks or by `seg-call` with one later segment per choice (`[S==n …]`, first match wins).
Loops (`｛ … ｝`) keep a menu on screen until a choice leaves the script.

## 2. Game start

```
NV.OVL ─► NV.INI ─► MES\RUN.MES ─► MODE.MES ─┬ verb 0 start            ─► NVOP ─► NOVA   (1st story)
                                              ├ verb 1 2nd story [R1003] ─► NVOP ─► NOVA2  (R801)
                                              ├ verb 2 3rd story [R1004] ─► NVOP ─► NOVA3  (R802)
                                              ├ verb 3 continue  [R0]    ─► flag-load 0/1/2 ─► MAP2 | 2MAP2A | 2MAP2B
                                              ├ verb 4 Sound     [R1005] ─► SOUND ─► MODE
                                              └ verb 5 Graphic   [R1005] ─► H ─► MODE
```

* **`NV.INI`** (**verified**, interpreter.md §7): banner, `decrypt 79`, copy-protection call, then
  `mes-jump "mes\run.mes"`; on failure a prompt to insert disk A or B and, when C has reached 2
  (two failed prompts), `exit`. C and N are its work variables; it clears both before the jump.
* **`RUN`** (**verified**): drives 0/1, `screen-mode 3 0 0`, loads `ChgFontH.tcm` to 8448 (and calls
  it with 1) and `InputNam.tcm` to 9984 — the latter stays in memory for `MODE`, which does not
  load it again — shows `\GPC\CP.GPC` (company logo) with `\MUS\CATS.USO`, waits `delay 500 0`,
  jumps to `MODE`. Nothing else leads to `RUN`.
* **`MODE`** (**verified**): `save-check 5` sets R1000..R1005 from the existence of `FLAG0`..`FLAG5`
  (six files: the handler at 0xE8BC checks slots *n* down to 0, so `save-check n` covers n+1 files —
  mes-format.md says n). R0 := 1 if any of R1000..R1002 (a save exists). Then a loop around one
  `menu2 (28,140)` with six verbs; verbs whose condition fails are not shown but keep their index,
  so V is fixed: 0 start, 1 2nd story, 2 3rd story, 3 continue, 4 Sound, 5 Graphic. Only "continue"
  has nouns (the three files, each shown if its R100x is set); the others select at once.
  `seg-call` then runs the segment `[V==n]`.
* **Segments 1–3 of `MODE`** (start, 2nd, 3rd) are three copies of the same code (909, 915 and 915 bytes),
  differing only in the flag they set first: nothing, R801, R802. They show `B:\GPC\NV56.GPC`, type
  out a prompt one character at a time (20 `text-clear` + text steps, 「キーボードから名前を…」), call
  the name entry (§2.1), `name-load`, and jump to `NVOP`.
* **`NVOP`** (**verified**): the opening shared by all three stories (palette file `\GPC\OPPAL.GPC`,
  pictures `B:NV55A`, `B:NV55B`, about 200 text runs), then `if [R802] → NOVA3`, `if [R801] → NOVA2`,
  else `NOVA`.
* Flags are **not** cleared when a game starts. This is harmless because `MODE` is only entered from
  `RUN` (memory just cleared by the interpreter), `SOUND` and `H` (which change no flags), and an
  ending never returns to the menu (§8). R0, R801/R802 and R1000–R1005 stay set during the story and
  end up in the saves (the shipped `FLAG5` has R0, R1000, R1003–R1005 set).

### 2.1 Name entry (verified call, inferred argument meaning)

```
text-pos 10 228          ; 9 full-width blanks, then "－－－－": four dashes starting at column 28
exec-mem 9984 0 0 4 28 218 "カイル" 15 0
name-load
```

`InputNam.tcm` is loaded at 9984 (0x2700) by `RUN`. The call has eight arguments: 0, 0, **4**,
**28**, **218**, a string, **15**, 0. From the layout around it: 4 = maximum length in full-width
characters (four dashes are drawn as the input line), 28 / 218 = column and pixel row of the input
field (the dashes are at column 28, row 228, i.e. just below), the string = the default name, 15 =
text colour (**inferred**; the first two and the last argument are unknown — see plugins.md). The
plug-in writes `A:\NAME.DEF`; `name-load` then reads it. The English translation's default name is
"Ｋｙｌｅ" (same call otherwise). `name-load` is also done by `MODE` segment 4 before a load and by
the three map scripts that can save (`MAP2`, `2MAP2A`, `2MAP2B`), because a loaded game restarts
there and the name is not part of the save.

## 3. Saves and unlock files (verified)

| File | Written by | When | Read by |
|---|---|---|---|
| `FLAG0`–`FLAG2` | `MAP2` 0930/0985/09DA, `2MAP2A` 06F8/074D/07A2, `2MAP2B` 09FF/0A54/0AA9 | the player clicks the SAVE panel of the deck-2 map (region 14) and picks file 1–3 | `MODE` segment 4: `flag-load N` |
| `FLAG3` | `END` 0EA3, if R700 | 1st story finished | `MODE`: R1003 shows "2nd story" |
| `FLAG4` | `END` 0EF5 / 0F47 / 0F99, if R701 / R702 / R703 | any ending of the 2nd story | `MODE`: R1004 shows "3rd story" |
| `FLAG5` | `END` 0FE9, if R704 | 3rd story finished | `MODE`: R1005 shows "Sound" and "Graphic" |

* **Save points exist only on the deck-2 map**: 1st story `MAP2`, 2nd story `2MAP2A` (phase A) and
  `2MAP2B` (phase B). There is no save in the prologues, in the 3rd story, or in the ending chains.
* The save sequence is `U=1`, `wait`, `flag-save n`, a confirmation text, `U=0`. U = 1 is therefore
  stored in the save; when the game is loaded the script restarts from its top, sees `U==1`, starts
  the map music (`MAP2`: NV01, `2MAP2A`: NV16, `2MAP2B`: NV04) and clears U. Scripts that lead to a
  map and want the music restarted set U = 1 themselves (`YUKA`, `COM`, `2CLD`, `2LEM`, `2MAL`,
  `YUKA3`).
* Loading is `flag-load N` with N = the noun chosen (0–2): the whole 256-byte state is replaced and
  the interpreter jumps to the script named in it. Slots 3–5 are never loaded; only their existence
  matters. `END` writes them as ordinary saves (current script `\MES\END.MES`, all flags of the
  finished play).
* Only the *existence* test distinguishes unlock levels, so the files are independent: `FLAG5` alone
  would show Sound/Graphic without the 2nd story.
* The disk A of our dump carries `FLAG0` (a 2nd-story save in `2MAP2A`: R200, R801, L = 3),
  `FLAG3`, `FLAG4` (ending 2B: R702), `FLAG5`, and two empty 256-byte `FLAG1`/`FLAG2` (all zero =
  "no save"): the dumped copy had been played through. A clean first start needs `FLAG3`–`FLAG5`
  absent or invalid.

## 4. 1st story (verified graph, inferred labels)

```
NOVA ─(3 choices, all)─► D21 ┬ "go down to the sound" ─► EV01 ─► D31
                             ├ "look around more"    ─► D24 ┬ "think calmly"  ─► D22 ┬ "follow"  ─► EV02 ─► D11 ─► S010B
                             │                              │                        └ "call out" ─► D23
                             │                              ├ "go down"        ─► D31
                             │                              └ "other rooms"    ─► D23
                             └ "other rooms"         ─► D23 ┬ LIFT_B  ─► EV04 ─► D31
                                                            └ ROOM-01 ─► (scene) ─► S010B
D31 ┬ cargo room ─► D32 ─► D34          D34 (corridor hub, menu items by flags)
    └ door       ─► D33 ┬ engine ─► D35 ┬ "go to the voice" (R906) ─► D34
                        │               └ "let it pass"            ─► D3YK ─► S010
                        └ leave (R905) ─► D34
D34 ┬ side passage [R907=0] ─► D36 ┬ "examine the plane" ─► D37 (R912) ─► S010A
    │                              └ elsewhere ─► D34
    ├ elevator [R908=1] ─► EV03 ┬ [R908 & R906] ─► (scene) ─► S010
    │                           └ otherwise      ─► D11 ─► S010B
    ├ door with the sound [R904=0] ─► D33
    └ cargo room [R902=0] ─► D32
S010 | S010A | S010B ─► S011 ─► S012 ◄─► S013 ◄─► S014        (deck hubs 1, 2, 3)
        S012: bridge ─► BLG ─► S012      access room ─► WAL ─► S012
        S014: catapult ─► CTD ─► S014    engine room ─► ENG ─► S014
        S012 with R101 & R102 & R105 & R106 ─► S015 ┬ "Yuka's room" ─► YUH01 ─[R800=0]─► S016
                                                    └ "own room"    ─► ALEX ───────────► S016
S016 (R800=1) ─► MAP1 ◄─► MAP2 ◄─► MAP3 ◄─► MAP4          (free movement, §7)
        MAP1 bridge [R54=0] ─► BLG2 ┬ "go with Marie" (R55) ─► WAL3 ─► X
                                    └ elsewhere ─► MAP1
        MAP2 room 03 ─► YUH ─► MAP2        room 07 ─► NTH ┬ "listen" (R56), loop
                                                          ├ "embrace" [R56=1] ─► X
                                                          ├ "leave" [R56=1] ─► MAP2
                                                          └ "leave" [R56=0] ─► NTH2 ─► S017
        MAP2 room 04 [R57=1] ─► LEH ─► X
        MAP3 engine room [R57=0] ─► ENG2 (R57) ─► MAP3         MAP4 catapult ─► CTD2 ─► MAP4
   X:  [R20=0] ─► YUH01 ─[R800=1]─► S017        [R20=1] ─► S017
S017 ─► S018 ─► S019 ─► S020 ─► S021 ─► S022 ─► S023 ─► S024 ─► S025 (R700) ─► END
```

* **Prologue** (`NOVA`, `D*`, `EV*`): the player wakes up alone and explores; the scripts are small
  nodes named after the deck (`D2x` deck 2, `D3x` deck 3, `D11` deck 1 — **inferred**). There are
  three ways out, each a different first meeting, each with its own wake-up script:
  `D3YK` or the long branch of `EV03` → **`S010`** (sets R913), `D37` → **`S010A`** (R912, set in
  both `D37` and `S010A`), `D11` or `D23` → **`S010B`**. R912 and R913 are remembered and select
  text variants later (R913 in `S011`; R912 in `CTD`, `ALEX`, `S016`, `S017`).
* `NOVA`'s first menu has three items that all lead to `D21` after different text.
* `D34` is the corridor hub of deck 3. Its menu items disappear as places are visited (R902 cargo
  room, R904 engine door, R907 side passage). The elevator appears with R908, which is set when the
  player leaves the cargo room by the menu (`D32` segment 3) or when cargo room, engine door and side
  passage have all been visited (R902 & R904 & R907, once: R910). `EV03` gives the long scene only
  if R906 (went towards the voice in `D35`) is also set.
* **Chapter 1** (`S011`–`S016`): a guided tour. `S012`/`S013`/`S014` are the hubs of decks 1/2/3 with
  first-visit texts (R100, R103, R104). The four rooms (R101 bridge, R102 access room, R105 catapult
  deck, R106 engine room) can each be visited once; when all four are done `S012` jumps to `S015`
  instead of showing its menu. `S015` asks where to spend the night; `S016` (next morning) sets R800
  and opens the map.
* **Map phase**: free movement over four deck maps. Events: `BLG2` (bridge, once: R54), `YUH`
  (R59), `ENG2` (once: R57, which also opens room 04 → `LEH`), `CTD2` (R58), `NTH`. Four events end
  the phase (X above): `WAL3`, `LEH`, `NTH` "embrace", and `NTH2`. The first three then test R20:
  if the scene `YUH01` was not seen on the first night (R20 = 0) it is played now and continues with
  `S017`, otherwise they go to `S017` directly. `NTH2` always goes to `S017`.
* **`YUH01`** has two entries and uses R800 to tell them apart at its end: R800 = 0 (first night,
  from `S015`) → `S016`; R800 = 1 (map phase) → `S017`. Inside it a menu loop with stage flags
  R17–R20; the last item needs R20, so R20 = 1 whenever the script has been left.
* **Chapter 2** (`S017`–`S025`) is linear except `S019`, an examination loop (R60, R61, R62; "robot"
  with R60 & R61 leaves to `S020`) and a text variant in `S018` (R54: whether the bridge event
  `BLG2` was seen). `S025` sets R700 and jumps to `END`.
* The save (in `MAP2`) covers only the map phase.

## 5. 2nd story (verified graph, inferred labels)

```
NOVA2 ┬ "examine the room" (L+1) ┐
      └ "go outside"             ┴► 2D21 ┬ "take the elevator"        ─► 2D31 ┐
                                         └ "look around more" (L+1)   ─► 2D22 ┴► CAP ┬ "go" (R200, L+2) ─► YUKA ┐
                                                                                     └ "don't" (R201)   ─► COM  ┴► 2MAP2A
phase A:  2MAP2A ◄─► 2MAP3 ◄─► 2MAP4
          2MAP2A hypersleep [R202=0] ─► 2CLD (R202) ┬ "examine more" (R203, L+1) ─► 2MAP2A
                                                    └ "other rooms"              ─► 2MAP2A
          2MAP3  cargo [R204=0] ─► 2CAR (R204; "capsule": R205) ─► 2MAP3      engine [R206=0] ─► 2ENG (R206) ─► 2MAP3
          2MAP4  catapult ─► YUKA2 ┬ "take Yuka to safety" (R207, L+2) ┐
                                   └ "go to the scream" (R208)         ┴► MON01 ─► MT ─► 2MAP2B
phase B:  2MAP2B ◄─► 2MAP1
          2MAP2B room 03 [R209=0] ─► YUKA3 (R209)                    ─► T
                 room 04 [R210=0] ─► 2LEM (R210, R218) ┬ "comfort" (R216, L+1) ─► T
                                                       └ "leave"               ─► T
                 room 05 [R211=0] ─► 2MAL (R211, R218) ┬ "do as told" (R217)  ─► 2MAP2B   (no test)
                                                       └ "refuse"              ─► T
                 lift B  [R215=0] ─► 2NAT (R214, R215) ─► T
          2MAP1  meeting room [R212=0] ─► 2KEI (R212, R214, R219) ─► T      bridge [R213=0] ─► 2BRG (R213, R214, R219) ─► T
   T:  [R214 & R209 & R218] ─► 2ALEX      otherwise back to the map the event came from
2ALEX ┬ [R217]        ─► 202 ─► HHLEM ─► HHKEI ─► HHNAT ─► HHYUKA ─► HHMAL (R702) ─► END   "No.2B"
      ├ [L ≥ 5]       ─► 201 ─► 2MAP1B ─(lift A)─► RO01  ─► RO02  ─► RO03  ─► RO04  (R701) ─► END   "No.2A"
      └ [L ≤ 5] (L<5) ─► 203 ─► 2MAP1C ─(lift A)─► RO01B ─► RO02B ─► RO03B ─► RO04B (R703) ─► END   "No.2C"
```

**How the ending is chosen** (**verified**, `2ALEX` 0399–03C5: three `if` blocks in this order, each
ending in `mes-jump`):

1. **R217 = 1 → ending 2B.** R217 is set in exactly one place: `2MAL` segment 1, the first menu item
   (「言われるままにする」, do as told). It overrides everything else.
2. otherwise **L ≥ 5 → ending 2A**, 3. otherwise (L ≤ 4) **→ ending 2C**. (The third test is written
   `L<=5`; L = 5 never reaches it.)

**L** is a 4-bit score of six choices, never reset (a story always starts from zeroed memory):

| Script | Choice | L |
|---|---|---:|
| `NOVA2` 0553 | item 0, examine the room | +1 |
| `2D21` 054F | item 1, look around more | +1 |
| `CAP` 163C | item 0, go (to Yuka) | +2 |
| `2CLD` 031E | item 0, examine the room more | +1 |
| `YUKA2` 0D72 | item 0, take Yuka to a safe place | +2 |
| `2LEM` 0717 | item 0, comfort Remy | +1 |

Maximum 8; ending 2A needs 5, e.g. both +2 choices and one +1. The menus of `NOVA2`, `2D21`, `CAP`
and `YUKA2` are always met (up to 6 points); `2CLD` and `2LEM` are optional visits (the hypersleep
room need not be entered; room 04 is one of two ways to get R218).

**When the story leaves the map** (**verified**): each phase-B event ends with
`if [R214 R209 R218] → 2ALEX`, i.e. one "crew" event (`2KEI`, `2BRG` or `2NAT`: R214), `YUKA3`
(R209) and one of `2LEM` / `2MAL` (R218). The exception is `2MAL` item 0 (the R217 choice): it
returns to the map without the test, so `2ALEX` comes with the next event that has the test; at
least one always remains (if all of them had been visited before, the test would already have
fired). R219 (set by `2KEI`, `2BRG`) only selects the background in `2ALEX` (deck 1 or deck 2
corridor).

* Phase A cannot go up to deck 1 (`2MAP2A` region 1 only prints a text); phase B cannot go down
  (`2MAP2B` region 13 runs `2NAT` once, then only a text). Phase A ends with the catapult deck
  (`YUKA2` → `MON01` → `MT`).
* R203 (examined the hypersleep room thoroughly) selects text variants in `YUKA2` and `YUKA3`.
* The ending chains are linear. `2MAP1B` / `2MAP1C` are one-exit maps of deck 1: only lift A does
  anything (→ `RO01` / `RO01B`). The menus in `HHLEM`, `HHKEI` and `HHNAT` have two items whose
  segments set no flag and end in the same jump: text variation only.
* Saves: `2MAP2A` and `2MAP2B`.

## 6. 3rd story (verified)

```
NOVA3 ─► 301 ─► 3K01 ─► 3HK ─► SELC ◄──────────────┐
   SELC  item n [R301+n = 0] (sets it) ─► 3HN01 | 3HM01 | 3HL01 | 3HY01 ─┤ not all of R301–R304
                                                                        └ all four ─► SELC2 ◄──────────┐
   SELC2 item n [R306+n = 0] (sets it) ─► 3HN02 | 3HM02 | 3HL02 | 3HY02 ─────────────┤ not all of R306–R309
                                                                                     └ all four ─► 3H (R704) ─► END   "No.3"
```

No real branching: two rounds of four scenes, order free, each scene once. `SELC` / `SELC2` show
an intro once (R300, R305) and a comment after each returned scene once (R314–R317 for R301–R304;
R310–R313 for R306–R309). Item order in both menus: Nat (N), Marie (M), Remy (L), Yuka (Y). No save
point. The round-1 scripts show the event pictures of disk B that the 1st and 2nd story also use; round 2
and `3HK`, `3H` use disk D (disks.md).

## 7. The map system

### 7.1 Script side (verified)

A map script is one loop:

```
input "\CLM\MAPn.CLM"                 ; load the hit table (F1h AH=0Ch)
image-file "B:\GPC\MAPn.GPC"   image-show 0        ; deck plan
image-file "B:\GPC\MAPWIN.GPC" image-show 1        ; message panel (+ "B:\GPC\SAVE.GPC" on deck 2)
｛  text "choose where to go with the cursor"
    input A 1                         ; wait for a click; A := region number under the pointer
    if [A==1 …] { describe the place; if it is enterable: menu yes/no → if [S==0] mes-jump … }
    if [A==2 …] { … }
    …
｝
```

* `input A 1` (F1h AH=0Dh, AL=1): per advbios.md §6.3 it waits for a left click, ignores the right
  button (bit 0), and returns the nibble of the 8×8-pixel cell under the pointer; a click on a cell
  with value 0 returns 0, which matches no `if`, so the loop just repeats.
* The `.CLM` file is `00, x0, y0, w, h` + w×h nibbles; NOVA's four are full screen 80×50 cells
  (2 005 bytes). Region numbers used: `MAP1` 1–4, `MAP2` 1–14, `MAP3` 1–4, `MAP4` 1–2. The regions
  are the room parallelograms of the isometric deck plan; region 14 of `MAP2` is the rectangle of
  the SAVE panel (cells 61–76 × 29–31, where `SAVE.GPC` is drawn).
* Each region is an `if` block of its own, not an alternative of one `if`. Where a region has two
  states the scripts write either two exclusive conditions (`[A==4 R54==0]`, `[A==4 R54==1]`) or a
  conditional block followed by an unconditional one (`[A==2 R202==0]`, `[A==2]`); in the second
  form answering "no" falls into the second block and shows the plain description as well.
* The 2nd story re-uses the four tables and pictures with its own scripts. The same table serves
  several scripts: `MAP1.CLM` ← `MAP1`, `2MAP1`, `2MAP1B`, `2MAP1C`; `MAP2.CLM` ← `MAP2`, `2MAP2A`,
  `2MAP2B`; `MAP3.CLM` ← `MAP3`, `2MAP3`; `MAP4.CLM` ← `MAP4`, `2MAP4`.
* Entering a place always asks yes / no (`menu (45,330) (45,350)`), except the save panel.

### 7.2 Regions and destinations (verified; room names from the scripts' own descriptions)

| Table | Region | Place | 1st story | 2nd story |
|---|---:|---|---|---|
| MAP1 (deck 1) | 1 | lift A down | `MAP1` → `MAP2` | `2MAP1` → `2MAP2B`; `2MAP1B` → `RO01`; `2MAP1C` → `RO01B` |
| | 2 | meeting room | text | `2MAP1` [R212=0] → `2KEI`; else text |
| | 3 | access room | text | text |
| | 4 | bridge | [R54=0] → `BLG2`; else text | `2MAP1` [R213=0] → `2BRG`; else text |
| MAP2 (deck 2) | 1 | lift A up | → `MAP1` | `2MAP2A`: text; `2MAP2B` → `2MAP1` |
| | 2 | hypersleep room | text | `2MAP2A` [R202=0] → `2CLD`; else text |
| | 3, 4 | medical room, food store | text | text |
| | 5, 6 | private rooms 01, 02 (unused; the player's) | text | text |
| | 7 | private room 03 (Yuka) | → `YUH` | `2MAP2B` [R209=0] → `YUKA3`; else text |
| | 8 | private room 04 (Remy) | [R57=1] → `LEH`; else text | `2MAP2B` [R210=0] → `2LEM`; else text |
| | 9 | private room 05 (Marie) | text | `2MAP2B` [R211=0] → `2MAL`; else text |
| | 10 | private room 06 (Alex) | text | text |
| | 11 | private room 07 (Nat) | → `NTH` | text |
| | 12 | private room 08 (Kate) | text | text |
| | 13 | lift B down | → `MAP3` | `2MAP2A` → `2MAP3`; `2MAP2B` [R215=0] → `2NAT`; else text |
| | 14 | SAVE panel | save menu | save menu (both) |
| MAP3 (deck 3) | 1 | lift B up | → `MAP2` | → `2MAP2A` |
| | 2 | cargo room | text | [R204=0] → `2CAR`; else text |
| | 3 | engine room | [R57=0] → `ENG2`; else text | [R206=0] → `2ENG`; else text |
| | 4 | lift C down | → `MAP4` | → `2MAP4` |
| MAP4 (catapult deck) | 1 | lift C up | → `MAP3` | → `2MAP3` |
| | 2 | catapult area | → `CTD2` | → `YUKA2` |

`2MAP3` → lift B always returns to `2MAP2A` and `2MAP4` exists only in phase A, so phase B never
sees decks 3 and 4.

### 7.3 The save panel (verified)

Region 14: a prompt, then `menu (45,300) (45,320) (45,340) (45,360)` with four items: cancel,
file 1, file 2, file 3 → `flag-save 0/1/2` (§3). The three scripts carry identical code.

## 8. Endings and staff roll (verified)

All five endings jump to **`END`** with one of R700–R704 set by the last story script:

| Flag | Set in | Card (quoted) | Unlock file |
|---|---|---|---|
| R700 | `S025` 0570 | Ｓｃｅｎａｒｉｏ Ｎｏ．１ Ｅｎｄ | `FLAG3` |
| R701 | `RO04` 0AF3 | … Ｎｏ．２Ａ Ｅｎｄ | `FLAG4` |
| R702 | `HHMAL` 0DB1 | … Ｎｏ．２Ｂ Ｅｎｄ | `FLAG4` |
| R703 | `RO04B` 0A9C | … Ｎｏ．２Ｃ Ｅｎｄ | `FLAG4` |
| R704 | `3H` 1302 | … Ｎｏ．３ Ｅｎｄ | `FLAG5` |

`END`: music `\MUS\NV09.USO`, background `B:\GPC\NV99.GPC`, then the staff roll as ordinary script
text: 18 screens, each `proc 1` (restore the window area), `proc 0` (save it, draw the window),
`text-frame 0 160 69 390`, a title line and names, `delay 200 0`. After the roll five `if` blocks
print the card for the flag that is set and write the unlock file. The script then ends in an empty
endless loop (`｛ ｝` at 0FED): **there is no way back to the title; the player resets the machine.**
(The loop still polls the abort request, interpreter.md §3.)

`END` is the only story script that does not set drive slot 1 itself: `NV99.GPC` is read from
whichever picture disk the last script used, which is why that file is on B, C and D (disks.md).

## 9. Music mode and CG mode (verified)

Neither mode keeps a list of what the player has seen or heard. Both are fixed scripts, available
as a whole once `FLAG5` exists.

**`SOUND`**: background `B:\GPC\NV56.GPC`, a loop around one `menu2` with 16 positions (4 columns ×
4 rows, columns 5/18/31/44, rows 100–160) and three verbs: "ＳＯＵＮＤ" with 16 nouns, "Ｓ．Ｅ" with 11
nouns, "▼ＥＸＩＴ". 27 segments `[V==0 N==n]` → `sound 0`, `sound "\MUS\NV01..16.USO"`, `sound 1`
and `[V==1 N==n]` → the same with `NVSE01..11.USO`; `[V==2]` → `sound 0`, `MODE`. The "sound
effects" are music files like the others (`.USO` played with `sound "file"`); the `sound se`
form is not used anywhere in the game.

**`H`** (called "Graphic" in the menu): `menu2` with four verbs — replay by key press, automatic
fast, automatic normal, exit — and three near-identical segments that show the same fixed sequence
of 45 screens: `fade 0 1`, `image-file` + `image-show 0` (and, for composed pictures, a second
`image-file` + `image-show 1 0`), `fade 1 1`, then `wait` (V = 0), `delay 100` (V = 1) or
`delay 300` (V = 2). The sequence is ordered by disk: 20 screens from disk B, `set-drive 1 2`,
13 from disk C, `set-drive 1 3`, 12 from disk D, then `set-drive 0 0`, `set-drive 1 1` and back to
the menu. On floppies this means two disk changes per run. Only event pictures are shown (no
backgrounds or portraits); the list is in `skeleton/H.txt`.

## 10. Per-script catalogue (verified; roles inferred)

Sizes in bytes; "Text" = text runs / characters; "Menus" = `menu(n)` with n items (`menu2(n)`:
n = verbs + noun slots); flags as ranges; "In from" / "Out to" = live `mes-jump` edges (`load:` = through `flag-load`).

**System scripts**

| Script | Role | Size | Text runs / chars | Menus | Flags set | Flags tested | In from | Out to |
|---|---|---:|---:|---|---|---|---|---|
| END | staff roll, ending card, unlock save | 4087 | 58 / 1669 | – | – | 700-704 | 3H HHMAL RO04 RO04B S025 | – |
| H | CG mode | 5377 | 4 / 52 | menu2(8) | – | – | MODE | MODE |
| MODE | title / mode menu, name entry, load | 3176 | 70 / 1022 | menu2(14) | 0 801-802 | 0 1000-1005 | H RUN SOUND | NVOP SOUND H load:2MAP2A load:2MAP2B load:MAP2 |
| NVOP | opening (all stories) | 8037 | 204 / 2320 | – | – | 801-802 | MODE | NOVA3 NOVA2 NOVA |
| RUN | boot: logo, plug-ins | 149 | 0 / 0 | – | – | – | NV.INI | MODE |
| SOUND | music mode | 1356 | 31 / 167 | menu2(31) | – | – | MODE | MODE |
| NV.INI | start script (banner, copy protection) | 954 | 13 / 121 | – | – | – | – | RUN |

**1st story**

| Script | Role | Size | Text runs / chars | Menus | Flags set | Flags tested | In from | Out to |
|---|---|---:|---:|---|---|---|---|---|
| ALEX | chapter 1: night scene | 3208 | 73 / 1507 | – | – | 912 | S015 | S016 |
| BLG | chapter 1: room visit | 4935 | 208 / 2215 | – | – | – | S012 | S012 |
| BLG2 | map event | 2759 | 100 / 1120 | menu(2) | 54-55 | 54 | MAP1 | WAL3 MAP1 |
| CTD | chapter 1: room visit | 2437 | 96 / 1073 | – | – | 912 | S014 | S014 |
| CTD2 | map event | 723 | 20 / 175 | – | 58 | 58 | MAP4 | MAP4 |
| D11 | prologue: meeting scene (exit) | 7783 | 250 / 4090 | – | – | – | EV02 EV03 | S010B |
| D21 | prologue: exploration node | 4341 | 69 / 1935 | menu(3) | – | – | NOVA | EV01 D24 D23 |
| D22 | prologue: exploration node | 2089 | 31 / 1040 | menu(2) | – | – | D24 | EV02 D23 |
| D23 | prologue: exploration node | 5522 | 193 / 2564 | menu(2) | – | – | D21 D22 D24 | EV04 S010B |
| D24 | prologue: exploration node | 2138 | 34 / 953 | menu(3) | – | – | D21 | D22 D31 D23 |
| D31 | prologue: exploration node | 1065 | 10 / 362 | menu(2) | – | – | D24 EV01 EV04 | D32 D33 |
| D32 | prologue: exploration node | 2053 | 32 / 982 | menu(3) | 900 902-903 908 | 900-901 | D31 D34 | D34 |
| D33 | prologue: exploration node | 1704 | 23 / 790 | menu(2) | 904-905 | – | D31 D34 | D35 D34 |
| D34 | prologue: exploration node | 1944 | 31 / 867 | menu(4) | 908-911 | 902 904 907-911 | D32 D33 D35 D36 | D36 EV03 D33 D32 |
| D35 | prologue: exploration node | 2880 | 73 / 1682 | menu(2) | 906 | – | D33 | D34 D3YK |
| D36 | prologue: exploration node | 1638 | 26 / 780 | menu(2) | 907 | – | D34 | D37 D34 |
| D37 | prologue: meeting scene (exit) | 5554 | 198 / 2772 | menu(2) | 912 | – | D36 | S010A |
| D3YK | prologue: meeting scene (exit) | 5228 | 214 / 2533 | – | – | – | D35 | S010 |
| ENG | chapter 1: room visit | 1875 | 70 / 790 | – | – | – | S014 | S014 |
| ENG2 | map event | 2627 | 96 / 1148 | – | 57 | 57 | MAP3 | MAP3 |
| EV01 | prologue: event | 685 | 5 / 181 | – | – | – | D21 | D31 |
| EV02 | prologue: event | 624 | 4 / 146 | – | – | – | D22 | D11 |
| EV03 | prologue: event | 7996 | 285 / 3878 | – | – | 906 908 | D34 | S010 D11 |
| EV04 | prologue: event | 639 | 10 / 285 | – | – | – | D23 | D31 |
| LEH | map event | 5205 | 209 / 2366 | – | – | 20 | MAP2 | YUH01 S017 |
| MAP1 | map screen | 935 | 14 / 204 | menu(2) menu(2) | – | 54 | BLG2 MAP2 S016 | MAP2 BLG2 |
| MAP2 | map screen | 2567 | 58 / 755 | menu(2) menu(2) menu(2) menu(2) menu(2) menu(4) | – | 57 | MAP1 MAP3 MODE(load) NTH YUH | MAP1 YUH LEH NTH MAP3 |
| MAP3 | map screen | 1073 | 18 / 248 | menu(2) menu(2) menu(2) | – | 57 | ENG2 MAP2 MAP4 | MAP2 ENG2 MAP4 |
| MAP4 | map screen | 779 | 11 / 159 | menu(2) menu(2) | – | – | CTD2 MAP3 | MAP3 CTD2 |
| NOVA | story start | 3972 | 99 / 1964 | menu(3) | – | – | NVOP | D21 |
| NTH | map event | 7109 | 316 / 3057 | menu(3) | 56 | 20 56 | MAP2 | YUH01 S017 MAP2 NTH2 |
| NTH2 | map event: scene (exit) | 7220 | 333 / 2914 | menu(4) | 42-47 49-50 | 42-47 49-50 | NTH | S017 |
| S010 | chapter 1: wake-up variant | 2829 | 72 / 1275 | – | 913 | – | D3YK EV03 | S011 |
| S010A | chapter 1: wake-up variant | 4761 | 152 / 2127 | – | 912 | – | D37 | S011 |
| S010B | chapter 1: wake-up variant | 1903 | 28 / 772 | – | – | – | D11 D23 | S011 |
| S011 | chapter 1: scene | 3510 | 117 / 1673 | – | – | 913 | S010 S010A S010B | S012 |
| S012 | chapter 1: deck hub | 1914 | 61 / 740 | menu(3) | 100-102 | 100-102 105-106 | BLG S011 S013 WAL | S015 BLG WAL S013 |
| S013 | chapter 1: deck hub | 1004 | 20 / 313 | menu(2) | 103 | 103 | S012 S014 | S012 S014 |
| S014 | chapter 1: deck hub | 1395 | 39 / 497 | menu(3) | 104-106 | 104-106 | CTD ENG S013 | CTD ENG S013 |
| S015 | chapter 1: scene | 3833 | 99 / 1658 | menu(2) | 100 | – | S012 | YUH01 ALEX |
| S016 | chapter 1: scene | 5832 | 221 / 2778 | – | 800 | 912 | ALEX YUH01 | MAP1 |
| S017 | chapter 2: scene | 3477 | 134 / 1587 | – | – | 912 | LEH NTH NTH2 WAL3 YUH01 | S018 |
| S018 | chapter 2: scene | 5757 | 205 / 2810 | – | – | 54 | S017 | S019 |
| S019 | chapter 2: examination menu | 2676 | 115 / 1019 | menu(3) | 60-62 | 60-62 | S018 | S020 |
| S020 | chapter 2: scene | 4347 | 162 / 2073 | – | – | – | S019 | S021 |
| S021 | chapter 2: scene | 6973 | 250 / 3188 | – | – | – | S020 | S022 |
| S022 | chapter 2: scene | 860 | 26 / 259 | – | – | – | S021 | S023 |
| S023 | chapter 2: scene | 3648 | 138 / 1703 | – | – | – | S022 | S024 |
| S024 | chapter 2: scene | 4588 | 178 / 1662 | – | – | – | S023 | S025 |
| S025 | final scene (ending 1) | 1433 | 34 / 483 | – | 700 | – | S024 | END |
| WAL | chapter 1: room visit | 1797 | 56 / 769 | – | – | – | S012 | S012 |
| WAL3 | map event: scene (exit) | 10787 | 377 / 5020 | – | – | 20 | BLG2 | YUH01 S017 |
| YUH | map event | 575 | 12 / 105 | – | 59 | 59 | MAP2 | MAP2 |
| YUH01 | adult scene (two entries) | 9896 | 467 / 4170 | menu(4) | 17-20 | 17-20 800 | LEH NTH S015 WAL3 | S016 S017 |

**2nd story**

| Script | Role | Size | Text runs / chars | Menus | Flags set | Flags tested | In from | Out to |
|---|---|---:|---:|---|---|---|---|---|
| 201 | branch scene | 5364 | 170 / 2588 | – | – | – | 2ALEX | 2MAP1B |
| 202 | branch scene | 6929 | 244 / 3328 | – | – | – | 2ALEX | HHLEM |
| 203 | branch scene | 6023 | 198 / 2897 | – | – | – | 2ALEX | 2MAP1C |
| 2ALEX | branch point | 985 | 26 / 283 | – | – | 217 219 | 2BRG 2KEI 2LEM 2MAL 2NAT YUKA3 | 202 201 203 |
| 2BRG | map event (phase B) | 1566 | 52 / 622 | – | 213-214 219 | 209 214 218 | 2MAP1 | 2ALEX 2MAP1 |
| 2CAR | map event (phase A) | 1746 | 65 / 565 | menu(2) | 204-205 | – | 2MAP3 | 2MAP3 |
| 2CLD | map event (phase A) | 1761 | 62 / 659 | menu(2) | 202-203 | – | 2MAP2A | 2MAP2A |
| 2D21 | prologue: scene | 1634 | 34 / 658 | menu(2) | – | – | NOVA2 | 2D31 2D22 |
| 2D22 | prologue: scene | 1531 | 52 / 625 | – | – | – | 2D21 | CAP |
| 2D31 | prologue: scene | 1455 | 48 / 571 | – | – | – | 2D21 | CAP |
| 2ENG | map event (phase A) | 863 | 24 / 269 | – | 206 | – | 2MAP3 | 2MAP3 |
| 2KEI | map event (phase B) | 1461 | 42 / 597 | – | 212 214 219 | 209 214 218 | 2MAP1 | 2ALEX 2MAP1 |
| 2LEM | map event (phase B) | 5898 | 250 / 2410 | menu(2) | 210 216 218 | 209 214 218 | 2MAP2B | 2ALEX 2MAP2B |
| 2MAL | map event (phase B) | 6616 | 288 / 2760 | menu(2) | 211 217-218 | 209 214 218 | 2MAP2B | 2MAP2B 2ALEX |
| 2MAP1 | map screen (phase B) | 1133 | 19 / 270 | menu(2) menu(2) menu(2) | – | 212-213 | 2BRG 2KEI 2MAP2B | 2MAP2B 2KEI 2BRG |
| 2MAP1B | map screen (ending A) | 807 | 9 / 136 | menu(2) | – | – | 201 | RO01 |
| 2MAP1C | map screen (ending C) | 790 | 9 / 136 | menu(2) | – | – | 203 | RO01B |
| 2MAP2A | map screen (phase A) | 1999 | 38 / 534 | menu(2) menu(2) menu(4) | – | 202 | 2CLD 2MAP3 COM MODE(load) YUKA | 2CLD 2MAP3 |
| 2MAP2B | map screen (phase B) | 2774 | 63 / 818 | menu(2) menu(2) menu(2) menu(2) menu(2) menu(4) | – | 209-211 215 | 2LEM 2MAL 2MAP1 2NAT MODE(load) MT YUKA3 | 2MAP1 YUKA3 2LEM 2MAL 2NAT |
| 2MAP3 | map screen (phase A) | 1259 | 23 / 308 | menu(2) menu(2) menu(2) menu(2) | – | 204 206 | 2CAR 2ENG 2MAP2A 2MAP4 | 2MAP2A 2CAR 2ENG 2MAP4 |
| 2MAP4 | map screen (phase A) | 781 | 11 / 159 | menu(2) menu(2) | – | – | 2MAP3 | 2MAP3 YUKA2 |
| 2NAT | map event (phase B) | 1097 | 32 / 378 | – | 214-215 | 209 214 218 | 2MAP2B | 2ALEX 2MAP2B |
| CAP | prologue: scene | 6180 | 213 / 2796 | menu(2) | 200-201 | – | 2D22 2D31 | YUKA COM |
| COM | prologue: scene | 2684 | 94 / 1080 | – | – | – | CAP | 2MAP2A |
| HHKEI | ending B chain | 5932 | 248 / 2314 | menu(2) | – | – | HHLEM | HHNAT |
| HHLEM | ending B chain | 3636 | 148 / 1475 | menu(2) | – | – | 202 | HHKEI |
| HHMAL | ending B final | 3554 | 148 / 1340 | – | 702 | – | HHYUKA | END |
| HHNAT | ending B chain | 4829 | 196 / 1969 | menu(2) | – | – | HHKEI | HHYUKA |
| HHYUKA | ending B chain | 1916 | 82 / 641 | – | – | – | HHNAT | HHMAL |
| MON01 | scene (phase A exit) | 1283 | 37 / 364 | – | – | – | YUKA2 | MT |
| MT | scene (phase A exit) | 2802 | 88 / 1212 | – | – | – | MON01 | 2MAP2B |
| NOVA2 | story start | 1826 | 39 / 734 | menu(2) | – | – | NVOP | 2D21 |
| RO01 | ending A chain | 2241 | 84 / 747 | – | – | – | 2MAP1B | RO02 |
| RO01B | ending C chain | 3126 | 124 / 1144 | – | – | – | 2MAP1C | RO02B |
| RO02 | ending A chain | 3041 | 120 / 1221 | – | – | – | RO01 | RO03 |
| RO02B | ending C chain | 3177 | 126 / 1297 | – | – | – | RO01B | RO03B |
| RO03 | ending A chain | 4734 | 192 / 2062 | – | – | – | RO02 | RO04 |
| RO03B | ending C chain | 3465 | 132 / 1426 | – | – | – | RO02B | RO04B |
| RO04 | ending A final | 2843 | 89 / 1115 | – | 701 | – | RO03 | END |
| RO04B | ending C final | 2756 | 96 / 983 | – | 703 | – | RO03B | END |
| YUKA | prologue: scene | 3194 | 114 / 1262 | – | – | – | CAP | 2MAP2A |
| YUKA2 | map event (phase A) | 5703 | 238 / 2309 | menu(2) | 207-208 | 203 | 2MAP4 | MON01 |
| YUKA3 | map event (phase B) | 3339 | 148 / 1449 | – | 209 | 203 209 214 218 | 2MAP2B | 2ALEX 2MAP2B |

**3rd story**

| Script | Role | Size | Text runs / chars | Menus | Flags set | Flags tested | In from | Out to |
|---|---|---:|---:|---|---|---|---|---|
| 301 | scene | 824 | 17 / 268 | – | – | – | NOVA3 | 3K01 |
| 3H | final scene (ending 3) | 4920 | 198 / 1966 | – | 704 | – | 3HL02 3HM02 3HN02 3HY02 | END |
| 3HK | scene | 2676 | 106 / 1001 | – | – | – | 3K01 | SELC |
| 3HL01 | adult scene, round 1 | 3316 | 90 / 1203 | – | – | 301-304 | SELC | SELC2 SELC |
| 3HL02 | adult scene, round 2 | 4049 | 134 / 1700 | – | – | 306-309 | SELC2 | 3H SELC2 |
| 3HM01 | adult scene, round 1 | 3059 | 99 / 1125 | – | – | 301-304 | SELC | SELC2 SELC |
| 3HM02 | adult scene, round 2 | 2794 | 89 / 1126 | – | – | 306-309 | SELC2 | 3H SELC2 |
| 3HN01 | adult scene, round 1 | 3416 | 105 / 1376 | – | – | 301-304 | SELC | SELC2 SELC |
| 3HN02 | adult scene, round 2 | 3497 | 111 / 1493 | – | – | 306-309 | SELC2 | 3H SELC2 |
| 3HY01 | adult scene, round 1 | 4511 | 162 / 1854 | – | – | 301-304 | SELC | SELC2 SELC |
| 3HY02 | adult scene, round 2 | 3323 | 133 / 1346 | – | – | 306-309 | SELC2 | 3H SELC2 |
| 3K01 | scene | 2228 | 90 / 973 | – | – | – | 301 | 3HK |
| NOVA3 | story start | 2198 | 72 / 960 | – | – | – | NVOP | 301 |
| SELC | selection menu, round 1 | 4095 | 134 / 1600 | menu(4) | 300-304 314-317 | 300-304 314-317 | 3HK 3HL01 3HM01 3HN01 3HY01 | 3HN01 3HM01 3HL01 3HY01 |
| SELC2 | selection menu, round 2 | 2887 | 106 / 1243 | menu(4) | 305-313 | 305-313 | 3HL01 3HL02 3HM01 3HM02 3HN01 3HN02 3HY01 3HY02 | 3HN02 3HM02 3HL02 3HY02 |

## 11. Flag table (verified sets and tests; meanings inferred)

95 flags occur. "Set" / "Tested" list the scripts. All assignments set the flag to 1 except R100
(also cleared).

| Flag | Set in | Tested in | Meaning |
|---|---|---|---|
| R0 | `MODE` | `MODE` | a save file exists (any of R1000–R1002): shows "continue" |
| R17 | `YUH01` | `YUH01` | scene stage 1 done (item 0 chosen); unlocks items 1, 2 |
| R18 | `YUH01` | `YUH01` | stage: item 2 chosen once (selects segment 5, then 6) |
| R19 | `YUH01` | `YUH01` | stage: item 1 progress (segment 3) |
| R20 | `YUH01` | `YUH01`, `LEH`, `NTH`, `WAL3` | scene `YUH01` reached its last stage = has been seen; map-phase exits skip it when set |
| R42–R47, R49, R50 | `NTH2` | `NTH2` | stage flags of the `NTH2` scene menu (16 segments ordered by them); R50 unlocks the last item |
| R54 | `BLG2` | `BLG2`, `MAP1`, `S018` | bridge event of the map phase seen; text variant in `S018` |
| R55 | `BLG2` | – | chose "go with Marie" (never tested) |
| R56 | `NTH` | `NTH` | listened to Nat; swaps menu item 0/1 and the meaning of "leave" |
| R57 | `ENG2` | `ENG2`, `MAP2`, `MAP3` | engine-room event seen; opens room 04 (`LEH`), closes the engine room |
| R58 | `CTD2` | `CTD2` | catapult event seen (short text afterwards) |
| R59 | `YUH` | `YUH` | Yuka's room visited (short text afterwards) |
| R60 | `S019` | `S019` | capsule area examined |
| R61 | `S019` | `S019` | parts under the robot examined |
| R62 | `S019` | `S019` | robot looked at once |
| R100 | `S012` (=1), `S015` (=0) | `S012` | deck-1 introduction given; cleared when going to Yuka's room (no later test can see it: `S012` is not entered again) |
| R101 | `S012` | `S012` | bridge visited (tour) |
| R102 | `S012` | `S012` | access room visited (tour) |
| R103 | `S013` | `S013` | deck-2 introduction given |
| R104 | `S014` | `S014` | deck-3 introduction given |
| R105 | `S014` | `S014`, `S012` | catapult deck visited (tour) |
| R106 | `S014` | `S014`, `S012` | engine room visited (tour); R101 & R102 & R105 & R106 → `S015` |
| R200 | `CAP` | – | went to Yuka (never tested; the effect is L+2 and the jump) |
| R201 | `CAP` | – | did not go (never tested) |
| R202 | `2CLD` | `2MAP2A` | hypersleep room visited |
| R203 | `2CLD` | `YUKA2`, `YUKA3` | hypersleep room examined thoroughly: text variants |
| R204 | `2CAR` | `2MAP3` | cargo room visited |
| R205 | `2CAR` | – | capsule examined (never tested) |
| R206 | `2ENG` | `2MAP3` | engine room visited |
| R207 | `YUKA2` | – | took Yuka to safety (never tested; L+2) |
| R208 | `YUKA2` | – | went to the scream (never tested) |
| R209 | `YUKA3` | `2MAP2B` + the six phase-B events | Yuka's room visited (phase B); part of the exit condition |
| R210 | `2LEM` | `2MAP2B` | Remy's room visited |
| R211 | `2MAL` | `2MAP2B` | Marie's room visited |
| R212 | `2KEI` | `2MAP1` | meeting-room event seen |
| R213 | `2BRG` | `2MAP1` | bridge event seen |
| R214 | `2KEI`, `2BRG`, `2NAT` | the six phase-B events | one crew event seen; part of the exit condition |
| R215 | `2NAT` | `2MAP2B` | lift-B event seen |
| R216 | `2LEM` | – | comforted Remy (never tested; L+1) |
| R217 | `2MAL` | `2ALEX` | did as Marie said → **ending 2B** |
| R218 | `2LEM`, `2MAL` | the six phase-B events | Remy's or Marie's room visited; part of the exit condition |
| R219 | `2KEI`, `2BRG` | `2ALEX` | last crew event was on deck 1: background in `2ALEX` |
| R300 | `SELC` | `SELC` | round-1 introduction given |
| R301–R304 | `SELC` | `SELC`, `3H?01` | round 1: Nat / Marie / Remy / Yuka chosen; all four → `SELC2` |
| R305 | `SELC2` | `SELC2` | round-2 introduction given |
| R306–R309 | `SELC2` | `SELC2`, `3H?02` | round 2: the same four; all four → `3H` |
| R310–R313 | `SELC2` | `SELC2` | comment after round-2 scene n given |
| R314–R317 | `SELC` | `SELC` | comment after round-1 scene n given |
| R700 | `S025` | `END` | 1st story finished |
| R701 | `RO04` | `END` | ending 2A |
| R702 | `HHMAL` | `END` | ending 2B |
| R703 | `RO04B` | `END` | ending 2C |
| R704 | `3H` | `END` | 3rd story finished |
| R800 | `S016` | `YUH01` | map phase of the 1st story has begun (second entry of `YUH01`) |
| R801 | `MODE` | `NVOP` | playing the 2nd story |
| R802 | `MODE` | `NVOP` | playing the 3rd story |
| R900 | `D32` | `D32` | robot examined |
| R901 | **never set** | `D32` | capsule examined — see §14 |
| R902 | `D32` | `D34` | cargo room visited |
| R903 | `D32` | – | left the cargo room by the menu (never tested) |
| R904 | `D33` | `D34` | engine door visited |
| R905 | `D33` | – | left the engine room without examining (never tested) |
| R906 | `D35` | `EV03` | went towards the voice |
| R907 | `D36` | `D34` | side passage (hangar) visited |
| R908 | `D32`, `D34` | `D34`, `EV03` | elevator available |
| R909 | `D34` | `D34` | first-visit text of the hub shown |
| R910 | `D34` | `D34` | "all three places seen" text shown |
| R911 | `D34` | `D34` | elevator text shown |
| R912 | `D37`, `S010A` | `CTD`, `ALEX`, `S016`, `S017` | first met in the hangar (prologue exit A): text variants |
| R913 | `S010` | `S011` | prologue exit through `S010`: text variant |
| R1000–R1002 | `save-check` | `MODE` | `FLAG0`–`FLAG2` exist |
| R1003 | `save-check` | `MODE` | `FLAG3` exists: 2nd story |
| R1004 | `save-check` | `MODE` | `FLAG4` exists: 3rd story |
| R1005 | `save-check` | `MODE` | `FLAG5` exists: Sound, Graphic |

Number ranges follow the scripts' purpose (**inferred**): 17–62 map-phase and scene flags of the
1st story, 100–106 the tour, 200–219 the 2nd story, 300–317 the 3rd, 700–704 endings, 800–802 mode,
900–913 the prologue of the 1st story, 1000–1005 `save-check`.

## 12. Variables (verified)

| Var | Written by | Tested in | Use |
|---|---|---|---|
| A | `input A 1` (11 map scripts) | the map scripts | region clicked on the map |
| C | `NV.INI` | `NV.INI` | retry counter of the copy-protection prompt |
| L | `NOVA2`, `2D21`, `CAP`, `2CLD`, `YUKA2`, `2LEM` | `2ALEX` | 2nd-story score (§5) |
| N | `menu2` (interpreter); `NV.INI` | `MODE`, `SOUND`; `NV.INI` | noun index: save file, track number; in `NV.INI` the result of the protection code (15 = ok) |
| S | `menu` (interpreter) | 45 scripts | index of the chosen menu item |
| U | the three save maps and six scripts that lead to them | `MAP2`, `2MAP2A`, `2MAP2B`, `2ALEX` | "start the music on entry" (§3); `2ALEX` starts NV04 if set and does not clear it |
| V | `menu2` (interpreter) | `MODE`, `SOUND`, `H` | verb index |

No script uses `branch-var`, arithmetic beyond `L += n`, or any other letter.

## 13. Plug-in calls seen in the scripts (verified calls; semantics in plugins.md)

| Plug-in | Loaded at | Calls | Where |
|---|---|---|---|
| `ACTE1.tcm` | 256 | `"INIT"`; `"GET n x y w h"`; `"PUT n x y ,FREE n"` — save / restore a screen rectangle (text window: `GET 0 7 296 72 104`; `END`: `GET 0 0 160 69 200`) | 111 scripts |
| `ChgFontH.tcm` | 8448 | `exec-mem 8448 1` once per script | 112 scripts |
| `InputNam.tcm` | 9984 | §2.1 | loaded by `RUN`, called by `MODE` |
| `PALCH.TCM` | 8704 | `exec-mem 8704 14 11 9 10 6` once, before the jump to `S011` | `S010`, `S010A`, `S010B` |
| `WHITEH.TCM` | 5376 | `exec-mem 5376 0 8` (proc 7) and `5376 1 8` (proc 8): a white flash, used with `text-C6 0 0 159 99 7 / 15` | `MON01` |

## 14. Oddities and defects in the scripts

| Script | Offset | What | Effect |
|---|---|---|---|
| `D32` | 02D1, 05B5 | **R901 is tested but never set.** Menu item 1 ("examine the capsule") is conditional on R901 = 0 and segment 1 (robot) leaves to `D34` only if R901 = 1. Segment 2 (capsule) was evidently meant to set it, as segment 1 sets R900. | The capsule item never disappears; examining the robot after the capsule does not leave the room (examining the capsule after the robot does, through R900). The room can always be left by item 2. The English translation fixes it: its `D32` has `R901=1` at the start of segment 2. |
| `202` | 1AFB | second `mes-jump` (`2MAP1C`) directly after `mes-jump "HHLEM"` | dead code; an earlier design in which ending B went through a map |
| `HHLEM` | 080A, 0E1C | `mes-jump "2MAP1C"` after `mes-jump "HHKEI"` | dead code |
| `HHKEI` | 0B86, 1716 | `mes-jump "\MES\2MAP2C.MES"` after `mes-jump "HHNAT"` | dead code; **`2MAP2C.MES` does not exist** |
| `HHNAT` | 0FCB, 12C5 | `mes-jump "\MES\2MAP3B.MES"` after `mes-jump "HHYUKA"` | dead code; **`2MAP3B.MES` does not exist** |
| `2MAP1B` | 0275 | `mes-jump "\MES\2MAP2C.MES"` after `mes-jump "RO01"` | dead code, missing target |
| `2MAP1B`, `2MAP1C` | 0238 | load `B:MAP2.GPC` and `MAPWIN` (deck-2 map) just before jumping to `RO01` / `RO01B` | remnant of the same design: the deck-2 map is shown for a moment, no map script follows |
| `2ALEX` | 03C3 | third test is `L<=5` after `L>=5` | harmless; L = 5 is taken by the second test |
| `2MAL` | 18BE | the R217 branch returns to the map without the exit test all other phase-B exits have | the branch to `2ALEX` is delayed to the next event (§5) |
| `2MAP2A`, `2MAP3` | 02BA; 02FD, 03E1 | visited / unvisited states of a region written as two `if` blocks, the second unconditional | answering "no" to "enter?" also prints the plain description |
| `CAP`, `YUKA2`, `2CAR`, `2LEM`, `BLG2`, `D32`, `D33` | – | flags set and never tested: R200, R201, R207, R208, R205, R216, R55, R903, R905 | none |
| `S015` | 0C03 | `R100=0` before leaving to `YUH01`; R100 is only tested in `S012`, which is not entered again | none |
| `NOVA` | 06FF–0F70 | three menu items, three text blocks, one destination (`D21`) | none (text variation) |
| `MODE` | 0151–0C02 | segments 1–3 are three copies of about 910 bytes differing in one flag assignment | none |
| `MODE`, `2KEI` … | – | `＠` (no-operation code) around flag assignments, e.g. `MODE` 0024, 04E0 | none |
| `END` | 0FED | ends in an empty endless loop | reset required after an ending (§8) |
| `END` | 0000 | sets drive slot 0 only | the picture disk of the previous script stays selected (disks.md) |
| `YUKA2` | 0003 | `set-drive 1 2` although the script loads no picture from unit 1 | on floppies the change to disk C is asked for one script early (`MON01` needs it) |
| `NVOP` 0118, `D21` 0124, … | | `sound 3` is used 16 times in the game after `sound "file"` where `sound 1` is the usual form | meaning of `sound 3`: advbios.md |
| `ALEX` | – | one `sound 1` more than in the English version of the script | none known |
| `BLG2` 07D6, `S018` 1679, `NOVA3` 0891 | | block-structure defects (mes-format.md §6) | none |
| 19 scripts | end | an extra empty segment before the end marker (`FF FF FF FF FF FE`) | none; e.g. `MAP1`, `S012`, `SELC`, `SOUND` (`reach.txt` lists them) |
| disks | – | `NV19A.GPC` (disk B) is not referenced by any script | unused picture |

No segment is unreachable for structural reasons: every script with later segments has a
`seg-call`, and no segment is shadowed by an earlier one with weaker conditions (checked by
`mesgraph.py`; `NTH2`, `S019` and `YUH01` rely on the first-match order).

## 15. Differences in the English translation's scripts (verified)

117 scripts (no `RUN.MES`, no `NV.INI` in our import). Control flow, flags, pictures, music and
drive commands are identical statement for statement to the Japanese scripts, with three
exceptions: `D32` sets R901 (§14), `ALEX` lacks one `sound 1`, and the default name in `MODE`.
The three block-structure defects are repaired. Offsets differ throughout because the text does.

## 16. Open questions

* `InputNam.tcm`: the meaning of arguments 1, 2 and 8 (0, 0, 0) — plugins.md.
* `PALCH.TCM 14 11 9 10 6` and `WHITEH.TCM n 8`: argument meanings — plugins.md.
* Why `NTH` "leave" without having listened (R56 = 0) leads to the scene `NTH2` while "leave" after
  listening returns to the map: read from the flags only; the story reason was not checked in the
  text.
* Whether the missing `2MAP2C` / `2MAP3B` exist in any other release (the Windows release's script
  list has no such names either: `resources/inventory.tsv`).
* The 2nd-story score: the arithmetic is verified, but what the six choices have in common in the
  story (why they count towards ending 2A) was not worked out from the text.
* `sound 3` versus `sound 1` after loading a file (16 uses, e.g. `NVOP`, `D21`): see advbios.md.
