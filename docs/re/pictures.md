# NOVA's pictures: the Windows release's Pi files, the disk rule, the table of all pictures

What the engine's `docs/re/graphics-formats.md` (the GPC format and the original draw routine)
says about this game's pictures in particular. The sections keep the numbers they have there, so
a "§" without a document is one of these or of that document. The verification tool
`re-tools/gpc_verify.py` (the engine's) checks the GPC decoder against the original's code; its
second witness, the Windows release's Pi files, is this game's: `re-tools/pi.py`.

Marking used below: **[V]** verified (against all files, the original code, or both, as
stated), **[I]** inferred, **[?]** unknown.

The Pi description used is Kirinn Bunnylin's <https://mooncore.eu/bunny/txt/pi-pic.htm>; the
decoder here was written from it and checked against the game's files; no code was copied.

## 5. Pi files of the Windows release

### 5.1 Variant

Standard 16-colour Pi, big-endian header: **[V]** unless marked.

```
"Pi"
comment bytes ... 0x1A
dummy comment bytes ... 0x00
u8  mode            = 0 in all 123 files
u8  aspect x, y     = 0, 0
u8  planes          = 4
4   saver id        = "PC98" (96 files) or "MG  " (27 files)
u16 n, n bytes      saver-specific data: empty, or 5 bytes (32 files)
u16 width, u16 height
48  palette, 16 x (R, G, B) bytes
... bit stream, MSB first
```

- Saver data, when present, is `01, u16 x, u16 y` (big-endian): the screen
  position of a cropped picture. Interpreting it this way makes all 32
  cropped PIs land exactly on the corresponding GPC pixels. **[V]** The meaning
  of the leading `01` is **[I]** (a tag for "position").
- `"PC98"` files are conversions of the PC-98 art (plus the Windows-only
  `AREA`, `HSS01/02`, `NV56A`): empty comment, palette bytes are `v << 4`
  (low nibble 0). `"MG  "` files (the new Windows art `NV99A`...,
  `NVOP01/02`, and the re-edited `ROGO`) have arbitrary 8-bit palette bytes;
  `ROGO.PI` alone has a comment (`User:KIN`, `MPS.EXE version 1.02`, plus a
  `-magFF0000` dummy field). **[V]**
- Compression is the textbook Pi scheme (per-colour move-to-front colour codes
  `1x / 00x / 010xx / 011xxx`, five position codes `00 / 01 / 10 / 110 / 111`
  = 2-or-4 back / one row up / two rows up / up-right / up-left, Elias-gamma
  style pair counts, the first two pixels virtually filling two rows above the
  picture). No deviations found. **[V]** by the pixel equality below. The
  stream is followed by 3-6 unused bytes.

### 5.2 GPC vs PI results (`re-tools/gpc_verify.py`)

| check | result |
|---|---|
| GPC contents decoded with the stream consumed to its last byte | 103 / 103 |
| original AdvBIOS decoder under Unicorn: 4 planes + palette buffer equal to `gpc.py` | 103 / 103 |
| GPCs with a same-named PI | 85 |
| ... identical rectangle and pixels | 49 |
| ... identical on screen, PI has a different rectangle (cropped to the non-zero bounding box, or uncropped) | 32 |
| ... real pixel differences | 4 |
| ... palette identical / different | 80 / 5 |
| A+B half-screen GPC pairs equal to the single full-screen PI | 9 / 9 (pixels and both palettes) |
| GPCs with no PI counterpart at all | 0 (the 18 "no PI" files are exactly those 9 pairs) |

"On screen" = both pictures placed at their own x,y on a 640x400 canvas of
colour 0. In all 32 cropped cases everything the GPC has outside the PI
rectangle is colour 0. **[V]**

The differences, all in the data rather than the decoder (the original code
produces the same GPC pixels) **[V]**:

| picture | difference |
|---|---|
| `NV10` | 1 stray pixel in the GPC at (617,399), colour 1; absent in the PI |
| `NV03E` | 1 stray pixel at (222,399), colour 1; absent in the PI |
| `NV03F` | 1 stray pixel at (639,366), colour 11; absent in the PI |
| `ROGO` | 311 pixels in 345,272-437,287: the copyright line "(C)1993" was redrawn as "(C)1993.1996"; palette entry 14 is 000 on PC-98 and (7,15,7) on Windows |
| `MAP1`-`MAP4` | pixels identical; palette entries 0 and 1 are (0,5,5) and (0,4,4) on PC-98 but black on Windows (as 0GRB words: 505, 404 vs 000, 000) |

### 5.3 Windows-only pictures (no GPC of that name)

`AREA`, `HSS01`, `HSS02`, `NV56A`, `NV99A`-`NV99R`, `NV99CPY`, `NV99SC1`,
`NV99SC2A/B/C`, `NV99SC3`, `NVOP01`, `NVOP02` (30 files), plus the nine merged
full screens `NV12 NV15 NV16 NV32 NV40 NV41 NV48 NV51 NV55`. All are 640x400.
**[V]** Whether the PC-98 version shows equivalent content by other means
(text-layer drawing, script effects) is outside this document. **[?]**

### 6.4 `NV43A.GPC`: disk B vs disk C

Same picture, different packaging. **[V]**

| | disk B | disk C |
|---|---|---|
| file size | 21 597 | 22 831 |
| rectangle | 304x358 at 272,42 | 640x400 at 0,0 |
| interleave | 1 | 1 |
| palette | identical | identical |
| non-zero pixels | bounding box 279,49-570,399 | same box, same pixels |

Placed on a colour-0 canvas the two are pixel-identical (0 differing pixels),
and both equal `NV43A.PI` (292x351 at 279,49). The only functional difference:
drawn *opaque*, the disk C copy also clears the rest of the screen to colour 0,
while the disk B copy only touches its rectangle; drawn masked they behave the
same. Which one a script expects depends on the draw mode it uses. **[?]**

## 7. Picture table

Columns: `il` = row interleave step; `filters` = set of row filter bytes
occurring; palette notes show entry 0 and any deviation of entries 1-5 from
`000 204 638 A8D ECF` or of entry 15 from `FFF` (0GRB words; full palettes are
in `resources/derived/images/gpc/index.tsv`); last column = comparison with the
Windows PI (section 5.2). One row per distinct content. All rows **[V]**; all
103 also match the original decoder under emulation.

| name | disks | WxH | x,y | il | filters | palette notes | kind | vs Windows PI |
|---|---|---|---|---|---|---|---|---|
| BL | A | 640x400 | 0,0 | 1 | 0,1 | 0=000 | full-screen | identical |
| CP | A | 640x400 | 0,0 | 1 | 0,1 | 0=000; 1-5=00C 0F0 0CC C00 C0C | overlay on full canvas (5% colour 0) | identical |
| MAP1 | BC | 640x400 | 0,0 | 16 | 0,1,2,4 | 0=505; 1-5=404 C3C BE2 535 DAD; 15=FFE | full-screen | identical; palette differs |
| MAP2 | BC | 640x400 | 0,0 | 16 | 0,1,2 | 0=505; 1-5=404 C3C BE2 535 DAD; 15=FFE | full-screen | identical; palette differs |
| MAP3 | B | 640x400 | 0,0 | 16 | 0,1,2 | 0=505; 1-5=404 C3C BE2 535 DAD; 15=FFE | full-screen | identical; palette differs |
| MAP4 | B | 640x400 | 0,0 | 16 | 0,1,2 | 0=505; 1-5=404 C3C BE2 535 DAD; 15=FFE | full-screen | identical; palette differs |
| MAPWIN | BC | 640x400 | 0,0 | 1 | 0,1 | 0=000; 1-5=404 C3C BE2 535 DAD; 15=FFE | overlay on full canvas (85% colour 0) | identical |
| NV00 | AD | 640x400 | 0,0 | 2 | 0,1 | 0=000 | full-screen | identical |
| NV01 | A | 640x400 | 0,0 | 2 | 0,1 | 0=000 | full-screen | identical |
| NV01L | A | 640x400 | 0,0 | 2 | 0,1 | 0=000 | full-screen | identical |
| NV02 | A | 640x400 | 0,0 | 2 | 0,1 | 0=000 | full-screen | identical |
| NV03 | BCD | 640x400 | 0,0 | 2 | 0,1,2 | 0=000 | full-screen | identical |
| NV03A | B | 640x400 | 0,0 | 1 | 0 | 0=000 | overlay on full canvas (97% colour 0) | same on screen (PI 103x136@457,229) |
| NV03ALL | B | 640x400 | 0,0 | 1 | 0 | 0=000 | overlay on full canvas (82% colour 0) | same on screen (PI 575x319@65,81) |
| NV03B | B | 640x400 | 0,0 | 1 | 0 | 0=000 | overlay on full canvas (98% colour 0) | same on screen (PI 50x185@424,103) |
| NV03C | B | 640x400 | 0,0 | 1 | 0 | 0=000 | overlay on full canvas (96% colour 0) | same on screen (PI 165x113@452,287) |
| NV03D | B | 640x400 | 0,0 | 1 | 0 | 0=000 | overlay on full canvas (96% colour 0) | same on screen (PI 124x143@172,231) |
| NV03E | B | 640x400 | 0,0 | 1 | 0 | 0=000 | overlay on full canvas (96% colour 0) | 1 px differ |
| NV03F | B | 640x400 | 0,0 | 2 | 0 | 0=000 | overlay on full canvas (96% colour 0) | 1 px differ |
| NV04 | A | 640x400 | 0,0 | 2 | 0,1 | 0=505 | full-screen | identical |
| NV05 | A | 640x400 | 0,0 | 2 | 0,1 | 0=505 | full-screen | identical |
| NV06 | A | 640x400 | 0,0 | 2 | 0,1 | 0=505 | full-screen | identical |
| NV06A | A | 640x400 | 0,0 | 2 | 0,1 | 0=505 | overlay on full canvas (86% colour 0) | same on screen (PI 320x400@320,0) |
| NV07 | A | 640x400 | 0,0 | 2 | 0,3 | 0=000 | full-screen | identical |
| NV08 | A | 640x400 | 0,0 | 2 | 0,1,2,3,4 | 0=505 | full-screen | identical |
| NV09 | A | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=010 204 638 A8D ECF | overlay on full canvas (68% colour 0) | same on screen (PI 400x370@200,30) |
| NV10 | A | 640x400 | 0,0 | 2 | 0,1 | 0=000 | overlay on full canvas (57% colour 0) | 1 px differ |
| NV11 | AD | 640x400 | 0,0 | 2 | 0,1 | 0=000 | overlay on full canvas (68% colour 0) | same on screen (PI 345x400@250,0) |
| NV12A | D | 320x400 | 0,0 | 2 | 0,1,2,5,9,12,14 | 0=404 | half-screen (left) | A+B = NV12.PI |
| NV12B | D | 320x400 | 320,0 | 4 | 0,1 | 0=404 | half-screen (right) | A+B = NV12.PI |
| NV13 | D | 640x400 | 0,0 | 2 | 0,1 | 0=404; 1-5=000 CCD 638 A8D 494 | full-screen | identical |
| NV14 | D | 640x400 | 0,0 | 2 | 0,1 | 0=000 | full-screen | identical |
| NV15A | D | 320x400 | 0,0 | 2 | 0,1 | 0=404; 1-5=000 204 250 A8D 491 | half-screen (left) | A+B = NV15.PI |
| NV15B | D | 320x400 | 320,0 | 2 | 0,1 | 0=404; 1-5=000 204 250 A8D 491 | half-screen (right) | A+B = NV15.PI |
| NV16A | C | 320x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 879 483 A8D ECF | half-screen (left) | A+B = NV16.PI |
| NV16B | C | 320x400 | 320,0 | 2 | 0,1,2,3 | 0=000; 1-5=000 879 483 A8D ECF | half-screen (right) | A+B = NV16.PI |
| NV17 | C | 640x400 | 0,0 | 2 | 0,1 | 0=000 | full-screen | identical |
| NV18 | CD | 640x400 | 0,0 | 2 | 0,1 | 0=000 | full-screen | identical |
| NV19 | A | 304x387 | 272,13 | 2 | 0,1 | 0=000 | overlay, cropped (47% colour 0) | same on screen (PI 283x374@282,26) |
| NV19A | B | 136x122 | 344,101 | 1 | 0 | 0=000 | overlay, cropped (46% colour 0) | same on screen (PI 115x111@356,108) |
| NV20 | B | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 304 638 A8D ECF | full-screen | identical |
| NV20A | B | 168x129 | 80,165 | 1 | 0 | 0=000; 1-5=000 304 638 A8D ECF | overlay, cropped (72% colour 0) | same on screen (PI 640x400@0,0) |
| NV20B | B | 400x316 | 80,37 | 1 | 0,1 | 0=000; 1-5=000 304 638 A8D ECF | overlay, cropped (74% colour 0) | same on screen (PI 355x291@89,54) |
| NV21 | B | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 304 638 A8D ECF | full-screen | identical |
| NV22 | D | 640x400 | 0,0 | 2 | 0,1,2 | 0=000; 1-5=000 304 638 A8D ECF | full-screen | identical |
| NV23 | C | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 204 638 A8D F7B | full-screen | identical |
| NV24 | C | 640x400 | 0,0 | 2 | 0,1 | 0=000 | full-screen | identical |
| NV25 | CD | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 304 638 A8D ECF | full-screen | identical |
| NV26 | CD | 640x400 | 0,0 | 1 | 0,1 | 0=000 | full-screen | identical |
| NV27 | A | 304x392 | 200,8 | 2 | 0,1 | 0=000 | overlay, cropped (42% colour 0) | same on screen (PI 294x373@208,27) |
| NV28 | B | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 304 638 A8D ECF | full-screen | identical |
| NV28A | B | 384x365 | 32,35 | 1 | 0 | 0=000; 1-5=000 304 638 A8D ECF | overlay, cropped (54% colour 0) | same on screen (PI 365x339@42,61) |
| NV28B | B | 216x339 | 152,61 | 2 | 0 | 0=000; 1-5=000 304 638 A8D ECF | overlay, cropped (63% colour 0) | same on screen (PI 193x328@168,72) |
| NV28C | B | 640x400 | 0,0 | 2 | 0 | 0=000; 1-5=000 304 638 A8D ECF | overlay on full canvas (80% colour 0) | same on screen (PI 348x333@45,67) |
| NV29 | B | 640x400 | 0,0 | 2 | 0,1 | 0=000 | full-screen | identical |
| NV30 | D | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 304 638 A8D ECF | full-screen | identical |
| NV31 | CD | 640x400 | 0,0 | 2 | 0,1 | 0=000 | full-screen | identical |
| NV32A | C | 328x400 | 0,0 | 1 | 0,1,2 | 0=000; 1-5=000 304 638 A8D ECF | half-screen (left) | A+B = NV32.PI |
| NV32B | C | 320x400 | 320,0 | 1 | 0,1 | 0=000; 1-5=000 304 638 A8D ECF | half-screen (right) | A+B = NV32.PI |
| NV33 | BC | 640x400 | 0,0 | 2 | 0,1 | 0=500; 1-5=000 889 CCD A8D ECF | full-screen | identical |
| NV34 | D | 640x400 | 0,0 | 2 | 0,1 | 0=000 | full-screen | identical |
| NV35 | A | 400x400 | 24,0 | 1 | 0 | 0=000 | overlay, cropped (49% colour 0) | same on screen (PI 370x396@45,4) |
| NV35B | B | 152x160 | 168,73 | 1 | 0,1 | 0=000 | overlay, cropped (37% colour 0) | same on screen (PI 144x141@173,83) |
| NV36 | B | 640x400 | 0,0 | 2 | 0,1 | 0=000 | full-screen | identical |
| NV36A | B | 336x351 | 280,49 | 1 | 0 | 0=000 | overlay, cropped (51% colour 0) | same on screen (PI 317x315@293,85) |
| NV36B | B | 640x336 | 0,64 | 2 | 0 | 0=000 | overlay, cropped (55% colour 0) | same on screen (PI 640x322@0,78) |
| NV37 | B | 640x400 | 0,0 | 2 | 0,1 | 0=404 | full-screen | identical |
| NV38 | D | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 304 638 A8D ECF | full-screen | identical |
| NV39 | D | 640x400 | 0,0 | 2 | 0,1 | 0=404; 1-5=000 204 638 A8D 491 | full-screen | identical |
| NV40A | CD | 320x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 778 638 A8D ECF | half-screen (left) | A+B = NV40.PI |
| NV40B | CD | 320x400 | 320,0 | 2 | 0 | 0=000; 1-5=000 778 638 A8D ECF | half-screen (right) | A+B = NV40.PI |
| NV41A | C | 320x400 | 0,0 | 2 | 0,1 | 0=000 | half-screen (left) | A+B = NV41.PI |
| NV41B | C | 320x400 | 320,0 | 2 | 0,1 | 0=000 | half-screen (right) | A+B = NV41.PI |
| NV42 | CD | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 304 638 A8D ECF | full-screen | identical |
| NV43 | A | 336x368 | 232,32 | 1 | 0 | 0=000 | overlay, cropped (42% colour 0) | same on screen (PI 314x360@241,40) |
| NV43A | B | 304x358 | 272,42 | 1 | 0 | 0=000 | overlay, cropped (37% colour 0) | same on screen (PI 292x351@279,49) |
| NV43A | C | 640x400 | 0,0 | 1 | 0 | 0=000 | overlay on full canvas (73% colour 0) | same on screen (PI 292x351@279,49) |
| NV43B | B | 304x366 | 248,34 | 1 | 0 | 0=000 | overlay, cropped (36% colour 0) | same on screen (PI 288x360@257,40) |
| NV44 | B | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 463 9C7 A8D 3C3 | full-screen | identical |
| NV44A | B | 232x207 | 104,123 | 2 | 0,1 | 0=000; 1-5=000 463 9C7 A8D 3C3 | overlay, cropped (58% colour 0) | same on screen (PI 218x205@111,123) |
| NV44B | B | 88x223 | 552,124 | 2 | 0 | 0=000; 1-5=000 463 9C7 A8D 3C3 | overlay, cropped (67% colour 0) | same on screen (PI 81x209@559,130) |
| NV44Z | B | 96x114 | 544,224 | 2 | 0,1 | 0=000; 1-5=000 463 9C7 A8D 3C3 | overlay, cropped (1% colour 0) | same on screen (PI 95x114@545,224) |
| NV45 | B | 640x400 | 0,0 | 1 | 0,1 | 0=000 | full-screen | identical |
| NV46 | D | 640x400 | 0,0 | 2 | 0,1 | 0=404 | full-screen | identical |
| NV47 | D | 640x400 | 0,0 | 2 | 0,1 | 0=404 | full-screen | identical |
| NV48A | C | 320x400 | 0,0 | 2 | 0,1 | 0=000 | half-screen (left) | A+B = NV48.PI |
| NV48B | C | 320x400 | 320,0 | 2 | 0,1 | 0=000 | half-screen (right) | A+B = NV48.PI |
| NV49 | BD | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 204 638 A8D DDE | full-screen | identical |
| NV49A | BD | 440x351 | 56,49 | 2 | 0,1 | 0=000; 1-5=000 204 638 A8D DDE | overlay, cropped (70% colour 0) | same on screen (PI 414x338@70,62) |
| NV50 | D | 640x400 | 0,0 | 4 | 0,1 | 0=404 | full-screen | identical |
| NV51A | C | 320x400 | 0,0 | 2 | 0 | 0=000; 1-5=000 304 638 A8D ECF | half-screen (left), 30% colour 0 | A+B = NV51.PI |
| NV51B | C | 320x400 | 320,0 | 2 | 0 | 0=000; 1-5=000 304 638 A8D ECF | half-screen (right), 20% colour 0 | A+B = NV51.PI |
| NV52 | B | 448x388 | 160,12 | 2 | 0 | 0=000 | overlay, cropped (44% colour 0) | same on screen (PI 420x374@169,26) |
| NV53 | B | 640x400 | 0,0 | 1 | 0,1 | 0=000; 1-5=000 304 638 A8D ECF | full-screen | identical |
| NV54 | B | 640x400 | 0,0 | 1 | 0,1 | 0=807; 1-5=000 304 638 A8D ECF | full-screen | identical |
| NV55A | B | 320x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 322 252 ACA AA9; 15=DDD | half-screen (left) | A+B = NV55.PI |
| NV55B | B | 320x400 | 320,0 | 2 | 0,1 | 0=000; 1-5=000 322 252 ACA AA9; 15=DDD | half-screen (right) | A+B = NV55.PI |
| NV56 | B | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 304 638 A8D ECF | overlay on full canvas (53% colour 0) | identical |
| NV99 | BCD | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 322 061 A8D 5D5 | full-screen | identical |
| NVWIN | A | 528x103 | 56,297 | 2 | 0,1 | 0=500; 1-5=000 304 638 A8D ECF | overlay, cropped (50% colour 0) | same on screen (PI 527x103@57,297) |
| OPPAL | A | 16x13 | 0,0 | 1 | 0 | 0=000; 1-5=111 222 333 444 555 | palette carrier (all colour 0) | same on screen (PI 640x400@0,0) |
| ROGO | B | 640x400 | 0,0 | 2 | 0,1 | 0=000; 1-5=000 322 061 092 5D5 | full-screen | 311 px differ; palette differs |
| SAVE | B | 144x37 | 480,225 | 1 | 0,1 | 0=000; 1-5=404 C3C BE2 535 DAD; 15=FFE | overlay, cropped (18% colour 0) | same on screen (PI 132x33@485,227) |
