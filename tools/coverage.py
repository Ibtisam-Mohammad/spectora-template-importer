"""Cell-level import coverage: what the schema consumes, and what it leaves behind.

    python tools/coverage.py fixtures/spectora/probe-html.xls [more.xls ...]
"""
import zipfile, re, sys
import xml.etree.ElementTree as ET
from collections import Counter

M = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'; NS = {'m': M}
def cn(i):
    s = ''; i += 1
    while i: i, r = divmod(i - 1, 26); s = chr(65 + r) + s
    return s
def ci(c):
    n = 0
    for ch in c: n = n * 26 + (ord(ch) - 64)
    return n - 1
def load(p):
    root = ET.fromstring(zipfile.ZipFile(p).read('xl/worksheets/sheet1.xml'))
    out = []
    for r in root.findall('.//m:row', NS):
        d = {}
        for c in r.findall('m:c', NS):
            v = c.find('m:v', NS)
            d[ci(''.join(x for x in c.get('r') if x.isalpha()))] = (v.text or '') if v is not None else ''
        out.append(d)
    return out

# Columns the schema in docs/design/schema.md stores: all 42.
MODELLED = {
    0: 'section.name', 1: 'item.name', 2: 'comment.name', 3: 'comment.body_html',
    4: 'comment.comment_type', 5: 'comment.severity', 6: 'comment.choices',
    7: 'comment.unit_options', 8: 'comment.recommendation', 9: 'comment.source_order',
    10: 'comment.answer_type', 11: 'comment.default_value', 12: 'comment.default_value_2',
    13: 'comment.default_unit_type', 14: 'comment.default_location',
    15: 'comment.estimate_min', 16: 'comment.estimate_max', 17: 'comment.locked',
    18: 'comment.simple_format', 19: 'comment.disable_photos', 20: 'comment.uses',
    41: 'comment.source_last_modified',
}
for n in range(10):
    MODELLED[21 + 2 * n] = f'comment.photos[{n}].url'
    MODELLED[22 + 2 * n] = f'comment.photos[{n}].caption'
NOT_MODELLED_REASON = {}   # every known column has a field; anything here needs a justification

for path in sys.argv[1:]:
    rows = load(path); hdr = rows[0]; data = rows[1:]
    NC = 42; N = len(data); total = N * NC
    nonempty = Counter()
    for r in data:
        for i in range(NC):
            v = r.get(i)
            if v is not None and v != '': nonempty[i] += 1
    tot_ne = sum(nonempty.values())
    mod_ne = sum(n for i, n in nonempty.items() if i in MODELLED)

    def distinct(i): return len({r.get(i) for r in data if r.get(i)})
    def classify(i):
        n = nonempty[i]
        if n == 0: return 'empty'
        if n == N and distinct(i) == 1: return 'constant'
        if i in MODELLED: return 'consumed'
        return 'not_modelled'

    print("=" * 80); print(path.split('/')[-1]); print("=" * 80)
    print(f"  grid                 : {N} rows x {NC} cols = {total:,} cells")
    print(f"  non-empty cells      : {tot_ne:,}  ({100*tot_ne/total:.1f}% of grid)")
    print(f"  consumed by schema   : {mod_ne:,}  ({100*mod_ne/tot_ne:.2f}% of non-empty)")
    print(f"  not consumed         : {tot_ne-mod_ne:,}")

    ledger = Counter(classify(i) for i in range(NC))
    print(f"\n  column ledger        : {dict(ledger)}")
    print(f"\n  non-empty columns NOT consumed by the schema:")
    varying_lost = 0
    for i in range(NC):
        cls = classify(i)
        if cls in ('constant', 'not_modelled') and i not in MODELLED:
            d = distinct(i)
            note = NOT_MODELLED_REASON.get(i, '** UNJUSTIFIED **')
            if cls == 'not_modelled': varying_lost += nonempty[i]
            print(f"    {cn(i):>3} {hdr.get(i,'')[:36]:36s} {nonempty[i]:4d} cells  {cls:12s} distinct={d:<3d} {note}")
    print(f"\n  >>> non-empty cells not consumed that actually VARY : {varying_lost}")
    print(f"  >>> constant system-default cells not consumed      : {sum(nonempty[i] for i in range(NC) if classify(i)=='constant' and i not in MODELLED)}")
    print(f"  >>> empty cells (nothing to lose)                   : {total-tot_ne:,}")

    tags = Counter(); attrs = Counter()
    for r in data:
        b = r.get(3) or ''
        for m_ in re.finditer(r'<\s*(/?)([a-zA-Z][\w-]*)([^>]*)>', b):
            if not m_.group(1):
                tags[m_.group(2).lower()] += 1
                for a in re.finditer(r'(?:^|\s)([a-zA-Z-]+)\s*=', m_.group(3)): attrs[a.group(1).lower()] += 1
    print(f"\n  markup inventory in Comment Text:")
    print(f"    tags      : {dict(tags)}")
    print(f"    attributes: {dict(attrs)}")
    print()
