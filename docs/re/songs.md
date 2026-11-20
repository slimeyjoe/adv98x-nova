# NOVA's songs

What the engine's `docs/re/usd-sequencer.md` (the `.USO` format and the sequencer of AdvBIOS's
music driver) says about this game's songs in particular: how they loop or end, and the table of
the files. The section keeps the number it has there.

## 11. Songs

### 11.1 Loop and end

There is no song-level structure. A looping track ends in `F5` back to its loop start; tracks of one song
may have different loop lengths and different intro lengths (NV13: three tracks loop every 768 ticks, two
every 3072, one every 192). `usoinfo.py` reports per track "intro ticks + loop ticks", and for the song
intro = latest loop entry, loop = least common multiple. Three effect files (NVSE04, NVSE05, NVSE07) have
track loops of unrelated lengths (888, 1548, 400, 192 … ticks), so the texture practically never repeats;
they are marked *free*. Seven files end by themselves (CATS, NV09, NVSE02/03/08/09/10): all tracks reach
`FF`, after which all channels are idle and the driver is silent; nothing tells the caller.

### 11.2 The files

Ticks from `usoinfo.py` (control flow only), seconds from the tempo words; the emulation gives the same
durations. "intro + loop": the first pass through the loop starts at tick *intro*. Scripts: names of the
`.MES` files whose `sound "…"` loads the file (all are also in the sound-test script `SOUND`).

| file | tracks | tempo word (tick ms) | intro + loop ticks | loop s | scripts |
|---|---|---|---|---|---|
| CATS | 6 | 0262 (11.358), 0352 from tick 576 | 784, ends | 9.14 total | RUN |
| NV01 | 6 | 0262 (11.358) | 8 + 384 | 4.36 | BLG MAP2 S011 S016 WAL3 |
| NV02 | 6 | 0276 (9.916) | 888 + 3072 | 30.46 | 3HM02 S017 S024 |
| NV03 | 6 | 0380 (9.177) | 18 + 2880 | 26.43 | 3H RO01 RO01B |
| NV04 | 6 | 0262 (11.358) | 32 + 6144 | 69.78 | 2ALEX 2MAP2B MT S010 S010A S010B S023 YUKA2 |
| NV05 | 6 | 0184 (8.924) | 1 + 3072 | 27.42 | S025 |
| NV06 | 6 | 0352 (12.494) | 32 + 3456 | 43.18 | NTH2 YUH01 |
| NV07 | 6 | 0352 (12.494) | 16 + 3072 | 38.38 | 2LEM 3HN02 |
| NV08 | 6 | 0254 (12.368) | 32 + 768 | 9.50 | 202 3HL02 |
| NV09 | 6 | 0352, then 023F, 0227, 0208 (ritardando) | 7856, ends | 100.29 total | END |
| NV10 | 6 | 02A2 (6.743) | 1554 + 4608 | 31.07 | 201 |
| NV11 | 6 | 0262 (11.358) | 24 + 6528 | 74.15 | 3HK |
| NV12 | 6 | 0262 (11.358) | 8 + 1536 | 17.45 | 3K01 CAP D11 D23 D37 D3YK EV03 |
| NV13 | 6 | 023F (13.882) | 792 + 3072 | 42.65 | 202 203 2LEM 2MAL ALEX BLG COM MT S018 S020 YUKA |
| NV14 | 6 | 035F (11.556) | 12 + 768 | 8.88 | D37 RO04 S021 YUKA2 |
| NV15 | 5 (no SSG3) | 0380 (9.177) | 32 + 4608 | 42.29 | 3HY02 MON01 |
| NV16 | 6 | 0254 (12.368) | 192 + 2304 | 28.50 | 2MAP2A |
| NVSE01 | 6 | 0352 (12.494) | 48 + 96 | 1.20 | 2D21 COM D11 LEH NTH NTH2 RO03 WAL3 YUH01 YUKA |
| NVSE02 | 1 (SSG3) | 0352 (12.494) | 528, ends | 6.60 total | 3H NOVA3 |
| NVSE03 | 6 | 036F (10.403) | 336, ends | 3.50 total | D11 D23 D24 D33 EV01 EV02 EV03 EV04 |
| NVSE04 | 6 | 036F (10.403) | free; track loops 888 / 1548 / 888 / 400 / 192 / 192 | – | D33 NVOP |
| NVSE05 | 6 | 036F (10.403) | free; 777 / 76 / 777 / 96, two tracks end | – | 2D31 301 D11 D21 D23 D31 D34 EV03 |
| NVSE06 | 6 | 036F (10.403) | 192 + 1554 (777 / 777 / 777 / 6) | 16.17 | 201 202 203 D11 S021 WAL3 |
| NVSE07 | 6 | 036F (10.403) | free; 777 / 1548 / 777, three tracks end | – | 2D21 3H D23 D32 NOVA NOVA2 NOVA3 S019 |
| NVSE08 | 6 | 036F (10.403) | 192, ends | 2.00 total | MON01 S024 |
| NVSE09 | 6 | 028C (8.329) | 636, ends | 5.30 total | 3H S024 |
| NVSE10 | 6 | 039F (6.941) | 469, ends | 3.26 total | 201 202 203 3H D32 D35 MON01 RO01 RO01B S024 SELC2 |
| NVSE11 | 6 | 0208 (17.849) | 192 + 4128 | 73.68 | 2CLD HHYUKA RO03 RO03B RO04 YUKA2 YUKA3 |

All tracks have priority 0; every file has owner 1 and sets its tempo in the first row of one track.
Machine-readable: `resources/music/index.tsv` (`usoinfo.py --index`).

The "effect" files that loop (NVSE01, 04–07, 11: alarms, ambiences) sound until the script stops them.
Since effects are played through the music path, an effect always replaces the music; scripts restart
the music afterwards.
