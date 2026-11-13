#!/usr/bin/env python3
"""Pi picture decoder (Yanagisawa's "Pi" format, 16-colour variant), as used by
the 1996 Windows release of NOVA for its *.PI pictures.

Used here as an independent ground truth for the GPC decoder and to convert
the Windows-only pictures.  Format notes: docs/re/graphics-formats.md.

Layout (big-endian):
  "Pi"  comment bytes ... 0x1A  [dummy bytes ...] 0x00
  u8 mode, u8 aspect_x, u8 aspect_y, u8 planes (4), 4 bytes saver id,
  u16 n + n bytes of saver-specific data, u16 width, u16 height,
  48 bytes palette (16 x R,G,B; the significant bits are the high nibble)
  (palette is absent if mode bit 7 is set), then the bit stream (MSB first).

Written from the public format descriptions (Kirinn Bunnylin's
https://mooncore.eu/bunny/txt/pi-pic.htm and the original PITECH.TXT ideas as
relayed there); no code copied.

Library use:
    header, palette, w, h, x, y, pixels = pi.decode(data)
      palette  [(r, g, b)] * 16 as 4-bit values (high nibbles of the file's bytes);
               header['palette_rgb8'] keeps the raw bytes
      x, y     screen position from the 5-byte saver extension (01 xx xx yy yy)
               that NOVA's cropped pictures carry; 0, 0 when absent

Command line:
    pi.py info FILE...
    pi.py png  FILE... -o DIR

Only the Python standard library is used.
"""
import os
import struct
import sys
import zlib


class PiError(ValueError):
    pass


def parse_header(data):
    if data[:2] != b'Pi':
        raise PiError('not a Pi file (bad signature)')
    p = data.find(b'\x1a', 2)
    if p < 0:
        raise PiError('no comment terminator')
    comment = bytes(data[2:p])
    q = data.find(b'\x00', p + 1)
    if q < 0:
        raise PiError('no dummy-comment terminator')
    dummy = bytes(data[p + 1:q])
    q += 1
    mode, ax, ay, planes = data[q], data[q + 1], data[q + 2], data[q + 3]
    saver = bytes(data[q + 4:q + 8])
    (extlen,) = struct.unpack_from('>H', data, q + 8)
    ext = bytes(data[q + 10:q + 10 + extlen])
    q += 10 + extlen
    width, height = struct.unpack_from('>HH', data, q)
    q += 4
    hdr = {'comment': comment, 'dummy': dummy, 'mode': mode, 'aspect_x': ax,
           'aspect_y': ay, 'planes': planes, 'saver': saver, 'ext': ext,
           'width': width, 'height': height, 'file_size': len(data),
           'x': 0, 'y': 0}
    # Saver-specific data.  NOVA's cropped pictures carry 5 bytes:
    # 0x01, u16 x, u16 y (big-endian) = screen position of the top-left pixel.
    if len(ext) == 5 and ext[0] == 1:
        hdr['x'], hdr['y'] = struct.unpack_from('>HH', ext, 1)
    if planes != 4:
        raise PiError('only 16-colour Pi is supported (planes=%d)' % planes)
    if mode & 0x80:
        hdr['palette_rgb8'] = None
    else:
        raw = data[q:q + 48]
        hdr['palette_rgb8'] = [tuple(raw[i:i + 3]) for i in range(0, 48, 3)]
        q += 48
    hdr['stream_offset'] = q
    return hdr


class _Bits:
    __slots__ = ('data', 'pos', 'acc', 'n')

    def __init__(self, data, pos):
        self.data = data
        self.pos = pos
        self.acc = 0
        self.n = 0

    def bit(self):
        if not self.n:
            try:
                self.acc = self.data[self.pos]
            except IndexError:
                self.acc = 0            # reading past the end yields zeros
            self.pos += 1
            self.n = 8
        self.n -= 1
        return (self.acc >> self.n) & 1

    def bits(self, k):
        v = 0
        for _ in range(k):
            v = (v << 1) | self.bit()
        return v


def decode(data):
    """Decode a 16-colour Pi file.

    Returns (header, palette, width, height, x, y, pixels) like gpc.decode().
    """
    hdr = parse_header(data)
    w, h = hdr['width'], hdr['height']
    total = w * h
    br = _Bits(data, hdr['stream_offset'])
    bit, bits = br.bit, br.bits

    # Move-to-front tables: one list per preceding colour.
    mtf = [[(a - b) & 15 for b in range(16)] for a in range(16)]

    def colour(prev):
        if bit():
            code = bit()
        elif not bit():
            code = 2 + bit()
        elif not bit():
            code = 4 + bits(2)
        else:
            code = 8 + bits(3)
        row = mtf[prev]
        c = row[code]
        if code:
            del row[code]
            row.insert(0, c)
        return c

    # The two leading pixels virtually fill the two rows above the picture.
    c0 = colour(0)
    c1 = colour(c0)
    pre = 2 * w
    if pre & 1:
        pre += 1
    out = bytearray([c0, c1]) * (pre // 2)
    end = pre + total
    last = -1
    while len(out) < end:
        # position code
        v = bits(2)
        if v == 3:
            v = 3 + bit()
        if v == last:
            # literal pixel pairs
            while True:
                a = colour(out[-1])
                out.append(a)
                out.append(colour(a))
                if not bit() or len(out) >= end:
                    break
            last = -1
            continue
        last = v
        # run length (in pixel pairs)
        k = 0
        while bit():
            k += 1
        n = (1 << k) + (bits(k) if k else 0)
        n *= 2
        if len(out) + n > end + 1:
            n = end + 1 - len(out)
        if v == 0:
            if out[-1] == out[-2]:
                out += out[-2:] * (n // 2)
                continue
            dist = 4
        elif v == 1:
            dist = w
        elif v == 2:
            dist = 2 * w
        elif v == 3:
            dist = w - 1
        else:
            dist = w + 1
        src = len(out) - dist
        if dist >= n:
            out += out[src:src + n]
        else:
            for i in range(n):
                out.append(out[src + i])
    hdr['stream_end'] = br.pos
    pixels = bytes(out[pre:end])
    pal = None
    if hdr['palette_rgb8']:
        pal = [(r >> 4, g >> 4, b >> 4) for r, g, b in hdr['palette_rgb8']]
    return hdr, pal, w, h, hdr['x'], hdr['y'], pixels


# --------------------------------------------------------------------------
# Minimal PNG writer (same as source/tools/gpc.py; duplicated so that each tool
# stays a single self-contained file).

def _chunk(tag, body):
    return struct.pack('>I', len(body)) + tag + body + \
        struct.pack('>I', zlib.crc32(tag + body) & 0xFFFFFFFF)


def write_png(path, width, height, pixels, palette4):
    if palette4 is None:
        palette4 = [(i, i, i) for i in range(16)]
    plte = bytes(c * 17 for rgb in palette4 for c in rgb)
    raw = bytearray()
    for r in range(height):
        raw.append(0)
        raw += pixels[r * width:(r + 1) * width]
    png = b'\x89PNG\r\n\x1a\n'
    png += _chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 3, 0, 0, 0))
    png += _chunk(b'PLTE', plte)
    png += _chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += _chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)


def cmd_info(paths):
    print('file\tsize\tw\th\tx\ty\tmode\taspect\tplanes\tsaver\text\tcomment\tdummy_len'
          '\tstream_ofs\tstream_end\tpalette(RGB, raw bytes)')
    for p in paths:
        data = open(p, 'rb').read()
        hdr = decode(data)[0]
        pal = ' '.join('%02X%02X%02X' % c for c in hdr['palette_rgb8']) \
            if hdr['palette_rgb8'] else '-'
        print('\t'.join(str(v) for v in (
            p, hdr['file_size'], hdr['width'], hdr['height'], hdr['x'], hdr['y'], '0x%02X' % hdr['mode'],
            '%d:%d' % (hdr['aspect_x'], hdr['aspect_y']), hdr['planes'],
            repr(hdr['saver'])[1:], hdr['ext'].hex() or '-',
            repr(hdr['comment'])[1:], len(hdr['dummy']),
            hdr['stream_offset'], hdr['stream_end'], pal)))


def cmd_png(paths, outdir):
    os.makedirs(outdir, exist_ok=True)
    rows = []
    for p in paths:
        hdr, pal, w, h, x, y, pix = decode(open(p, 'rb').read())
        name = os.path.splitext(os.path.basename(p))[0] + '.png'
        write_png(os.path.join(outdir, name), w, h, pix, pal)
        rows.append((name, p, x, y, w, h,
                     ' '.join('%X%X%X' % c for c in pal) if pal else '-'))
    with open(os.path.join(outdir, 'index.tsv'), 'w') as f:
        f.write('png\tsource\tx\ty\tw\th\tpalette_RGB\n')
        for r in rows:
            f.write('\t'.join(str(v) for v in r) + '\n')
    print('wrote %d PNG(s) and index.tsv to %s' % (len(rows), outdir))


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description='Pi picture decoder (16 colours)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('info', help='print header fields as TSV')
    a.add_argument('files', nargs='+')
    a = sub.add_parser('png', help='convert to indexed PNG + index.tsv')
    a.add_argument('files', nargs='+')
    a.add_argument('-o', '--outdir', required=True)
    args = ap.parse_args(argv)
    if args.cmd == 'info':
        cmd_info(args.files)
    else:
        cmd_png(args.files, args.outdir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
