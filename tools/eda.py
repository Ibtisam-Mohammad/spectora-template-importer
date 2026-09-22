"""Exploratory data analysis of a Spectora HTML-text template export."""
import zipfile, html, re, sys, unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict, defaultdict

M = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
NS = {'m': M}

def colname(i):
    s = ''; i += 1
    while i:
        i, r = divmod(i - 1, 26); s = chr(65 + r) + s
    return s

def colindex(c):
    n = 0
    for ch in c: n = n * 26 + (ord(ch) - 64)
    return n - 1

def load(path):
    z = zipfile.ZipFile(path)
    raw = z.read('xl/worksheets/sheet1.xml').decode('utf-8')
    root = ET.fromstring(raw)
    rows = []
    for r in root.findall('.//m:row', NS):
        cells = {}
        types = {}
        for c in r.findall('m:c', NS):
            i = colindex(''.join(ch for ch in c.get('r') if ch.isalpha()))
            v = c.find('m:v', NS)
            isv = c.find('m:is/m:t', NS)
            if isv is not None: cells[i] = isv.text or ''
            elif v is not None: cells[i] = v.text or ''
            else: cells[i] = None          # present but empty
            types[i] = c.get('t')
        rows.append((cells, types, int(r.get('r'))))
    return raw, rows

path = sys.argv[1]
raw, rows = load(path)
hdr = rows[0][0]
data = rows[1:]
N = len(data)
NCOL = 42
H = [hdr.get(i, '') for i in range(NCOL)]
print(f"FILE: {path}\nrows(data)={N}  cols={NCOL}\n")

def sec(t): print("\n" + "="*78 + f"\n{t}\n" + "="*78)

# ---------------------------------------------------------------- cell mechanics
sec("1. CELL MECHANICS")
missing = Counter(); empty = Counter(); ws_only = Counter(); typed = Counter()
for cells, types, rn in data:
    for i in range(NCOL):
        if i not in cells: missing[i] += 1
        elif cells[i] is None: empty[i] += 1
        elif cells[i].strip() == '' and cells[i] != '': ws_only[i] += 1
        if types.get(i): typed[types[i]] += 1
print("cell 't' attribute values seen:", dict(typed) or "none (all default -> numeric/string via <v>)")
print("columns where the <c> element is ABSENT on some rows:",
      {colname(i): n for i, n in sorted(missing.items())} or "none")
print("columns with present-but-valueless <c>:",
      {colname(i): n for i, n in sorted(empty.items())} or "none")
print("whitespace-only values:", {colname(i): n for i, n in ws_only.items()} or "none")

lead_trail = Counter()
for cells, _, _ in data:
    for i in range(NCOL):
        v = cells.get(i)
        if isinstance(v, str) and v and v != v.strip(): lead_trail[colname(i)] += 1
print("values with leading/trailing whitespace:", dict(lead_trail) or "none")

# ---------------------------------------------------------------- unicode
sec("2. CHARACTER / UNICODE AUDIT")
nonascii = defaultdict(Counter)
for cells, _, rn in data:
    for i in range(NCOL):
        v = cells.get(i)
        if isinstance(v, str):
            for ch in v:
                if ord(ch) > 126: nonascii[colname(i)][ch] += 1
for c, cnt in nonascii.items():
    pretty = ', '.join(f"{repr(ch)}({unicodedata.name(ch,'?')[:28]})x{n}" for ch, n in cnt.most_common(8))
    print(f"  {c}: {pretty}")
if not nonascii: print("  pure ASCII across all cells")

ctrl = Counter()
for cells, _, _ in data:
    for i in range(NCOL):
        v = cells.get(i)
        if isinstance(v, str):
            for ch in v:
                if ord(ch) < 32 and ch not in '\t': ctrl[(colname(i), repr(ch))] += 1
print("control characters:", dict(ctrl) or "none")

def dec1(v): return html.unescape(v) if isinstance(v, str) else ''
def get(cells, i): 
    v = cells.get(i)
    return v if isinstance(v, str) else ''

# ---------------------------------------------------------------- hierarchy
sec("3. HIERARCHY & IDENTITY")
secs = OrderedDict(); items = OrderedDict(); rows_by_item = defaultdict(list)
for cells, _, rn in data:
    s = dec1(get(cells, 0)); it = dec1(get(cells, 1)); cn = dec1(get(cells, 2))
    secs.setdefault(s, 0); secs[s] += 1
    items.setdefault((s, it), 0); items[(s, it)] += 1
    rows_by_item[(s, it)].append((rn, cn, get(cells, 4), get(cells, 9)))
print(f"sections={len(secs)}  items(sec,item)={len(items)}  distinct item names={len({i for _,i in items})}")

reuse = defaultdict(list)
for s, i in items: reuse[i].append(s)
multi = {i: ss for i, ss in reuse.items() if len(ss) > 1}
print(f"\nitem names reused across sections: {len(multi)}")
for i, ss in sorted(multi.items(), key=lambda kv: -len(kv[1])):
    print(f"  {i!r} -> {len(ss)} sections: {ss}")

print("\nrows with a blank Section or Item:",
      sum(1 for c,_,_ in data if not get(c,0).strip() or not get(c,1).strip()))

print("\ncomment-name collisions WITHIN the same item (identity hazard):")
coll = 0
for k, lst in rows_by_item.items():
    names = Counter(n for _, n, _, _ in lst)
    dup = {n: c for n, c in names.items() if c > 1}
    if dup:
        coll += 1
        print(f"  {k[0]} / {k[1]}: {dup}")
print(f"  items affected: {coll}/{len(items)}")

print("\ncomment-name reuse ACROSS items (expected, not a hazard):")
allnames = Counter(dec1(get(c,2)) for c,_,_ in data)
print("  ", {n: c for n, c in allnames.most_common(6)})

# lengths
sec("4. LENGTHS")
for i, label in [(0,'Section Name'),(1,'Item Name'),(2,'Comment Name'),(3,'Comment Text')]:
    vals = [dec1(get(c,i)) if i != 3 else get(c,3) for c,_,_ in data]
    vals = [v for v in vals if v]
    if not vals: continue
    ln = sorted(len(v) for v in vals)
    longest = max(vals, key=len)
    print(f"  {label:14s} n={len(ln):3d} min={ln[0]:4d} median={ln[len(ln)//2]:5d} max={ln[-1]:6d}")
    print(f"                 longest: {longest[:90]!r}")

# ---------------------------------------------------------------- HTML
sec("5. COMMENT TEXT / HTML DEEP DIVE")
bodies = [(rn, get(c,3)) for c,_,rn in data if get(c,3)]
tags = Counter(); attrs = Counter(); links = []
plain = 0; unclosed = []
for rn, b in bodies:
    if '<' not in b: plain += 1
    for m in re.finditer(r'<\s*(/?)([a-zA-Z][\w-]*)([^>]*)>', b):
        close, name, rest = m.group(1), m.group(2).lower(), m.group(3)
        tags[('/' if close else '') + name] += 1
        if not close:
            for a in re.finditer(r'([a-zA-Z-]+)\s*=', rest): attrs[a.group(1).lower()] += 1
    for m in re.finditer(r'href\s*=\s*["\']([^"\']+)["\']', b): links.append((rn, m.group(1)))
    opens = Counter(m.group(1).lower() for m in re.finditer(r'<\s*([a-zA-Z][\w-]*)[^>]*>', b) if not m.group(0).startswith('</'))
    closes = Counter(m.group(1).lower() for m in re.finditer(r'</\s*([a-zA-Z][\w-]*)\s*>', b))
    void = {'br','img','hr','input','meta','link'}
    for t_ in opens:
        if t_ not in void and opens[t_] != closes.get(t_, 0):
            unclosed.append((rn, t_, opens[t_], closes.get(t_,0)))
print(f"populated bodies: {len(bodies)}   with NO markup: {plain}   with markup: {len(bodies)-plain}")
print("tags:", dict(tags.most_common()))
print("attributes on open tags:", dict(attrs) or "none")
print(f"\nunbalanced tags: {len(unclosed)}")
for u in unclosed[:10]: print("   row", u)

print(f"\nhyperlinks: {len(links)}")
hosts = Counter(re.sub(r'^(https?://)?([^/]+).*$', r'\2', u) for _, u in links)
print("  hosts:", dict(hosts))
for rn, u in links[:5]: print(f"   row {rn}: {u[:95]}")

print("\nentities still present AFTER xml decode (must survive as HTML):")
ent = Counter()
for _, b in bodies:
    for m in re.finditer(r'&[a-zA-Z#][a-zA-Z0-9]*;', b): ent[m.group(0)] += 1
print("  ", dict(ent))

# ---------------------------------------------------------------- choices
sec("6. MULTIPLE CHOICE OPTIONS - COMMA SPLIT HAZARD")
ch = [(rn, get(c,6)) for c,_,rn in data if get(c,6)]
print(f"rows with choices: {len(ch)}")
counts = Counter()
suspicious = []
for rn, v in ch:
    parts = [p.strip() for p in v.split(',')]
    counts[len(parts)] += 1
    for p in parts:
        if len(p) <= 2 or re.match(r'^(F|C|Inc|Jr|Ltd)$', p): suspicious.append((rn, p, v[:70]))
print("  choices-per-row distribution:", dict(sorted(counts.items())))
print(f"  parts that look like fragments of a split value: {len(suspicious)}")
for s in suspicious[:12]: print("    row %s part=%r  in %r" % s)

# ---------------------------------------------------------------- enums & order
sec("7. ENUMS, ORDER ANOMALIES, RARE ROWS")
DOC_TYPES={'info','limit','defect'}; DOC_ANS={'boolean','checkbox','date','number','range','text'}; DOC_CAT={'-1','0','1'}
t_=Counter(get(c,4) for c,_,_ in data); a_=Counter(get(c,10) for c,_,_ in data); cat=Counter(get(c,5) for c,_,_ in data)
print("Comment Type  :", dict(t_), "| undocumented:", set(t_)-DOC_TYPES-{''})
print("Answer Type   :", dict(a_), "| undocumented:", set(a_)-DOC_ANS-{''}, "| documented-but-absent:", DOC_ANS-set(a_))
print("Category      :", dict(cat), "| undocumented:", set(cat)-DOC_CAT-{''})

print("\ncross-tab Comment Type x Category:")
ct=defaultdict(Counter)
for c,_,_ in data: ct[get(c,4)][get(c,5) or '(blank)']+=1
for k,v in ct.items(): print(f"  {k:7s} {dict(v)}")
print("\ncross-tab Comment Type x Answer Type:")
ca=defaultdict(Counter)
for c,_,_ in data: ca[get(c,4)][get(c,10)]+=1
for k,v in ca.items(): print(f"  {k:7s} {dict(v)}")

print("\nchoices present but Answer Type != checkbox:",
      sum(1 for c,_,_ in data if get(c,6) and get(c,10)!='checkbox'))
print("Answer Type == checkbox but NO choices:",
      sum(1 for c,_,_ in data if get(c,10)=='checkbox' and not get(c,6)))

TYPE_ORDER={'info':0,'limit':1,'defect':2}
bad=[]
for k,lst in rows_by_item.items():
    by=defaultdict(list)
    for rn,cn,ty,od in lst: by[ty].append((int(od) if od.isdigit() else -1, cn, rn))
    for ty,v in by.items():
        o=sorted(x[0] for x in v)
        if o!=list(range(len(o))): bad.append((k,ty,o,[x[1] for x in sorted(v)]))
print(f"\ntype-groups whose Order is not a clean 0..n-1: {len(bad)}")
for k,ty,o,names in bad: print(f"  {k[0]} / {k[1]}  [{ty}] orders={o} names={names}")

print("\nrare rows:")
for c,_,rn in data:
    if get(c,10) in ('number','text') or get(c,11) or get(c,8):
        print(f"  row {rn}: {dec1(get(c,0))} / {dec1(get(c,1))} / {dec1(get(c,2))} "
              f"ans={get(c,10)} defaultValue={get(c,11)!r} units={get(c,7)!r} rec={get(c,8)!r}")

sec("8. DEGENERATE / CONSTANT COLUMNS")
for i in range(NCOL):
    vals={get(c,i) for c,_,_ in data}
    if len(vals)==1:
        v=next(iter(vals))
        print(f"  {colname(i):>3} {H[i][:48]:48s} = {v!r}" + ("   <-- constant NON-empty" if v else ""))
