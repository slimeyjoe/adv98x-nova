# Disks and picture files, seen from the scripts

NOVA came on four floppies. Disk A is the game disk (system, interpreter, plug-ins, all scripts,
music, hit tables, saves, and the pictures used everywhere); B, C and D carry only `\GPC\`. This
note says which picture is where, how the scripts choose a disk, and how an engine that has all
files on one medium should resolve a picture name.

Sources: `resources/inventory.tsv` (release `pc98`), the parsed scripts, and
`re-tools/mesgraph.py`, whose `pictures.tsv` and `reach.txt` (in `resources/derived/scripts/`)
contain every number quoted here. AdvBIOS's side (drive handling, the prompt) is in
the engine's `docs/re/advbios.md` §8. **verified** = checked on all scripts / files or read in code;
**inferred** = not proven.

## 1. What is on which disk (verified)

122 picture files, 102 distinct names. Disk A: 21 files, 522 354 bytes; B: 47, 1 125 710;
C: 27, 978 741; D: 27, 1 161 838.

| On disks | Names (`.GPC`) | Remarks |
|---|---|---|
| A | BL CP NV01 NV01L NV02 NV04 NV05 NV06 NV06A NV07 NV08 NV09 NV10 NV19 NV27 NV35 NV43 NVWIN OPPAL | backgrounds, portraits, text window, logo, opening palette |
| A, D | NV00 NV11 | identical files; never loaded from D (§5) |
| B | MAP3 MAP4 NV03A–NV03F NV03ALL NV19A NV20 NV20A NV20B NV21 NV28 NV28A–C NV29 NV35B NV36 NV36A NV36B NV37 NV43B NV44 NV44A NV44B NV44Z NV45 NV52–NV54 NV55A NV55B NV56 ROGO SAVE | 1st-story events, opening, title background, maps of decks 3 and 4 |
| B, C | MAP1 MAP2 MAPWIN NV33 **NV43A** | identical except NV43A (§4) |
| B, C, D | NV03 NV99 | identical; NV99 is the staff-roll background |
| B, D | NV49 NV49A | identical |
| C | NV16A NV16B NV17 NV23 NV24 NV32A NV32B NV41A NV41B NV48A NV48B NV51A NV51B | 2nd-story events |
| C, D | NV18 NV25 NV26 NV31 NV40A NV40B NV42 | identical |
| D | NV12A NV12B NV13 NV14 NV15A NV15B NV22 NV30 NV34 NV38 NV39 NV46 NV47 NV50 | 3rd-story events |

All copies of a name are byte-identical (same MD5) except `NV43A.GPC`.

Why the copies exist follows from the scripts (**inferred** from the verified usage below): a
script works with one picture disk in drive 2, so whatever it needs "from B:" must be on that disk.
`NV03` (meeting room) and `NV99` are needed with every disk; the deck-1/deck-2 maps and `MAPWIN`
are shown by 2nd-story scripts that run with disk C; `NV18`, `NV25`, `NV26`, `NV31`, `NV40A/B`,
`NV42` are used by 2nd-story scripts (disk C) and 3rd-story scripts (disk D).

## 2. How the scripts select a disk (verified)

Two mechanisms, always used together:

1. **The drive letter in the file name.** Of the 1 038 `image-file` statements, 619 have no drive
   letter (`\GPC\NV01.GPC`) and 419 start with `B:` (`B:\GPC\NV03.GPC`). No other letter occurs.
   Music (`\MUS\…`), hit tables (`\CLM\…`), plug-ins (bare names) and scripts (`\MES\…`) never have
   one.
2. **`set-drive slot value`** — 254 statements, four forms only:

   | Statement | Count | Meaning |
   |---|---:|---|
   | `set-drive 0 0` | 125 | unit 0 (the boot drive, "A:") holds disk #A |
   | `set-drive 1 1` | 98 | unit 1 ("B:") holds disk #B |
   | `set-drive 1 2` | 21 | unit 1 holds disk #C |
   | `set-drive 1 3` | 10 | unit 1 holds disk #D |

   The value is a **disk number** (0–3 = A–D), the slot a **drive unit**. This is what AdvBIOS does
   with it (advbios.md §8: INT F2h AH=04h stores the number at DS:03C2+unit and, on floppies, reads
   the volume label of the drive and asks for "disk #Y in drive X" until label and number match; the
   same check runs before every file open) and it agrees with the data: under this reading every
   picture reference of every script finds its file (§3).

Every script except `END` and `NV.INI` begins with `set-drive 0 0` and `set-drive 1 n`
(`NV.INI` sets both a few statements later). The choice of n per script:

| n | Disk | Scripts |
|---:|---|---|
| 1 | B | 92 scripts: all of the 1st story, the system scripts, the 2nd story up to `2MAP4` and its map phases, `201`–`203`, `2ALEX`, the 3rd story's `NOVA3`, `301`, `3K01`, `SELC`, `3H?01` |
| 2 | C | 18: `YUKA2`, `MON01`, `MT`, `2MAP1B`, `2MAP1C`, `RO01`–`RO04`, `RO01B`–`RO04B`, `HHLEM`, `HHKEI`, `HHNAT`, `HHYUKA`, `HHMAL` |
| 3 | D | 7: `3HK`, `SELC2`, `3HN02`, `3HM02`, `3HL02`, `3HY02`, `3H` |

Only **`H`** (CG mode) changes the disk in mid-script: `set-drive 1 2` after the pictures of disk B,
`set-drive 1 3` after those of disk C, and `set-drive 0 0`, `set-drive 1 1` at the end of each of
its three display segments (14 `set-drive` statements in all).

**`END`** sets only `set-drive 0 0` and then loads `B:\GPC\NV99.GPC` with whatever disk its
predecessor selected: B after `S025`, C after `RO04`, `RO04B`, `HHMAL`, D after `3H`. The file is on
all three disks, identical.

### 2.1 Where the player changes disks (floppy play; verified from the graph)

| Transition | Change |
|---|---|
| `2MAP4` → `YUKA2` | B → C (asked for by `YUKA2`, which itself loads nothing from unit 1; `MON01` does) |
| `MT` → `2MAP2B` | C → B |
| `201` → `2MAP1B`, `202` → `HHLEM`, `203` → `2MAP1C` | B → C, for the rest of the 2nd story |
| `3K01` → `3HK` | B → D |
| `3HK` → `SELC` | D → B |
| last `3H?01` → `SELC2` | B → D, for the rest of the 3rd story |
| `H` | B → C → D → B on every run |

The 1st story never leaves disk B. Loading a save needs nothing special: the save holds the two
drive bytes, and the three scripts that can be saved in (`MAP2`, `2MAP2A`, `2MAP2B`) set 0 / 1 at
their start anyway.

### 2.2 "Insert disk" prompts

**No script contains a disk prompt** for picture disks. There is no text, no wait and no test
around a disk change: the script states which disk it expects (`set-drive`) and AdvBIOS does the
asking (box 「ドライブＸに、ディスク＃Ｙを入れてください。」, advbios.md §8.3). The only scripted
prompt is in `NV.INI`, part of the copy-protection loop: a message to insert disk #A or #B and
press space, repeated until the check succeeds, `exit` after two failures (interpreter.md §7).

For a new engine this means: `set-drive` needs no user interaction at all.

## 3. Resolution rule for an engine with all files on one medium

Keep the four disks as four directories (as `resources/original/pc98/A..D` already are) and keep
the two drive bytes of the interpreter state (0xFD, 0xFE; initial 0 and 1; part of a save).

```
resolve(name):                       # the operand of image-file
    unit = 0
    if name[1] == ':':               # "B:\GPC\X.GPC"
        unit = (letter - 'A') & 1    # A: -> 0, B: -> 1   (AdvBIOS: (letter - 1) & 1)
        name = name[2:]
    disk = "ABCD"[drive_byte[unit]]  # set by set-drive unit value
    return <disk>/<name without the leading backslash>
```

`set-drive slot value` only stores `drive_byte[slot & 1] = value`.

**Verification** (`mesgraph.py`, `pictures.tsv`; the drive state is followed statement by statement
inside each script and across `mes-jump` edges to a fixpoint):

| | |
|---|---:|
| `image-file` references in the 119 scripts | 1 038 |
| distinct names referenced | 101 |
| resolved to exactly one existing file | **1 038** |
| not found / drive unknown | 0 |
| no letter → disk A | 619 |
| `B:` → disk B | 242 |
| `B:` → disk C | 110 |
| `B:` → disk D | 66 |
| `B:` → one of B, C, D by predecessor (`END`: `NV99`, same file on all three) | 1 |

The rule is exact in the other direction too: no `B:` reference names a file that is only on
disk A, and no letterless reference names a file that is missing from A. The English scripts give
the same result (1 037 references, one fewer because `RUN.MES` with `CP.GPC` is not in that set).

**Simpler alternative (also verified):** put all pictures in one directory and resolve by bare
name, ignoring drive letters and `set-drive`. This is correct for all 101 names: every duplicated
name has identical files, and the one exception, `NV43A`, has two files that show the same picture
(§4). The four-directory rule is still the recommended one — it is what the original does, it needs
no decision about `NV43A`, and it keeps the files as shipped.

## 4. `NV43A.GPC`: two files, one picture (verified)

| | Disk B | Disk C |
|---|---|---|
| size, MD5 | 21 597, `593f75df…` | 22 831, `747da26e…` |
| stored rectangle | 304×358 at (272, 42) | 640×400 at (0, 0) |
| used by (drive state) | `LEH`, `NTH`, `NTH2`, `WAL3`, `YUH01`, `S024` (`set-drive 1 1`) | `HHYUKA`, `HHMAL` (`set-drive 1 2`) |
| references | 6 | 3 |

Which file a reference means is decided by the drive state, and independent evidence agrees: the
other `B:` pictures of `NTH2`, `S024`, `WAL3`, `YUH01` exist only on disk B, those of `HHYUKA`
(`NV48A/B`) and `HHMAL` (`NV32A/B`) only on disk C (`LEH` and `NTH` have no other `B:` picture and
rest on `set-drive 1 1` alone). So the rule of §3 picks B's file for the six 1st-story references
and C's for the three in the ending-B chain.

But the choice does not matter on screen: decoded and placed at their rectangles on the 640×400
screen, **the two files are the same picture — 0 of 256 000 pixels differ in palette index, and
the 16-colour palettes are identical** (`reach.txt`: "NV43A.GPC on screen"; from the decoded
pictures in `resources/derived/images/gpc/`). The picture is a portrait drawn over a background
with `image-show 1` (colour 0 transparent, graphics-formats.md §6.2); disk C's file simply stores
it on a full canvas padded with colour 0, disk B's as the cropped rectangle. It is the same
artwork saved twice with different settings, not two versions.

## 5. Files nobody loads (verified)

| File | Remark |
|---|---|
| B: `NV19A.GPC` | not referenced by any script (a small overlay, 136×122; unused) |
| D: `NV00.GPC`, `NV11.GPC` | referenced only without drive letter → read from A. The 3rd-story scripts that run with disk D (`3HK`, `SELC2`, `3H`) use them, which may be why they were put on D (**inferred**); the scripts do not use the copies |
| D: `NV49.GPC`, `NV49A.GPC` | loaded only while disk B is selected (`NV49` by `3HY01` and `H`, `NV49A` by `H`) |
| C: `NV33.GPC` | loaded only by `2MAL`, `3HM01` and `H` while disk B is selected |

All 28 music files and the four hit tables on disk A are used; no script refers to a picture,
music file, plug-in or hit table that does not exist. The only missing files referenced are the
scripts `2MAP2C.MES` and `2MAP3B.MES`, in dead code (script-catalog.md §14).

## 6. Hard-disk installs and other releases

* **PC-98 hard-disk install** (`INSTH.EXE` on disk A, "Adv98V ハードディスク インストール プログラム
  Version 1.01"): copies the disks, asking for each (`ドライブ %c: に ディスク #%c を…`), to the hard disk
  (one directory tree — **inferred** from its messages; the program was not analysed). AdvBIOS detects a non-removable boot drive ("hard-disk mode", advbios.md §8.1); in
  that mode it **drops the `X:` prefix of every name** and never checks or prompts, so
  `B:\GPC\NV43A.GPC` becomes `GPC\NV43A.GPC` in the install directory and `set-drive` has no
  effect. The scripts are not changed for this. A hard-disk install therefore has exactly one
  `NV43A.GPC`; which of the two it is depends on the installer's copy order and overwrite behaviour,
  which were not analysed (**open**) — and it is irrelevant for the display (§4).
* **English translation** (scripts in `resources/original/en/MES/`): the scripts **still use
  `B:`** and the same `set-drive` statements — 419 `B:` references and `set-drive 0 0` / `1 1` /
  `1 2` / `1 3` exactly as in the Japanese scripts (the counts differ only by the missing `RUN.MES`
  and `NV.INI`). It relies on AdvBIOS's hard-disk mode like any installed copy. **Which `NV43A` its
  picture directory holds cannot be determined here**: the translation's pictures are not in our
  import (only its 117 scripts are). By §4 it makes no visible difference.
* **Windows release** (`resources/original/win/`, pictures converted to Pi, one directory): one
  `NV43A.PI`, 292×351 at (279, 49). Decoded, it is again the same picture (0 differing pixels
  against either PC-98 file); it is stored cropped to its non-zero pixels, as that conversion does
  with every overlay (graphics-formats.md), so it does not tell which PC-98 file was the source.

## 7. Open questions

* The copy order and overwrite behaviour of `INSTH.EXE` (which `NV43A.GPC` an installed PC-98 copy
  keeps). No practical consequence.
* The volume labels of the four disks (AdvBIOS identifies a disk by the first 10 characters of the
  label and its 11th character; our import has files, not labels).
* Whether a name without drive letter is always read from the boot drive in floppy mode, or from
  the current DOS drive (advbios.md §8.1 says boot drive + unit 0). The data cannot distinguish:
  every letterless picture is on A.
