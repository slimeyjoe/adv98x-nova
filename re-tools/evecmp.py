#!/usr/bin/env python3
"""Compare the scripts of the other releases of NOVA with the PC-98 scripts, file by file.

  python3 -I re-tools/evecmp.py win   PC98_MES_DIR WIN_DIR   [-o OUTDIR]   # Windows .EVE scripts
  python3 -I re-tools/evecmp.py towns PC98_MES_DIR TOWNS_DIR [-o OUTDIR]   # FM Towns .MES scripts
  python3 -I re-tools/evecmp.py towns-check TOWNS_DIR                      # parse coverage only

PC98_MES_DIR  resources/original/pc98/A/MES
WIN_DIR       resources/original/win (the members of EVE.PCK)
TOWNS_DIR     output of `cdimg.py arc-extract` (one sub-directory per NOVA.0xx archive)

Each script is reduced to a list of events in file order (not execution order):
  line   a run of printed text up to the next key wait (PC-98 prints the speaker tag and the
         sentence as two text runs with a `proc` between, and some scripts keep the tag in a
         procedure, which is expanded here; Windows has one string per line)
  menu   the text of a menu item
  pic    a picture file loaded (name without directory and extension)
  snd    a music file / CD track / sound effect started
  set    a flag or variable assigned;  test: a flag or variable tested
  jump   a script chained to
Text is compared after normalisation: brackets ［］ = 【】, the name placeholder ＊＊＊ = %s, and
spaces and line breaks dropped (the releases wrap lines differently). Lines are aligned with
difflib; a pair in a replaced block counts as "differing" when at least half of it matches,
otherwise the lines count as present in one release only.

Stdout gets a table per script and totals; OUTDIR (default: none) gets text.tsv (every line
that is not equal), music.tsv (which PC-98 file is started where the other release starts
which track), pictures.tsv, flags.tsv and summary.tsv. The TSVs hold game text: OUTDIR belongs
under resources/derived/.

The Towns scripts are in a dialect of the PC-98 format (class TownsScript):
  * a variable token is 3 bytes: 10h+op (0 set / equal, 2 add / >=, 4 subtract / <=),
    variable index * 2, value
  * `sound` (D0) takes a two-letter device first: `cd n` (CD track through the table NOVA.CDT),
    `se n` (sample n of NOVA.SE), and `fm` / `pm` / `cd` / `se` "file" to load the tables
  * D5 is not `decrypt` but `D5 n "file"`: open archive file n
Everything else parses with source/tools/mes.py unchanged.
"""
import collections
import difflib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'source', 'tools'))
sys.path.insert(0, HERE)
import mes      # noqa: E402
import evedis   # noqa: E402


# --------------------------------------------------------------------------------------------
# FM Towns dialect of .MES

class TownsScript(mes.Script):
    def _regvar(self, p):
        d = self.data
        if d[p] < 0x10:
            return mes.Script._regvar(self, p)
        op = {0: '=', 2: '+', 4: '-'}.get(d[p] & 0xF)
        if op is None or d[p + 1] & 1:
            raise mes.ParseError('variable token %02X %02X at %#x' % (d[p], d[p + 1], p))
        self._mark(p, p + 3)
        return ('var', p, p + 3, d[p + 1] >> 1, op, d[p + 2])

    def _conds(self, p):
        out = []
        while self.data[p] < 0x20:
            n = self._regvar(p)
            out.append(n)
            p = n[2]
        return out, p

    def _run(self, p, out):
        """mes.Script._run with the token length of flag / variable tokens taken from the node."""
        d = self.data
        text_start, text = None, []

        def flush(at):
            nonlocal text_start, text
            if text:
                out.append(('text', text_start, at, mes.decode_text(b''.join(text))))
            text_start, text = None, []
        while True:
            b = d[p]
            if b == 0xFF and d[p + 1] in (0xFF, 0xFE):
                flush(p)
                self._mark(p, p + 2)
                out.append(('end', p, p + 2, 'FF%02X' % d[p + 1]))
                return p + 2, d[p + 1] | 0xFF00
            if 0xA0 <= b <= 0xA4:
                flush(p)
                self._mark(p, p + 1)
                return p + 1, b
            if mes.is_lead(b):
                w = b << 8 | d[p + 1]
                ctl = {0x8197: 'nop', 0x8190: 'key-clear', 0x816F: 'loop-begin',
                       0x8170: 'loop-end'}.get(w)
                self._mark(p, p + 2)
                if ctl:
                    flush(p)
                    out.append(('ctl', p, p + 2, ctl))
                else:
                    if text_start is None:
                        text_start = p
                    text.append(bytes(d[p:p + 2]))
                p += 2
            elif b == 0x21:
                flush(p)
                q = d.index(0, p)
                self._mark(p, q + 1)
                out.append(('ascii', p, q + 1, bytes(d[p + 1:q])))
                p = q + 1
            elif b < 0x20:
                flush(p)
                n = self._regvar(p)
                out.append(n)
                p = n[2]
            elif b == 0xA5:
                flush(p)
                self._mark(p, p + 1)
                out.append(('nl', p, p + 1))
                p += 1
            elif 0x2D <= b <= 0x7F:
                self._mark(p, p + 1)
                if text_start is None:
                    text_start = p
                text.append(bytes((0x82, b + 0x72)))
                p += 1
            elif 0xA6 <= b <= 0xD8:
                flush(p)
                p = self._op(p, out)
            else:
                raise mes.ParseError('byte %02X at %#x is not a statement' % (b, p))

    def _op(self, p, out):
        d = self.data
        op = d[p]
        if op == 0xD0 and bytes(d[p + 1:p + 3]) in (b'cd', b'se', b'fm', b'pm'):
            s = p
            self._mark(p, p + 3)
            args = [('letter', bytes(d[p + 1:p + 3]).decode('ascii'))]
            p += 3
            while d[p] == 0x20:
                self._mark(p, p + 1)
                p += 1
            if d[p] == 0x22:
                a, p = self._str(p)
            else:
                a, p = self._num(p)
            args.append(a)
            out.append(('op', s, p, op, args, []))
            return p
        if op == 0xD5:
            s = p
            self._mark(p, p + 1)
            n, p = self._num(p + 1)
            a, p = self._str(p)
            out.append(('op', s, p, op, [n, a], []))
            return p
        return mes.Script._op(self, p, out)


# --------------------------------------------------------------------------------------------
# events

def stem(name):
    name = name.replace('\\', '/').split('/')[-1].split(':')[-1]
    return os.path.splitext(name)[0].upper()


def mes_events(sc, towns=False):
    ev = []
    buf = []
    procs = {}                # slot -> text printed by the procedure (speaker tags)

    def flush(kind='line'):
        if buf:
            ev.append((kind, ''.join(buf)))
            del buf[:]

    def cond(nodes):
        for n in nodes:
            if n[0] == 'reg':
                ev.append(('test', 'f%d' % n[3]))
            else:
                ev.append(('test', mes.var_name(n[3])))

    def body(nodes):
        for n in nodes:
            k = n[0]
            if k == 'text':
                buf.append(n[3])
            elif k == 'ascii':
                buf.append(mes.decode_text(n[3]))
            elif k == 'nl':
                pass
            elif k == 'ctl':
                if n[3] == 'key-clear':
                    flush()
            elif k == 'reg':
                flush()
                ev.append(('set', 'f%d' % n[3], '%d' % n[4]))
            elif k == 'var':
                flush()
                ev.append(('set', mes.var_name(n[3]), '%s%d' % (n[4], n[5])))
            elif k == 'op':
                op, args, blocks = n[3], n[4], n[5]
                if op == 0xBA:                           # proc: a speaker tag kept in a procedure
                    if procs.get(args[0]):
                        buf.append(procs[args[0]])
                    continue
                if op in (0xA6, 0xA7, 0xA8):             # text-frame, text-pos, text-color
                    continue
                flush()
                if op == 0xB9:                           # define-proc: remember the text it prints
                    procs[args[0]] = ''.join(m[3] for m in blocks[0]['body'] if m[0] == 'text')
                    body([m for m in blocks[0]['body'] if m[0] != 'text'])
                    flush()
                    continue
                if op == 0xC9:
                    ev.append(('pic', stem(args[0][1].decode('cp932', 'replace'))))
                elif op == 0xB1:
                    ev.append(('jump', stem(args[0][1].decode('cp932', 'replace'))))
                elif op == 0xD0:
                    a = args[0] if args else None
                    if isinstance(a, tuple) and a[0] == 'str':
                        ev.append(('snd', stem(a[1].decode('cp932', 'replace'))))
                    elif isinstance(a, tuple) and a[0] == 'letter':
                        b = args[1] if len(args) > 1 else None
                        if isinstance(b, tuple):
                            if towns and a[1] in ('cd', 'fm', 'pm'):
                                continue                  # loading a table
                            ev.append(('snd', stem(b[1].decode('cp932', 'replace'))))
                        elif b is not None:
                            ev.append(('snd', '%s %d' % (a[1], b)))
                for b in blocks:
                    cond(b['conds'])
                    body(b['body'])
                    flush('menu' if b['kind'] in ('item', 'verb', 'noun') else 'line')
    for seg in sc.segments:
        cond(seg['conds'])
        body(seg['body'])
        flush()
    return ev


WIN_VARS = {'gmode': 'A'}


def eve_events(ins):
    ev = []
    buf = []

    def flush():
        if buf:
            ev.append(('line', ''.join(buf)))
            del buf[:]

    def var(b):
        v = evedis.text(b)
        return WIN_VARS.get(v, v)
    for x in ins:
        if x.op in (0x10, 0x13):
            buf.append(evedis.text(x.args[0][1]))
            continue
        if x.op in (0x11, 0x12, 0x14):
            continue
        flush()
        if x.op == 0x51:
            ev.append(('menu', evedis.text(x.args[1][1])))
        elif x.op == 0x80:
            ev.append(('pic', stem(evedis.text(x.args[3][1]))))
        elif x.op == 0x82:
            ev.append(('jump', stem(evedis.text(x.args[0][1]))))
        elif x.op == 0xC0:
            if x.args[0][1] == 0:
                ev.append(('snd', 'cd %s' % evedis.text(x.args[1][1])))
            elif len(x.args) > 1:
                ev.append(('snd', stem(evedis.text(x.args[1][1]))))
        elif x.op == 0x70:
            ev.append(('set', var(x.args[0][1]), evedis.text(x.args[1][1])))
        elif x.op == 0x71:
            a, b, _, o, dst = (v for _, v in x.args)
            ev.append(('set', var(dst), '%s%s' % ({1: '+', 2: '-', 3: '/', 4: '*'}.get(o, '?'),
                                                 evedis.text(b))))
        for i, (k, v) in enumerate(x.args):
            if k == 'n' and not evedis.is_literal(v) and x.op not in (0x70, 0x71):
                ev.append(('test', var(v)))
    flush()
    return ev


_DROP = re.compile('[\\s\u3000]+')


def norm(s):
    s = s.replace('［', '【').replace('］', '】').replace('＊＊＊', '%s')
    return _DROP.sub('', s)


# --------------------------------------------------------------------------------------------
# comparison

def align_text(a, b):
    """a, b: lists of raw strings. Returns (equal, [(status, a_text, b_text)]) with status
    'differ' / 'only-a' / 'only-b'."""
    na, nb = [norm(x) for x in a], [norm(x) for x in b]
    sm = difflib.SequenceMatcher(None, na, nb, autojunk=False)
    equal = 0
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            equal += i2 - i1
            continue
        ia, ib = list(range(i1, i2)), list(range(j1, j2))
        # pair up similar lines inside the block, keeping the order
        j = 0
        for i in ia:
            best = None
            for jj in range(j, len(ib)):
                r = difflib.SequenceMatcher(None, na[i], nb[ib[jj]], autojunk=False).ratio()
                if r >= 0.5:
                    best = jj
                    break
            if best is None:
                out.append(('only-a', a[i], ''))
            else:
                for jj in range(j, best):
                    out.append(('only-b', '', b[ib[jj]]))
                out.append(('differ', a[i], b[ib[best]]))
                j = best + 1
        for jj in range(j, len(ib)):
            out.append(('only-b', '', b[ib[jj]]))
    return equal, out


FLAG_SKIP_A = {'S', 'V', 'N'}                # menu results of the PC-98 interpreter
FLAG_SKIP_B = {'exit', 'return', '[WindowMode]', '[PaletteMode]', 'TextX1', 'TextX2',
               'TextY1', 'TextY2'}


def compare(pc, other, label, outdir, sound_key, skip_b):
    """pc, other: {script name: events}."""
    names = sorted(set(pc) & set(other))
    print('scripts: PC-98 %d, %s %d, common %d' % (len(pc), label, len(other), len(names)))
    print('  only PC-98: %s' % (' '.join(sorted(set(pc) - set(other))) or '-'))
    print('  only %s: %s' % (label, ' '.join(sorted(set(other) - set(pc))) or '-'))

    # music mapping, pass 1: scripts with the same number of sound events, paired by position
    tally = collections.Counter()
    for n in names:
        a = [e[1] for e in pc[n] if e[0] == 'snd']
        b = [e[1] for e in other[n] if e[0] == 'snd']
        if len(a) == len(b):
            tally.update(zip(a, b))
    mapping = {}
    for (a, b), c in sorted(tally.items(), key=lambda kv: -kv[1]):
        mapping.setdefault(a, b)

    rows, text_rows, pic_rows, snd_rows, flag_rows = [], [], [], [], []
    tot = collections.Counter()
    pic_only_a, pic_only_b = collections.Counter(), collections.Counter()
    print('\n%-8s %6s %6s %6s %6s  %s' % ('script', 'equal', 'differ', 'pc98', label[:6], 'other differences'))
    for n in names:
        ea, eb = pc[n], other[n]
        notes = []
        res = {}
        for kind in ('line', 'menu'):
            a = [e[1] for e in ea if e[0] == kind]
            b = [e[1] for e in eb if e[0] == kind]
            eq, diffs = align_text(a, b)
            c = collections.Counter(d[0] for d in diffs)
            res[kind] = (eq, c['differ'], c['only-a'], c['only-b'])
            for st, x, y in diffs:
                text_rows.append((n, kind, st.replace('only-a', 'only-pc98').replace('only-b', 'only-' + label), x, y))
        eq, df, oa, ob = (sum(res[k][i] for k in res) for i in range(4))
        tot.update(equal=eq, differ=df, only_pc=oa, only_other=ob,
                   menu_eq=res['menu'][0], menu_other=sum(res['menu'][1:]))
        # pictures
        pa = collections.Counter(e[1] for e in ea if e[0] == 'pic')
        pb = collections.Counter(e[1] for e in eb if e[0] == 'pic')
        oa_p, ob_p = sorted(set(pa) - set(pb)), sorted(set(pb) - set(pa))
        for s in oa_p:
            pic_only_a[s] += 1
            pic_rows.append((n, 'only-pc98', s, str(pa[s])))
        for s in ob_p:
            pic_only_b[s] += 1
            pic_rows.append((n, 'only-' + label, s, str(pb[s])))
        if oa_p or ob_p:
            notes.append('pics -%s +%s' % (','.join(oa_p) or '-', ','.join(ob_p) or '-'))
        # music
        sa = [mapping.get(e[1], e[1]) for e in ea if e[0] == 'snd']
        sb = [e[1] for e in eb if e[0] == 'snd']
        if sa != sb:
            sm = difflib.SequenceMatcher(None, sa, sb, autojunk=False)
            d = []
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag != 'equal':
                    d.append('%s>%s' % ('/'.join(sa[i1:i2]) or '-', '/'.join(sb[j1:j2]) or '-'))
                    snd_rows.append((n, '/'.join(sa[i1:i2]), '/'.join(sb[j1:j2])))
            notes.append('snd ' + ' '.join(d))
            tot['snd_scripts'] += 1
        # flags and variables
        fa = collections.Counter((e[1], e[2]) for e in ea if e[0] == 'set' and e[1] not in FLAG_SKIP_A)
        fb = collections.Counter((e[1], e[2].lstrip('=')) for e in eb if e[0] == 'set' and e[1] not in skip_b)
        fa = collections.Counter({(k, v.lstrip('=')): c for (k, v), c in fa.items()})
        ta = {e[1] for e in ea if e[0] == 'test' and e[1] not in FLAG_SKIP_A}
        tb = {e[1] for e in eb if e[0] == 'test' and e[1] not in skip_b}
        d = []
        for k in sorted(set(fa) | set(fb)):
            if fa[k] != fb[k]:
                d.append('%s=%s:%d/%d' % (k[0], k[1], fa[k], fb[k]))
                flag_rows.append((n, 'set', '%s=%s' % k, str(fa[k]), str(fb[k])))
        for k in sorted(ta ^ tb):
            d.append('test %s:%s' % (k, 'pc98' if k in ta else label))
            flag_rows.append((n, 'test', k, str(int(k in ta)), str(int(k in tb))))
        if d:
            notes.append('flags ' + ' '.join(d))
            tot['flag_scripts'] += 1
        ja = sorted({e[1] for e in ea if e[0] == 'jump'})
        jb = sorted({e[1] for e in eb if e[0] == 'jump'})
        if ja != jb:
            notes.append('jumps -%s +%s' % (','.join(sorted(set(ja) - set(jb))) or '-',
                                           ','.join(sorted(set(jb) - set(ja))) or '-'))
            tot['jump_scripts'] += 1
        rows.append((n, eq, df, oa, ob, '; '.join(notes)))
        print('%-8s %6d %6d %6d %6d  %s' % (n, eq, df, oa, ob, '; '.join(notes)))
    print('\ntotal    %6d %6d %6d %6d   (of these menu items: %d equal, %d not)'
          % (tot['equal'], tot['differ'], tot['only_pc'], tot['only_other'], tot['menu_eq'], tot['menu_other']))
    print('scripts with music differences: %d, flag differences: %d, jump differences: %d'
          % (tot['snd_scripts'], tot['flag_scripts'], tot['jump_scripts']))
    print('\npictures loaded only by PC-98 (scripts): %s'
          % ' '.join('%s(%d)' % kv for kv in sorted(pic_only_a.items())))
    print('pictures loaded only by %s (scripts): %s'
          % (label, ' '.join('%s(%d)' % kv for kv in sorted(pic_only_b.items()))))
    print('\nmusic: PC-98 file -> %s (count, from scripts with equally many sound events)' % label)
    for (a, b), c in sorted(tally.items(), key=lambda kv: (sound_key(kv[0][0]), -kv[1])):
        print('  %-8s %-10s %3d%s' % (a, b, c, '' if mapping[a] == b else '   <- minority'))

    if outdir:
        os.makedirs(outdir, exist_ok=True)

        def tsv(fn, head, data):
            with open(os.path.join(outdir, fn), 'w', encoding='utf-8') as f:
                f.write('\t'.join(head) + '\n')
                for r in data:
                    f.write('\t'.join(str(c).replace('\r', '\\r').replace('\n', '\\n').replace('\t', ' ')
                                      for c in r) + '\n')
        tsv('summary.tsv', ('script', 'equal', 'differ', 'only_pc98', 'only_' + label, 'notes'), rows)
        tsv('text.tsv', ('script', 'kind', 'status', 'pc98', label), text_rows)
        tsv('pictures.tsv', ('script', 'status', 'picture', 'loads'), pic_rows)
        tsv('music-diff.tsv', ('script', 'pc98_mapped', label), snd_rows)
        tsv('music.tsv', ('pc98', label, 'count'), [(a, b, c) for (a, b), c in sorted(tally.items())])
        tsv('flags.tsv', ('script', 'access', 'what', 'pc98', label), flag_rows)
        print('\ndetails -> %s' % outdir)


def load_pc(d, cls=mes.Script, towns=False):
    out = {}
    for root, _, files in os.walk(d):
        for fn in sorted(files):
            if fn.upper().endswith('.MES'):
                with open(os.path.join(root, fn), 'rb') as f:
                    data = f.read()
                name = stem(fn)
                ev = mes_events(cls(data).parse(), towns)
                if name in out and out[name] != ev:
                    sys.stderr.write('warning: %s exists in several versions; first one used\n' % name)
                out.setdefault(name, ev)
    return out


def load_win(d):
    out = {}
    for fn in sorted(os.listdir(d)):
        if fn.upper().endswith('.EVE'):
            out[stem(fn)] = eve_events(evedis.decode(evedis.load(os.path.join(d, fn))))
    return out


def towns_check(d):
    n = bad = 0
    seen = set()
    for root, _, files in os.walk(d):
        for fn in sorted(files):
            if not fn.upper().endswith(('.MES', '.INI')):
                continue
            with open(os.path.join(root, fn), 'rb') as f:
                data = f.read()
            if data in seen:
                continue
            seen.add(data)
            n += 1
            try:
                sc = TownsScript(data).parse()
            except (mes.ParseError, IndexError, ValueError) as e:
                print('%s: %s' % (fn, e))
                bad += 1
                continue
            if sc.covered.count(0) or sc.trailer:
                print('%s: %d bytes not covered, trailer %r' % (fn, sc.covered.count(0), sc.trailer))
                bad += 1
            for off, what in sc.defects:
                print('%s: defect at %#x: %s' % (fn, off, what))
    print('%d distinct scripts, %d with problems' % (n, bad))
    return 1 if bad else 0


def uso_key(s):
    return (0 if s.startswith('NV') and not s.startswith('NVSE') else 1 if s.startswith('NVSE') else 2, s)


def main(argv):
    args = argv[1:]
    outdir = None
    if '-o' in args:
        i = args.index('-o')
        outdir = args[i + 1]
        del args[i:i + 2]
    if len(args) == 3 and args[0] == 'win':
        compare(load_pc(args[1]), load_win(args[2]), 'win', outdir, uso_key, FLAG_SKIP_B)
    elif len(args) == 3 and args[0] == 'towns':
        compare(load_pc(args[1]), load_pc(args[2], TownsScript, True), 'towns', outdir, uso_key,
                FLAG_SKIP_A)
    elif len(args) == 2 and args[0] == 'towns-check':
        return towns_check(args[1])
    else:
        sys.stderr.write(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
