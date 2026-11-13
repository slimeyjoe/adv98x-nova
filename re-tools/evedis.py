#!/usr/bin/env python3
"""Lister / checker / exporter for the `.EVE` scripts of the Windows release of NOVA (1996).

The Windows release runs on a different engine (`EVE.EXE`, MFC; "NOVA for Windows95") whose
scripts live in `EVE.PCK`. The grammar below is the one the interpreter in `EVE.EXE` reads
(function 0x40BFD0, dispatch table 0x40D1C0/0x40D288; docs/re/other-versions.md §2.2).

  python3 -I re-tools/evedis.py list FILE...            # listing on stdout
  python3 -I re-tools/evedis.py check FILE...           # every byte accounted for, jump targets valid
  python3 -I re-tools/evedis.py export OUTDIR FILE...   # listing/*.txt, strings.tsv, assets.tsv,
                                                        # flags.tsv, graph.tsv, ops.tsv
The exports hold the game's text: OUTDIR belongs under resources/derived/ (not committed).

File: every byte is stored inverted (XOR FFh). The plain stream is a sequence of instructions:
a 16-bit little-endian opcode, then operands of these kinds:
  w  16-bit little-endian word
  j  16-bit little-endian offset into the same file (a jump target)
  s  NUL-terminated string (Shift-JIS)
  n  number: a NUL-terminated string; if it starts with a digit, '+' or '-' it is a decimal
     literal, otherwise the name of a variable whose value is used
  e  condition: comparison (n n w) { w connector [comparison] }: connector 0 ends, 1 = AND, 2 = OR
"""
import collections
import os
import sys

# opcode -> (name, operand kinds); '?' kinds are resolved in decode()
OPS = {
    0x00: ('end', ''),            # return from `call`, or end of the program
    0x10: ('text', 's'),          # print in the text frame; %s = the player's name
    0x11: ('text-frame', 'nnnn'), # x1 y1 x2 y2 in pixels -> variables TextX1 TextY1 TextX2 TextY2
    0x12: ('text-color', 'wn'),
    0x13: ('text-raw', 's'),
    0x14: ('text-pos', 'nn'),
    0x21: ('nop-21', ''),
    0x30: ('wait', 'w?'),         # 1: key; 2 "return": key (text page); 3 default: name input; 4: ?
    0x40: ('delay', 'n'),         # n * 10 ms
    0x41: ('delay-ms', 'n'),
    0x50: ('menu-begin', ''),
    0x51: ('menu-item', 'wsjw?'), # default-item, text, offset after the item's body, has-cond [e]
    0x52: ('menu-jump', 'j'),
    0x53: ('menu-run', ''),
    0x60: ('switch', 'n'),
    0x61: ('case', 'nj'),         # if switch value != n: jump
    0x62: ('case-end', 'j'),
    0x63: ('switch-end', ''),
    0x64: ('jump', 'j'),
    0x65: ('if', 'ej'),           # jump if false
    0x66: ('else', 'j'),
    0x67: ('if2', 'ej'),          # jump if false
    0x68: ('jump2', 'j'),
    0x69: ('until', 'ej'),        # jump if true
    0x6A: ('cycle', 'w'),         # the word is a counter the interpreter increments in the script
    0x6B: ('cycle-alt', 'jw?'),
    0x6C: ('cycle-end', 'j'),
    0x6D: ('cycle-run', ''),
    0x6E: ('while', 'ej'),        # jump if false
    0x70: ('set', 'sn'),          # variable := n
    0x71: ('calc', 'nnnws'),      # variable s := a op b (third number unused); 1 + 2 - 3 / 4 *
    0x73: ('nop-73', ''),
    0x80: ('image', 'wwws'),      # x y key (FFFF = none), file
    0x81: ('map-load', 's'),
    0x82: ('goto-script', 's'),
    0x83: ('call-script', 's'),
    0x90: ('effect', 'n?'),
    0x91: ('effect-91', 'nn'),
    0x92: ('effect-92', 'nnnnn'),
    0xC0: ('play', 'w?'),         # 0 n: CD track; 1 s: wave file
    0xC1: ('stop', 'w'),          # 0: CD; 1: wave
    0xC2: ('repeat', 'w?'),       # 0 w: [repeatCDAUDIO] := w; 1 w: [repeatWAVE] := w
    0xD0: ('title', 's'),
    0xD1: ('mkdir', 's'),
    0xD2: ('sys-save', ''),       # write EVE.EVS
    0xD3: ('sys-load', ''),       # read EVE.EVS
    0xD4: ('sys-get', 'sn'),      # variable s := system value n
    0xD5: ('sys-set', 'nn'),      # system value a := b
    0xD7: ('reset', 'n'),         # 0: clear all variables and set the defaults
}
# sub-commands of `effect` that take one more number (the others take none: jump table 0x40D380)
EFFECT_SUBS = {1, 2, 3, 4, 5, 6, 7, 8, 50, 51, 52, 60, 61, 70, 71, 72, 73, 80}
# comparison codes, written here as "a OP b" for the operands in file order (the interpreter
# evaluates them the other way round: code 2 is "b > a"); 6 and 7 are never true
CMP = {1: '==', 2: '<', 3: '<=', 4: '>', 5: '>=', 8: '!='}


class ParseError(Exception):
    pass


def decrypt(raw):
    return bytes(b ^ 0xFF for b in raw)


class Ins:
    __slots__ = ('start', 'end', 'op', 'args')

    def __init__(self, start, end, op, args):
        self.start, self.end, self.op, self.args = start, end, op, args

    @property
    def name(self):
        return OPS[self.op][0]

    def vals(self, kind):
        return [v for k, v in self.args if k == kind]


def decode(d):
    """Plain (already inverted) script bytes -> [Ins]. Raises ParseError on anything unknown."""
    out = []
    p = 0
    n = len(d)

    def word():
        nonlocal p
        if p + 2 > n:
            raise ParseError('word past the end at %#x' % p)
        v = d[p] | d[p + 1] << 8
        p += 2
        return v

    def string():
        nonlocal p
        q = d.find(b'\0', p)
        if q < 0:
            raise ParseError('unterminated string at %#x' % p)
        s = d[p:q]
        p = q + 1
        return s

    def compare(args):
        args.append(('n', string()))
        args.append(('n', string()))
        args.append(('cmp', word()))

    def expr(args):
        compare(args)
        while True:
            c = word()
            args.append(('conn', c))
            if c == 0:
                return
            if c in (1, 2):
                compare(args)

    while p < n:
        s = p
        op = word()
        if op not in OPS:
            raise ParseError('unknown opcode %04X at %#x' % (op, s))
        args = []
        for k in OPS[op][1]:
            if k == 'w':
                args.append(('w', word()))
            elif k == 'j':
                args.append(('j', word()))
            elif k == 's':
                args.append(('s', string()))
            elif k == 'n':
                args.append(('n', string()))
            elif k == 'e':
                expr(args)
            elif op == 0x30:
                if args[0][1] in (1, 2, 3, 4):
                    args.append(('s', string()))
                else:
                    raise ParseError('wait: sub-command %d at %#x' % (args[0][1], s))
            elif op in (0x51, 0x6B):
                if args[-1][1]:
                    expr(args)
            elif op == 0x90:
                sub = args[0][1]
                if not sub.isdigit():
                    raise ParseError('effect: variable sub-command at %#x' % s)
                if int(sub) in EFFECT_SUBS:
                    args.append(('n', string()))
            elif op == 0xC0:
                if args[0][1] == 0:
                    args.append(('n', string()))
                elif args[0][1] == 1:
                    args.append(('s', string()))
            elif op == 0xC2:
                if args[0][1] in (0, 1):
                    args.append(('w', word()))
        out.append(Ins(s, p, op, args))
    return out


def text(b):
    return b.decode('cp932', 'replace')


def is_literal(b):
    return b[:1].isdigit() or b[:1] in (b'-', b'+')


def fmt_expr(args):
    out = []
    i = 0
    while i < len(args):
        k, v = args[i]
        if k == 'n':
            a, b, c = args[i][1], args[i + 1][1], args[i + 2][1]
            out.append('%s %s %s' % (text(a), CMP.get(c, 'cmp%d' % c), text(b)))
            i += 3
        elif k == 'conn':
            if v:
                out.append({1: 'and', 2: 'or'}.get(v, 'conn%d' % v))
            i += 1
        else:
            break
    return ' '.join(out), i


def fmt(ins):
    parts = [ins.name]
    a = ins.args
    i = 0
    while i < len(a):
        k, v = a[i]
        if k == 'w':
            parts.append('-' if v == 0xFFFF else str(v))
        elif k == 'j':
            parts.append('@%04X' % v)
        elif k == 's':
            parts.append('"%s"' % text(v))
        elif k == 'n' and (i + 2 < len(a) and a[i + 2][0] == 'cmp'):
            e, used = fmt_expr(a[i:])
            parts.append('(%s)' % e)
            i += used
            continue
        elif k == 'n':
            parts.append(text(v))
        i += 1
    return ' '.join(parts)


def load(path):
    with open(path, 'rb') as f:
        return decrypt(f.read())


def check(path):
    """Coverage and jump-target check; returns a list of problems."""
    d = load(path)
    ins = decode(d)
    probs = []
    pos = 0
    for x in ins:
        if x.start != pos:
            probs.append('gap at %#x' % pos)
        pos = x.end
    if pos != len(d):
        probs.append('ends at %#x of %#x' % (pos, len(d)))
    starts = {x.start for x in ins} | {len(d)}
    for x in ins:
        for t in x.vals('j'):
            if t not in starts:
                probs.append('%04X %s: target %#x is not an instruction' % (x.start, x.name, t))
    return ins, probs


def names(paths):
    for p in paths:
        yield os.path.splitext(os.path.basename(p))[0].upper(), p


def cmd_list(paths):
    for name, p in names(paths):
        print('; %s' % name)
        for x in decode(load(p)):
            print('%04X  %s' % (x.start, fmt(x)))


def cmd_check(paths):
    bad = 0
    total = collections.Counter()
    nbytes = 0
    for name, p in names(paths):
        try:
            ins, probs = check(p)
        except ParseError as e:
            print('%s: %s' % (name, e))
            bad += 1
            continue
        nbytes += os.path.getsize(p)
        for x in ins:
            total[x.op] += 1
        if probs:
            bad += 1
            for q in probs:
                print('%s: %s' % (name, q))
    print('%d files, %d bytes, %d instructions, %d opcodes used, %d files with problems'
          % (len(paths), nbytes, sum(total.values()), len(total), bad))
    return 1 if bad else 0


def cmd_export(outdir, paths):
    os.makedirs(os.path.join(outdir, 'listing'), exist_ok=True)
    strings, assets, flags, graph = [], [], [], []
    ops = collections.Counter()
    for name, p in names(paths):
        ins = decode(load(p))
        with open(os.path.join(outdir, 'listing', name + '.txt'), 'w', encoding='utf-8') as f:
            for x in ins:
                f.write('%04X  %s\n' % (x.start, fmt(x)))
        for x in ins:
            ops[x.name] += 1
            if x.op in (0x10, 0x13):
                strings.append((name, x.start, x.name, text(x.args[0][1])))
            elif x.op == 0x51:
                strings.append((name, x.start, 'menu-item', text(x.args[1][1])))
            elif x.op == 0x30 and x.args[0][1] == 3:
                strings.append((name, x.start, 'name-default', text(x.args[1][1])))
            elif x.op in (0x80, 0x81):
                assets.append((name, x.start, x.name, text(x.vals('s')[0])))
            elif x.op == 0xC0:
                assets.append((name, x.start, 'play-cd' if x.args[0][1] == 0 else 'play-wave',
                               text(x.args[1][1]) if len(x.args) > 1 else ''))
            elif x.op in (0x82, 0x83):
                graph.append((name, x.start, x.name, text(x.args[0][1]).upper()))
            if x.op == 0x70:
                flags.append((name, x.start, 'set', text(x.args[0][1]), text(x.args[1][1])))
            elif x.op == 0x71:
                flags.append((name, x.start, 'set', text(x.args[4][1]), 'calc'))
            elif x.op == 0xD4:
                flags.append((name, x.start, 'set', text(x.args[0][1]), 'sys ' + text(x.args[1][1])))
            for i, (k, v) in enumerate(x.args):
                if k == 'n' and not is_literal(v):
                    flags.append((name, x.start, 'read', text(v), x.name))

    def tsv(fn, head, rows):
        with open(os.path.join(outdir, fn), 'w', encoding='utf-8') as f:
            f.write('\t'.join(head) + '\n')
            for r in rows:
                f.write('\t'.join(('%04X' % c) if isinstance(c, int) else c for c in r) + '\n')
    tsv('strings.tsv', ('script', 'offset', 'kind', 'text'), strings)
    tsv('assets.tsv', ('script', 'offset', 'op', 'name'), assets)
    tsv('flags.tsv', ('script', 'offset', 'access', 'variable', 'detail'), flags)
    tsv('graph.tsv', ('script', 'offset', 'op', 'target'), graph)
    with open(os.path.join(outdir, 'ops.tsv'), 'w', encoding='utf-8') as f:
        f.write('op\tcount\n')
        for k, v in sorted(ops.items()):
            f.write('%s\t%d\n' % (k, v))
    print('%d scripts -> %s' % (len(paths), outdir))


def main(argv):
    if len(argv) >= 3 and argv[1] == 'list':
        cmd_list(argv[2:])
    elif len(argv) >= 3 and argv[1] == 'check':
        return cmd_check(argv[2:])
    elif len(argv) >= 4 and argv[1] == 'export':
        cmd_export(argv[2], argv[3:])
    else:
        sys.stderr.write(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
