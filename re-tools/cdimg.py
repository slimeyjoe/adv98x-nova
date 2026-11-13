#!/usr/bin/env python3
"""Reader for raw CD images (2352-byte sectors, e.g. CloneCD .img + .ccd/.cue): track table,
ISO 9660 file system of the data track, audio tracks as WAV. Stdlib only.

  python3 -I re-tools/cdimg.py tracks IMAGE            # track table (from IMAGE's .cue / .ccd)
  python3 -I re-tools/cdimg.py ls IMAGE                # ISO 9660 listing: lba, size, date, path
  python3 -I re-tools/cdimg.py extract IMAGE OUTDIR [PATH...]   # all files, or the named ones
  python3 -I re-tools/cdimg.py cat IMAGE PATH          # one file to stdout
  python3 -I re-tools/cdimg.py wav IMAGE TRACK OUT.wav # one audio track (44.1 kHz 16-bit stereo)
  python3 -I re-tools/cdimg.py audio IMAGE             # per audio track: length, peak, lead/trail silence, md5
  python3 -I re-tools/cdimg.py arc-ls ARCHIVE...       # members of AdvTowns archives (NOVA.000 ...)
  python3 -I re-tools/cdimg.py arc-extract OUTDIR ARCHIVE...    # -> OUTDIR/<archive name>/<member>
  python3 -I re-tools/cdimg.py gpc-png OUTDIR FILE.GPC...       # AdvTowns pictures -> PNG
  python3 -I re-tools/cdimg.py gpc-cmp TOWNS_DIR PC98_DIR       # compare them with the PC-98 GPCs
  python3 -I re-tools/cdimg.py se-wav NOVA.SE OUTDIR            # the samples of NOVA.SE -> WAV

IMAGE is the .img / .bin file; the .cue and .ccd are looked up next to it. Track ends come from
the next track's start (index 1; the pregap, index 0, belongs to the end of the previous track as
on the disc) and from the image size.
Written for the FM Towns CD of NOVA (docs/re/other-versions.md §3).

AdvTowns archive ("AdvTowns for CD", Ides 1991,93): a table of 16-byte entries, 12 bytes of
NUL-padded lower-case name + u32 LE offset of the member; the table ends where the first member
starts; the last entry has an empty name and the file size as offset. Members are stored as is.

AdvTowns .GPC picture (no signature): 16 palette words 0x0GRB, then u16 width, height, x, y,
k; then the same zero-suppression stream as the PC-98 GPC (source/tools/gpc.py), but a row is a
filter byte + width/2 bytes of packed pixels (low nibble = left pixel) instead of four bit
planes, and both the row interleave and the filter byte are stored as exponents: interleave
step = 1 << (k - 1), horizontal XOR step = 1 << (f - 1) for a filter byte f > 0.

NOVA.SE: u16 count, then count x (u8 0, u32 offset); at each offset a 32-byte FM Towns SND
header (8 name, u32 id, u32 length, u32 loop start, u32 loop length, u16 rate (Hz * 0.098),
s16 adjust, u8 base note, 3 x 0) and `length` bytes of 8-bit sign-magnitude PCM.
"""
import hashlib
import os
import re
import struct
import sys
import wave

SECTOR = 2352
SYNC = b'\x00' + b'\xff' * 10 + b'\x00'


class Track:
    def __init__(self, number, mode, start, pregap=None):
        self.number, self.mode, self.start, self.pregap = number, mode, start, pregap
        self.end = None           # exclusive, in sectors

    @property
    def audio(self):
        return self.mode == 'AUDIO'

    @property
    def sectors(self):
        return self.end - self.start


def msf(n):
    return '%02d:%02d:%02d' % (n // 75 // 60, n // 75 % 60, n % 75)


def parse_cue(path):
    tracks = []
    with open(path, encoding='latin-1') as f:
        for line in f:
            w = line.split()
            if not w:
                continue
            if w[0] == 'TRACK':
                tracks.append(Track(int(w[1]), w[2], None))
            elif w[0] == 'INDEX':
                m, s, fr = (int(x) for x in w[2].split(':'))
                lba = (m * 60 + s) * 75 + fr
                if int(w[1]) == 0:
                    tracks[-1].pregap = lba
                elif int(w[1]) == 1:
                    tracks[-1].start = lba
    return tracks


def parse_ccd(path):
    """CloneCD control file: [Entry n] with Point (track number), Control, PLBA; [TRACK n] with
    MODE and INDEX 0/1."""
    sect, entries, tr = None, [], {}
    cur = {}
    with open(path, encoding='latin-1') as f:
        for line in f:
            line = line.strip()
            m = re.match(r'\[(.+)\]$', line)
            if m:
                sect = m.group(1)
                cur = {}
                if sect.startswith('Entry'):
                    entries.append(cur)
                elif sect.startswith('TRACK'):
                    tr[int(sect.split()[1])] = cur
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                cur[k.strip()] = v.strip()
    tracks = []
    leadout = None
    for e in entries:
        point = int(e.get('Point', '0'), 0)
        lba = int(e.get('PLBA', '0'), 0)
        if point == 0xA2:
            leadout = lba
        elif 1 <= point <= 99:
            ctl = int(e.get('Control', '0'), 0)
            t = Track(point, 'DATA' if ctl & 4 else 'AUDIO', lba)
            x = tr.get(point, {})
            if 'INDEX 0' in x:
                t.pregap = int(x['INDEX 0'], 0)
            if 'INDEX 1' in x:
                t.start = int(x['INDEX 1'], 0)
            if 'MODE' in x and t.mode == 'DATA':
                t.mode = 'MODE%s' % x['MODE']
            tracks.append(t)
    tracks.sort(key=lambda t: t.number)
    return tracks, leadout


class Image:
    def __init__(self, path):
        self.path = path
        self.size = os.path.getsize(path)
        self.nsect = self.size // SECTOR
        self.f = open(path, 'rb')
        base = os.path.splitext(path)[0]
        self.source = None
        self.leadout = None
        self.tracks = []
        if os.path.exists(base + '.ccd'):
            self.tracks, self.leadout = parse_ccd(base + '.ccd')
            self.source = 'ccd'
        if not self.tracks and os.path.exists(base + '.cue'):
            self.tracks = parse_cue(base + '.cue')
            self.source = 'cue'
        if not self.tracks:
            self.tracks = [Track(1, 'MODE1/2352', 0)]
            self.source = 'none'
        for a, b in zip(self.tracks, self.tracks[1:]):
            a.end = b.start
        self.tracks[-1].end = self.nsect

    def raw(self, lba, count=1):
        self.f.seek(lba * SECTOR)
        return self.f.read(count * SECTOR)

    def sector(self, lba):
        """2048 bytes of user data of a mode 1 / mode 2 form 1 sector."""
        r = self.raw(lba)
        if len(r) < SECTOR:
            raise IOError('sector %d is past the end of the image' % lba)
        if r[:12] != SYNC:
            raise IOError('sector %d has no sync pattern (not a data sector)' % lba)
        if r[15] == 2:
            return r[24:24 + 2048]
        return r[16:16 + 2048]

    def read(self, lba, size):
        out = bytearray()
        while len(out) < size:
            out += self.sector(lba)
            lba += 1
        return bytes(out[:size])

    # ---- ISO 9660 ----
    def pvd(self):
        d = self.sector(16)
        if d[1:6] != b'CD001' or d[0] != 1:
            raise IOError('no ISO 9660 primary volume descriptor at sector 16')
        return d

    def volume(self):
        d = self.pvd()

        def a(s, e):
            return d[s:e].decode('cp932', 'replace').rstrip()
        return dict(system=a(8, 40), volume=a(40, 72), blocks=struct.unpack_from('<I', d, 80)[0],
                    block_size=struct.unpack_from('<H', d, 128)[0],
                    volume_set=a(190, 318), publisher=a(318, 446), preparer=a(446, 574),
                    application=a(574, 702), created=a(813, 830), modified=a(830, 847))

    def walk(self):
        """Yield (path, lba, size, date, is_dir) for every directory entry, depth first."""
        d = self.pvd()
        root = d[156:190]
        lba, size = struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0]
        seen = set()

        def rec(lba, size, prefix):
            if lba in seen:
                return
            seen.add(lba)
            data = self.read(lba, size)
            p = 0
            while p < len(data):
                n = data[p]
                if n == 0:                      # records do not cross sectors
                    p = (p // 2048 + 1) * 2048
                    continue
                r = data[p:p + n]
                p += n
                e_lba, e_size = struct.unpack_from('<I', r, 2)[0], struct.unpack_from('<I', r, 10)[0]
                y, mo, dd, hh, mi, ss = r[18:24]
                flags = r[25]
                name = r[33:33 + r[32]]
                if name in (b'\0', b'\1'):
                    continue
                nm = name.decode('cp932', 'replace')
                if not flags & 2:
                    nm = nm.split(';')[0]
                    if nm.endswith('.'):
                        nm = nm[:-1]
                date = '%04d-%02d-%02d %02d:%02d:%02d' % (1900 + y, mo, dd, hh, mi, ss)
                path = prefix + nm
                yield path, e_lba, e_size, date, bool(flags & 2)
                if flags & 2:
                    yield from rec(e_lba, e_size, path + '/')
        yield from rec(lba, size, '')

    def files(self):
        return [e for e in self.walk() if not e[4]]

    def file(self, path):
        want = path.strip('/').upper()
        for p, lba, size, _, is_dir in self.walk():
            if p.upper() == want and not is_dir:
                return self.read(lba, size)
        raise KeyError(path)

    # ---- audio ----
    def track(self, number):
        for t in self.tracks:
            if t.number == number:
                return t
        raise KeyError('track %d' % number)

    def pcm(self, t):
        self.f.seek(t.start * SECTOR)
        return self.f.read(t.sectors * SECTOR)


def cmd_tracks(img):
    print('image: %d bytes = %d sectors (%s), table from .%s%s'
          % (img.size, img.nsect, msf(img.nsect), img.source,
             ', lead-out %d' % img.leadout if img.leadout is not None else ''))
    print('track\tmode\tpregap\tstart\tstart_msf\tsectors\tlength\tseconds')
    for t in img.tracks:
        print('%d\t%s\t%s\t%d\t%s\t%d\t%s\t%.2f' % (
            t.number, t.mode, '' if t.pregap is None else t.pregap, t.start, msf(t.start),
            t.sectors, msf(t.sectors), t.sectors / 75))


def cmd_ls(img):
    v = img.volume()
    for k in ('system', 'volume', 'publisher', 'preparer', 'application', 'created', 'modified'):
        print('; %s: %s' % (k, v[k]))
    print('; blocks: %d x %d' % (v['blocks'], v['block_size']))
    n = total = 0
    for path, lba, size, date, is_dir in img.walk():
        print('%7d %9s  %s  %s%s' % (lba, '' if is_dir else size, date, path, '/' if is_dir else ''))
        if not is_dir:
            n += 1
            total += size
    print('; %d files, %d bytes' % (n, total))


def cmd_extract(img, outdir, wanted):
    wanted = {w.strip('/').upper() for w in wanted}
    n = 0
    root = os.path.realpath(outdir)
    for path, lba, size, date, is_dir in img.walk():
        parts = [p for p in path.split('/') if p not in ('', '.', '..')]
        dest = os.path.join(root, *parts)
        if not os.path.realpath(dest).startswith(root + os.sep):
            continue
        if is_dir:
            if not wanted:
                os.makedirs(dest, exist_ok=True)
            continue
        if wanted and path.upper() not in wanted:
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(img.read(lba, size))
        n += 1
    print('%d files -> %s' % (n, outdir))


def cmd_wav(img, number, out):
    t = img.track(number)
    if not t.audio:
        raise SystemExit('track %d is not an audio track' % number)
    with wave.open(out, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        img.f.seek(t.start * SECTOR)
        left = t.sectors
        while left:
            n = min(left, 512)
            w.writeframes(img.f.read(n * SECTOR))
            left -= n
    print('track %d: %d sectors, %.2f s -> %s' % (number, t.sectors, t.sectors / 75, out))


def cmd_audio(img):
    print('track\tseconds\tpeak\tlead_silence_s\ttrail_silence_s\tmd5')
    for t in img.tracks:
        if not t.audio:
            continue
        pcm = img.pcm(t)
        n = len(pcm) // 2
        s = struct.unpack('<%dh' % n, pcm[:n * 2])
        peak = max(max(s), -min(s)) if s else 0
        lead = 0
        while lead < n and -8 <= s[lead] <= 8:
            lead += 1
        trail = 0
        while trail < n - lead and -8 <= s[n - 1 - trail] <= 8:
            trail += 1
        print('%d\t%.2f\t%d\t%.2f\t%.2f\t%s' % (t.number, t.sectors / 75, peak, lead / 88200,
                                              trail / 88200, hashlib.md5(pcm).hexdigest()))


def arc_members(data):
    """[(name, offset, size)] of an AdvTowns archive."""
    first = struct.unpack_from('<I', data, 12)[0]
    if first % 16 or not 32 <= first <= len(data):
        raise ValueError('not an AdvTowns archive')
    ents = []
    for i in range(0, first, 16):
        name = data[i:i + 12].split(b'\0')[0].decode('ascii')
        ents.append((name, struct.unpack_from('<I', data, i + 12)[0]))
    if ents[-1][0] != '' or ents[-1][1] != len(data):
        raise ValueError('AdvTowns archive: bad end entry')
    out = []
    for (name, off), (_, nxt) in zip(ents, ents[1:]):
        if not off <= nxt <= len(data):
            raise ValueError('AdvTowns archive: offsets not ascending')
        out.append((name, off, nxt - off))
    return out


def cmd_arc(paths, outdir=None):
    for p in paths:
        with open(p, 'rb') as f:
            data = f.read()
        base = os.path.basename(p)
        for name, off, size in arc_members(data):
            if outdir is None:
                print('%s\t%s\t%d\t%d' % (base, name, off, size))
            else:
                if not re.match(r'[A-Za-z0-9_][A-Za-z0-9_.\- ]*$', name):
                    raise ValueError('unsafe member name %r' % name)
                os.makedirs(os.path.join(outdir, base), exist_ok=True)
                with open(os.path.join(outdir, base, name.upper()), 'wb') as f:
                    f.write(data[off:off + size])


def _gpc():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'source', 'tools'))
    import gpc
    return gpc


def towns_gpc(data):
    """AdvTowns picture -> (palette words, width, height, x, y, pixels, bytes consumed)."""
    gpc = _gpc()
    pal = struct.unpack_from('<16H', data, 0)
    w, h, x, y, k = struct.unpack_from('<5H', data, 0x20)
    if not (0 < w <= 640 and 0 < h <= 480 and k <= 8):
        raise ValueError('not an AdvTowns picture')
    rl = (w + 1) // 2
    buf, end = gpc.unpack_stream(data, 0x2A, (rl + 1) * h)
    for r in range(h):
        f = buf[r * (rl + 1)]
        if f:
            buf[r * (rl + 1)] = 1 << (f - 1)
    rows = gpc.deinterleave(gpc.unfilter_rows(buf, rl, h), 1 << (k - 1) if k else 1)
    px = bytearray()
    for r in rows:
        for b in r:
            px.append(b & 15)
            px.append(b >> 4)
    return pal, w, h, x, y, bytes(px), end


def cmd_gpc_png(outdir, paths):
    gpc = _gpc()
    os.makedirs(outdir, exist_ok=True)
    for p in paths:
        with open(p, 'rb') as f:
            pal, w, h, x, y, px, _ = towns_gpc(f.read())
        gpc.write_png(os.path.join(outdir, os.path.splitext(os.path.basename(p))[0] + '.png'),
                      w, h, px, gpc.palette_rgb4(pal))


def cmd_gpc_cmp(towns_dir, pc_dir):
    gpc = _gpc()
    pc = {}
    for root, _, files in os.walk(pc_dir):
        for fn in files:
            if fn.upper().endswith('.GPC'):
                with open(os.path.join(root, fn), 'rb') as f:
                    pc.setdefault(fn.upper(), set()).add(f.read())
    seen = {}
    for root, _, files in os.walk(towns_dir):
        for fn in sorted(files):
            if fn.upper().endswith('.GPC'):
                with open(os.path.join(root, fn), 'rb') as f:
                    seen.setdefault(fn.upper(), set()).add(f.read())
    n = same = 0
    for name in sorted(seen):
        for data in seen[name]:
            pal, w, h, x, y, px, end = towns_gpc(data)
            note = '' if end == len(data) else ' (stream ends at %d of %d)' % (end, len(data))
            if name not in pc:
                print('%-12s %dx%d+%d+%d  Towns only%s' % (name, w, h, x, y, note))
                continue
            n += 1
            res = []
            for pd in pc[name]:
                hdr, ppal, pw, ph, pxx, pyy, ppx = gpc.decode(pd)
                res.append(((pw, ph) == (w, h) and ppx == px, tuple(hdr['palette_raw']) == pal,
                            (pw, ph, pxx, pyy) == (w, h, x, y), (pw, ph, pxx, pyy)))
            best = max(res)
            if best[:3] == (True, True, True):
                same += 1
            else:
                print('%-12s %dx%d+%d+%d  pixels %s, palette %s, PC-98 geometry %dx%d+%d+%d%s'
                      % ((name, w, h, x, y, 'same' if best[0] else 'differ',
                          'same' if best[1] else 'differs') + best[3] + (note,)))
    print('%d pictures with a PC-98 namesake, %d identical in pixels, palette and position' % (n, same))


def cmd_se_wav(path, outdir):
    with open(path, 'rb') as f:
        d = f.read()
    n = struct.unpack_from('<H', d, 0)[0]
    os.makedirs(outdir, exist_ok=True)
    for i in range(n):
        off = struct.unpack_from('<I', d, 3 + 5 * i)[0]
        name = d[off:off + 8].split(b'\0')[0].decode('ascii')
        if not re.match(r'[A-Za-z0-9_]+$', name):
            raise ValueError('unsafe sample name %r' % name)
        _, size, ls, ll, rate, adj = struct.unpack_from('<IIIIHh', d, off + 8)
        hz = round(rate * 1000 / 98)
        pcm = bytes(b if b & 0x80 else 0x7F - b for b in d[off + 32:off + 32 + size])
        with wave.open(os.path.join(outdir, '%d_%s.wav' % (i, name)), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(1)
            w.setframerate(hz)
            w.writeframes(pcm)
        print('%d\t%s\t%d bytes\t%d Hz\tloop %d+%d\tnote %d' % (i, name, size, hz, ls, ll, d[off + 28]))


def main(argv):
    if len(argv) >= 4 and argv[1] == 'gpc-png':
        cmd_gpc_png(argv[2], argv[3:])
        return 0
    if len(argv) == 4 and argv[1] == 'gpc-cmp':
        cmd_gpc_cmp(argv[2], argv[3])
        return 0
    if len(argv) == 4 and argv[1] == 'se-wav':
        cmd_se_wav(argv[2], argv[3])
        return 0
    if len(argv) >= 3 and argv[1] == 'arc-ls':
        cmd_arc(argv[2:])
        return 0
    if len(argv) >= 4 and argv[1] == 'arc-extract':
        cmd_arc(argv[3:], argv[2])
        return 0
    if len(argv) < 3:
        sys.stderr.write(__doc__)
        return 2
    cmd, img = argv[1], Image(argv[2])
    if cmd == 'tracks':
        cmd_tracks(img)
    elif cmd == 'ls':
        cmd_ls(img)
    elif cmd == 'extract' and len(argv) >= 4:
        cmd_extract(img, argv[3], argv[4:])
    elif cmd == 'cat' and len(argv) == 4:
        sys.stdout.buffer.write(img.file(argv[3]))
    elif cmd == 'wav' and len(argv) == 5:
        cmd_wav(img, int(argv[3]), argv[4])
    elif cmd == 'audio':
        cmd_audio(img)
    else:
        sys.stderr.write(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
