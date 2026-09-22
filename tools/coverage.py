"""Cell-level import coverage: what a given model consumes, and what it leaves behind."""
import zipfile, html, re, sys, json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
M='http://schemas.openxmlformats.org/spreadsheetml/2006/main'; NS={'m':M}
def cn(i):
    s=''; i+=1
    while i: i,r=divmod(i-1,26); s=chr(65+r)+s
    return s
def ci(c):
    n=0
    for ch in c: n=n*26+(ord(ch)-64)
    return n-1
def load(p):
    root=ET.fromstring(zipfile.ZipFile(p).read('xl/worksheets/sheet1.xml'))
    out=[]
    for r in root.findall('.//m:row',NS):
        d={}
        for c in r.findall('m:c',NS):
            v=c.find('m:v',NS)
            d[ci(''.join(x for x in c.get('r') if x.isalpha()))]=(v.text or '') if v is not None else ''
        out.append(d)
    return out

# columns the proposed schema stores
MODELLED = {0:'section.name',1:'item.name',2:'comment.name',3:'comment.body_html',
            4:'comment.comment_type',5:'comment.severity',6:'comment.choices',
            7:'comment.unit_options',8:'comment.recommendation',9:'comment.source_order',
            10:'comment.answer_type',11:'comment.default_value',12:'comment.default_value_2'}

for path in sys.argv[1:]:
    rows=load(path); hdr=rows[0]; data=rows[1:]
    NC=42; N=len(data)
    total=N*NC
    nonempty=Counter(); present=Counter()
    for r in data:
        for i in range(NC):
            v=r.get(i)
            if v is not None and v!='': nonempty[i]+=1
    tot_ne=sum(nonempty.values())
    mod_ne=sum(n for i,n in nonempty.items() if i in MODELLED)
    unmod=[(i,n) for i,n in sorted(nonempty.items()) if i not in MODELLED and n]
    # a column is "constant" if it has exactly one distinct non-empty value across all rows
    def distinct(i): return len({r.get(i) for r in data if r.get(i)})
    print("="*80); print(path.split('/')[-1]); print("="*80)
    print(f"  grid                : {N} rows x {NC} cols = {total:,} cells")
    print(f"  non-empty cells     : {tot_ne:,}  ({100*tot_ne/total:.1f}% of grid)")
    print(f"  modelled (non-empty): {mod_ne:,}  ({100*mod_ne/tot_ne:.2f}% of non-empty)")
    print(f"  NOT modelled        : {tot_ne-mod_ne:,}")
    print(f"\n  unmodelled columns carrying data:")
    varying=0
    for i,n in unmod:
        d=distinct(i)
        tag="CONSTANT (system default)" if d==1 else f"** VARIES ({d} distinct) **"
        if d>1: varying+=n
        print(f"    {cn(i):>3} {hdr.get(i,'')[:40]:40s} {n:4d} cells  {tag}")
    print(f"\n  >>> non-empty cells lost that actually VARY: {varying}")
    print(f"  >>> empty cells (nothing to lose)            : {total-tot_ne:,}")

    # markup inventory
    tags=Counter(); attrs=Counter()
    for r in data:
        b=r.get(3) or ''
        for m_ in re.finditer(r'<\s*(/?)([a-zA-Z][\w-]*)([^>]*)>', b):
            if not m_.group(1):
                tags[m_.group(2).lower()]+=1
                for a in re.finditer(r'(?:^|\s)([a-zA-Z-]+)\s*=', m_.group(3)): attrs[a.group(1).lower()]+=1
    print(f"\n  markup inventory in Comment Text:")
    print(f"    tags      : {dict(tags)}")
    print(f"    attributes: {dict(attrs)}")
    print()
