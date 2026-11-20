#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify source/tools/gpc.py against two independent witnesses.

1. The 1996 Windows release ships the same art as Pi files (decoded by
   re-tools/pi.py).  Every PC-98 GPC is compared with the same-named PI:
   palette (16 x 12 bit) and pixels.  The Windows files are often cropped to
   the bounding box of the non-zero pixels, so pixels are compared on a
   640x400 canvas of colour 0, each picture placed at its own x,y.
   The "A"/"B" half-screen GPCs (NV12A + NV12B ...) are composed and compared
   with the single full-screen PI (NV12.PI).

2. The original decoder in the game's AdvBIOS (resources/derived/exe/NV.OV1,
   routine at image offset 0x29AE = 0290:00AE) is run under the Unicorn CPU
   emulator on every file and its four output bit planes + palette buffer are
   compared with gpc.decode().  This needs the `unicorn` package; without it
   (e.g. under a bare `python3 -I`) the step is skipped and reported as such.

Usage:
    gpc_verify.py [--pc98 DIR] [--win DIR] [--ov1 FILE] [--no-emu] [--tsv FILE]

Exit status 0 if nothing unexpected was found (differences that are in the
game data itself are listed but are not failures of the decoder).
"""
import argparse
import collections
import glob
import hashlib
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'source', 'tools'))
sys.path.insert(0, HERE)

import advbuild  # noqa: E402
import gamedir  # noqa: E402
import gpc   # noqa: E402
import pi    # noqa: E402

SW, SH = 640, 400


def canvas(pics):
    """Compose [(w, h, x, y, pixels)] in order onto a 640x400 canvas of 0."""
    c = bytearray(SW * SH)
    for w, h, x, y, pix in pics:
        for r in range(h):
            yy = y + r
            if 0 <= yy < SH and x < SW:
                n = min(w, SW - x)
                c[yy * SW + x:yy * SW + x + n] = pix[r * w:r * w + n]
    return bytes(c)


def diff_pixels(a, b):
    """Return (count, bbox, samples) of differing positions of two canvases."""
    if a == b:
        return 0, None, []
    n = 0
    x0 = y0 = 10 ** 9
    x1 = y1 = -1
    samples = []
    for y in range(SH):
        ra = a[y * SW:(y + 1) * SW]
        rb = b[y * SW:(y + 1) * SW]
        if ra == rb:
            continue
        for x in range(SW):
            if ra[x] != rb[x]:
                n += 1
                x0, x1 = min(x0, x), max(x1, x)
                y0, y1 = min(y0, y), max(y1, y)
                if len(samples) < 4:
                    samples.append((x, y, ra[x], rb[x]))
    return n, (x0, y0, x1, y1), samples


def outside_colours(w, h, x, y, pix, rw, rh, rx, ry):
    """Histogram of the pixels of picture (w,h,x,y) lying outside rect r."""
    hist = collections.Counter()
    for r in range(h):
        row = pix[r * w:(r + 1) * w]
        yy = y + r
        if ry <= yy < ry + rh:
            lo = max(0, rx - x)
            hi = min(w, rx + rw - x)
            if lo < hi:
                hist.update(row[:lo])
                hist.update(row[hi:])
                continue
        hist.update(row)
    return hist


def pal_diff(pg, pp):
    if pg is None or pp is None:
        return 'n/a'
    d = ['%d:%X%X%X>%X%X%X' % ((i,) + pg[i] + pp[i]) for i in range(16) if pg[i] != pp[i]]
    return ' '.join(d)


# --------------------------------------------------------------------------
# Third witness: the original routine under Unicorn.

class Emu:
    """Runs AdvBIOS's GPC draw routine (NV.OV1 image offset 0x29AE).

    Calling convention recovered from the code (see graphics-formats.md):
      DS = ES = 0x04E9 (AdvBIOS data segment), file image at DS:0x0454,
      [BP+2]:SI -> 16-byte parameter block copied to DS:0000:
        +0..+6  four plane segments (plane 0..3)
        +8      x in bytes (0xFFFF = take x and y from the file)
        +A      y
        +C      0 = opaque copy, non-zero = colour 0 transparent
        +E      bit 0: copy the file palette to DS:0022, bit 1: program the DAC
    """
    CS = 0x0290
    ENTRY = 0x00AE
    DS = 0x04E9
    FILEBUF = 0x0454
    FILEMAX = 0xF800
    PLANES = (0x6000, 0x6800, 0x7000, 0x7800)   # scratch segments, 32000 bytes each

    def __init__(self, ov1_path):
        import unicorn
        from unicorn import x86_const as x
        self.uc_mod, self.x = unicorn, x
        exe = advbuild.check(open(ov1_path, 'rb').read(), advbuild.BIOS, ov1_path)
        if exe[:2] != b'MZ':
            raise ValueError('NV.OV1 is not a plain MZ file')
        hdr_paras = struct.unpack_from('<H', exe, 8)[0]
        self.image = exe[hdr_paras * 16:]
        # sanity: the routine starts by copying the parameter block
        code = self.image[self.CS * 16 + self.ENTRY:][:12]
        if code[:1] != b'\x1e' or b'\xf3\xa5' not in code:
            raise ValueError('unexpected code at the decoder entry point')

    def run(self, data, masked=False):
        unicorn, x = self.uc_mod, self.x
        if len(data) > self.FILEMAX:
            raise ValueError('file larger than the AdvBIOS buffer')
        uc = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_16)
        uc.mem_map(0, 0x110000)
        uc.mem_write(0, self.image)
        base = self.DS * 16
        uc.mem_write(base + self.FILEBUF, bytes(data))
        pseg, poff = 0x9000, 0x0100
        params = struct.pack('<4HHHHH', *self.PLANES, 0xFFFF, 0, 1 if masked else 0, 1)
        uc.mem_write(pseg * 16 + poff, params)
        for seg in self.PLANES:
            uc.mem_write(seg * 16, bytes(0x8000))
        sseg, sp = 0x9800, 0xFFE0
        bp = 0x8000
        uc.mem_write(sseg * 16 + bp, struct.pack('<HH', self.DS, pseg))
        stop = 0xFFF0
        sp -= 2
        uc.mem_write(sseg * 16 + sp, struct.pack('<H', stop))
        for reg, val in ((x.UC_X86_REG_CS, self.CS), (x.UC_X86_REG_DS, self.DS),
                         (x.UC_X86_REG_ES, self.DS), (x.UC_X86_REG_SS, sseg),
                         (x.UC_X86_REG_SP, sp), (x.UC_X86_REG_BP, bp),
                         (x.UC_X86_REG_SI, poff), (x.UC_X86_REG_EFLAGS, 0x2)):
            uc.reg_write(reg, val)
        uc.emu_start(self.CS * 16 + self.ENTRY, self.CS * 16 + stop, count=200000000)
        if uc.reg_read(x.UC_X86_REG_IP) != stop:
            raise RuntimeError('emulation did not return')
        planes = [bytes(uc.mem_read(seg * 16, 80 * SH)) for seg in self.PLANES]
        pal = struct.unpack('<16H', bytes(uc.mem_read(base + 0x22, 32)))
        return planes, list(pal)


def planes_from_pixels(w, h, x, y, pix):
    """What an opaque draw of the picture leaves in four cleared 80x400 planes."""
    scr = canvas([(w, h, x, y, pix)])
    planes = [bytearray(80 * SH) for _ in range(4)]
    for i in range(0, SW * SH, 8):
        chunk = scr[i:i + 8]
        if not any(chunk):
            continue
        for p in range(4):
            v = 0
            for c in chunk:
                v = (v << 1) | ((c >> p) & 1)
            planes[p][i >> 3] = v
    return [bytes(p) for p in planes]


# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--pc98')
    ap.add_argument('--win')
    ap.add_argument('--ov1')
    ap.add_argument('--no-emu', action='store_true', help='skip the Unicorn witness')
    ap.add_argument('--tsv', help='also write the per-picture table to this file')
    args = ap.parse_args(argv)
    args.pc98 = args.pc98 or gamedir.original(None, 'pc98')
    args.win = args.win or gamedir.original(None, 'win')
    args.ov1 = args.ov1 or gamedir.derived(None, 'exe', 'NV.OV1')

    # ---- collect
    gpcs = collections.OrderedDict()       # name -> {md5: ([disks], data)}
    for path in sorted(glob.glob(os.path.join(args.pc98, '*', 'GPC', '*.GPC'))):
        disk = os.path.basename(os.path.dirname(os.path.dirname(path)))
        name = os.path.splitext(os.path.basename(path))[0].upper()
        data = open(path, 'rb').read()
        key = hashlib.md5(data).hexdigest()
        gpcs.setdefault(name, collections.OrderedDict()).setdefault(key, ([], data))[0].append(disk)
    pis = {}
    for path in sorted(glob.glob(os.path.join(args.win, '*.PI'))):
        pis[os.path.splitext(os.path.basename(path))[0].upper()] = path
    nfiles = sum(len(d) for v in gpcs.values() for d, _ in v.values())
    nuniq = sum(len(v) for v in gpcs.values())
    print('GPC files: %d (%d names, %d distinct contents); PI files: %d'
          % (nfiles, len(gpcs), nuniq, len(pis)))
    multi = [n for n, v in gpcs.items() if len(v) > 1]
    print('names whose content differs between disks: %s' % (', '.join(multi) or 'none'))

    emu = None
    emu_note = 'skipped (--no-emu)'
    if not args.no_emu:
        try:
            emu = Emu(args.ov1)
            emu_note = 'ran'
        except ImportError:
            emu_note = 'skipped (python module "unicorn" not available)'
        except (OSError, ValueError) as e:
            emu_note = 'skipped (%s)' % e

    # ---- per picture
    rows = []
    decoded = {}
    pi_cache = {}
    stats = collections.Counter()
    carry_matters = 0
    problems = []
    for name, variants in gpcs.items():
        for key, (disks, data) in variants.items():
            hdr, pal, w, h, x, y, pix = gpc.decode(data)
            decoded[(name, key)] = (hdr, pal, w, h, x, y, pix, disks)
            stats['decoded'] += 1
            if hdr['stream_end'] != len(data) or \
                    hdr['stream_size_field'] != len(data) - hdr['stream_offset']:
                problems.append('%s: stream not consumed exactly' % name)
            if gpc.decode(data, carry=False)[6] != pix:
                carry_matters += 1
            # witness 2: original code
            emu_res = '-'
            if emu:
                try:
                    planes, epal = emu.run(data)
                    ok = planes == planes_from_pixels(w, h, x, y, pix) and \
                        epal == hdr['palette_raw']
                    emu_res = 'ok' if ok else 'DIFF'
                    stats['emu_' + emu_res] += 1
                    if not ok:
                        problems.append('%s: differs from the original decoder' % name)
                except Exception as e:          # noqa: BLE001
                    emu_res = 'ERR'
                    stats['emu_ERR'] += 1
                    problems.append('%s: emulation failed: %s' % (name, e))
            # witness 1: Windows PI
            cmp_, paln, extra = 'no PI', '', ''
            if name in pis:
                if name not in pi_cache:
                    pi_cache[name] = pi.decode(open(pis[name], 'rb').read())
                phdr, ppal, pw, ph, px, py, ppix = pi_cache[name]
                n, bbox, samples = diff_pixels(canvas([(w, h, x, y, pix)]),
                                               canvas([(pw, ph, px, py, ppix)]))
                same_rect = (w, h, x, y) == (pw, ph, px, py)
                if n == 0 and same_rect:
                    cmp_ = 'identical'
                elif n == 0:
                    cmp_ = 'same on screen'
                    hist = outside_colours(w, h, x, y, pix, pw, ph, px, py)
                    hist2 = outside_colours(pw, ph, px, py, ppix, w, h, x, y)
                    extra = 'PI rect %dx%d@%d,%d' % (pw, ph, px, py)
                    if set(hist) - {0} or set(hist2) - {0}:
                        extra += ' NONZERO OUTSIDE'
                        problems.append('%s: non-zero pixels outside common rect' % name)
                else:
                    cmp_ = '%d px differ' % n
                    extra = 'PI rect %dx%d@%d,%d; bbox %d,%d-%d,%d; e.g. %s' % (
                        pw, ph, px, py, *bbox,
                        ' '.join('(%d,%d) gpc=%d pi=%d' % s for s in samples))
                stats['pi_' + ('identical' if cmp_ == 'identical' else
                               'same_on_screen' if n == 0 else 'pixel_diff')] += 1
                pd = pal_diff(pal, ppal)
                paln = 'same' if not pd else pd
                stats['pal_same' if not pd else 'pal_diff'] += 1
            else:
                stats['pi_none'] += 1
            rows.append((name, ''.join(disks), '%dx%d' % (w, h), '%d,%d' % (x, y),
                         hdr['interleave'], cmp_, paln, emu_res, extra))

    # ---- half-screen pairs vs. one PI
    pair_rows = []
    for name in list(gpcs):
        if not name.endswith('A') or name in pis:
            continue
        base = name[:-1]
        if base + 'B' not in gpcs or base not in pis or base + 'B' in pis:
            continue
        for ka, (da, _) in gpcs[name].items():
            for kb, (db, _) in gpcs[base + 'B'].items():
                A = decoded[(name, ka)]
                B = decoded[(base + 'B', kb)]
                phdr, ppal, pw, ph, px, py, ppix = pi.decode(open(pis[base], 'rb').read())
                pc = canvas([(pw, ph, px, py, ppix)])
                res = []
                for label, order in (('A then B', (A, B)), ('B then A', (B, A))):
                    n, bbox, samples = diff_pixels(
                        canvas([(o[2], o[3], o[4], o[5], o[6]) for o in order]), pc)
                    res.append((label, n, bbox))
                pda = pal_diff(A[1], ppal) or 'same'
                pdb = pal_diff(B[1], ppal) or 'same'
                pair_rows.append((base, res, pda, pdb))
                stats['pair_ok' if min(r[1] for r in res) == 0 else 'pair_diff'] += 1

    # ---- output
    head = ('name', 'disks', 'WxH', 'x,y', 'il', 'vs Windows PI', 'palette vs PI',
            'orig.code', 'notes')
    widths = [max(len(str(r[i])) for r in rows + [head]) for i in range(len(head) - 1)]
    fmt = '  '.join('%%-%ds' % wd for wd in widths) + '  %s'
    print()
    print(fmt % head)
    for r in rows:
        print(fmt % r)
    if args.tsv:
        with open(args.tsv, 'w') as f:
            f.write('\t'.join(head) + '\n')
            for r in rows:
                f.write('\t'.join(str(v) for v in r) + '\n')

    print('\nHalf-screen pairs composed and compared with the full-screen PI:')
    for base, res, pda, pdb in pair_rows:
        print('  %-6s %s; palette A: %s; palette B: %s' % (
            base + 'A+B',
            '; '.join('%s: %s' % (lab, 'identical' if n == 0 else
                                  '%d px differ (bbox %d,%d-%d,%d)' % ((n,) + bbox))
                      for lab, n, bbox in res), pda, pdb))

    only_pi = sorted(n for n in pis if n not in gpcs)
    print('\nPI files without a same-named GPC (%d): %s' % (len(only_pi), ' '.join(only_pi)))

    print('\nSummary')
    print('  GPC contents decoded, stream consumed to the last byte : %d / %d'
          % (stats['decoded'] - sum('stream' in p for p in problems), nuniq))
    print('  with a same-named PI                                   : %d'
          % (nuniq - stats['pi_none']))
    print('    identical rectangle and pixels                       : %d' % stats['pi_identical'])
    print('    identical on screen, PI cropped/uncropped differently: %d' % stats['pi_same_on_screen'])
    print('    real pixel differences                               : %d' % stats['pi_pixel_diff'])
    print('    palette identical / different                        : %d / %d'
          % (stats['pal_same'], stats['pal_diff']))
    print('  without a PI                                           : %d' % stats['pi_none'])
    print('  A+B pairs equal to the combined PI / not               : %d / %d'
          % (stats['pair_ok'], stats['pair_diff']))
    print('  files where resetting the XOR accumulator per chain')
    print('    would change the picture (i.e. carry-over matters)   : %d' % carry_matters)
    print('  original AdvBIOS decoder under Unicorn                 : %s' % emu_note)
    if emu:
        print('    planes + palette identical / different / error       : %d / %d / %d'
              % (stats['emu_ok'], stats['emu_DIFF'], stats['emu_ERR']))
    if problems:
        print('\nUNEXPECTED:')
        for p in problems:
            print('  ' + p)
        return 1
    print('\nNo unexpected findings.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
