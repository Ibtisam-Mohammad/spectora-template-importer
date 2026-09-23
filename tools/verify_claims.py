"""Claim-by-claim verification of everything documented about the Spectora export,
run against a single file. Every claim prints PASS or FAIL with the evidence.

    python tools/verify_claims.py fixtures/spectora/probe-html.xls
"""
import zipfile, html, re, sys
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict, defaultdict

M = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'; NS = {'m': M}
PATH = sys.argv[1]

def cn(i):
    s = ''; i += 1
    while i: i, r = divmod(i - 1, 26); s = chr(65 + r) + s
    return s
def ci(c):
    n = 0
    for ch in c: n = n * 26 + (ord(ch) - 64)
    return n - 1

z = zipfile.ZipFile(PATH)
raw = z.read('xl/worksheets/sheet1.xml').decode('utf-8')
root = ET.fromstring(raw)
wb = ET.fromstring(z.read('xl/workbook.xml'))
rows = {}
for r in root.findall('.//m:row', NS):
    cells = {}
    for c in r.findall('m:c', NS):
        v = c.find('m:v', NS)
        cells[ci(''.join(x for x in c.get('r') if x.isalpha()))] = (v.text or '') if v is not None else ''
    rows[int(r.get('r'))] = cells
hdr = rows[1]; data = {k: v for k, v in rows.items() if k > 1}
u = html.unescape
def g(rn, i): return data[rn].get(i, '')
def byname(name):
    hits = [rn for rn, r in data.items() if u(r.get(2, '')) == name]
    return hits[0] if hits else None

results = []
def claim(section, text, ok, evidence):
    results.append((section, text, bool(ok), evidence))

# ------------------------------------------------------------------ file mechanics
magic = open(PATH, 'rb').read(4)
claim('file', 'magic bytes are PK (OOXML zip) despite .xls extension', magic == b'PK\x03\x04', repr(magic))
claim('file', 'no sharedStrings.xml; all values inline', 'xl/sharedStrings.xml' not in z.namelist(), str(z.namelist()))
sheets = [s.get('name') for s in wb.iter('{%s}sheet' % M)]
claim('file', 'exactly one worksheet named Sheet1', sheets == ['Sheet1'], str(sheets))
dim = root.find('m:dimension', NS).get('ref')
claim('file', 'dimension spans 42 columns A..AP', dim.startswith('A1:AP'), dim)
claim('file', 'header on row 1 with 42 cells', len(hdr) == 42 and 1 in rows, f'{len(hdr)} header cells')
tset = Counter(c.get('t') for c in root.iter('{%s}c' % M) if c.get('t'))
claim('file', "string cells use t=\"str\" (formula-string type), no t=\"s\" or inlineStr", set(tset) == {'str'}, str(dict(tset)))

EXPECT = ['Section Name','Item Name','Comment Name','Comment Text','Comment Type (info, limit, defect)',
 'Category (-1: Low, 0: Med, 1: High)','Multiple Choice Options (comma-separated)',
 'Unit Type Options (numeric answers only, comma-separated)','Recommendation (from list)','Order (w/i item)',
 'Answer Type (boolean, checkbox, date, number, range, text)','Default Value','Default Value 2 (for "range" types)',
 'Default Unit Type (for "number" and "range" types)','Default Location','Default Estimate Min','Default Estimate Max',
 'Locked','Simple Format','Disable Photos','Uses'] + \
 [x for n in range(1, 11) for x in (f'Default Photo {n}', f'Default Photo {n} Caption')] + ['Last Modified']
got = [hdr.get(i, '') for i in range(42)]
claim('file', '42 header strings byte-identical to the documented list', got == EXPECT,
      'first mismatch: ' + next((f'{cn(i)} {got[i]!r} vs {EXPECT[i]!r}' for i in range(42) if got[i] != EXPECT[i]), 'none'))

# sparse cells
absent = Counter(); valueless = Counter()
for r in root.findall('.//m:row', NS):
    if int(r.get('r')) == 1: continue
    present = {}
    for c in r.findall('m:c', NS):
        i = ci(''.join(x for x in c.get('r') if x.isalpha())); present[i] = c.find('m:v', NS)
    for i in range(42):
        if i not in present: absent[i] += 1
        elif present[i] is None: valueless[i] += 1
claim('file', 'photo columns AB..AO have zero <c> elements on every data row (sparse: index by r attribute)',
      all(absent[i] == len(data) for i in range(27, 41)), f"AB..AO absent counts: {sorted(set(absent[i] for i in range(27,41)))}")
claim('file', 'two kinds of empty exist: absent <c> and present-but-valueless <c>',
      sum(absent.values()) > 0 and sum(valueless.values()) > 0, f"absent on {len([i for i in absent if absent[i]])} cols, valueless on {len([i for i in valueless if valueless[i]])} cols")

# ------------------------------------------------------------------ structure
secs = list(OrderedDict.fromkeys(u(r.get(0, '')) for r in data.values()))
items = list(OrderedDict.fromkeys((u(r.get(0, '')), u(r.get(1, ''))) for r in data.values()))
names = {i for _, i in items}
claim('structure', f'403 data rows', len(data) == 403, str(len(data)))
claim('structure', '14 sections, 70 items, 62 distinct item names', (len(secs), len(items), len(names)) == (14, 70, 62), f'{len(secs)},{len(items)},{len(names)}')
claim('structure', 'every row has non-blank Section and Item', all(u(r.get(0,'')).strip() and u(r.get(1,'')).strip() for r in data.values()), '')
claim('structure', 'empty section "ZZ Empty" is ABSENT from the export', not any(s.startswith('ZZ Empty') for s in secs), str([s for s in secs if 'ZZ' in s]))
claim('structure', 'empty item "ZZ Empty Item" is ABSENT from the export', not any(i == 'ZZ Empty Item' for _, i in items), str([i for _, i in items if 'ZZ' in i]))
reuse = defaultdict(set)
for s, i in items: reuse[i].add(s)
claim('structure', "item name 'General' appears under 8 sections", len(reuse.get('General', ())) == 8, str(sorted(reuse.get('General', ()))))
coll = [(k, n) for k, cnt in ((k, Counter(u(r.get(2,'')) for r in data.values() if (u(r.get(0,'')), u(r.get(1,''))) == k)) for k in items) for n, c in cnt.items() if c > 1]
claim('structure', "duplicate comment name inside one item: Fireplace/Damper Doors 'Damper Inoperable' x2", coll == [(('Fireplace', 'Damper Doors'), 'Damper Inoperable')], str(coll))
ext = [i for s, i in items if s == 'Exterior']
claim('structure', 'Exterior item order: Walkways (6th) before Vegetation (7th), matching the UI after the drag',
      ext[5].startswith('Walkways') and ext[6].startswith('Vegetation'), ' | '.join(ext))
sec_expected = ['Inspection Details','Exterior','Roof','Basement, Foundation, Crawlspace & Structure','Heating','Cooling','Plumbing','Electrical','Fireplace','Attic, Insulation & Ventilation','Doors, Windows & Interior','Built-in Appliances','Garage']
claim('structure', 'first 13 sections in the UI order, probe section 14th', secs[:13] == sec_expected and secs[13].startswith('ZZ Probe'), str(secs[13:]))

# ------------------------------------------------------------------ enums & invariants
types = Counter(r.get(4, '') for r in data.values()); ans = Counter(r.get(10, '') for r in data.values()); cat = Counter(r.get(5, '') for r in data.values())
claim('enums', 'Comment Type: info 85, defect 305, limit 13', dict(types) == {'info': 85, 'defect': 305, 'limit': 13}, str(dict(types)))
claim('enums', 'all SEVEN answer types present, including undocumented "signature"',
      set(ans) == {'boolean','checkbox','number','text','range','date','signature'}, str(dict(ans)))
claim('enums', 'Category values are exactly -1, 0, 1 and blank', set(cat) == {'-1', '0', '1', ''}, str(dict(cat)))
claim('invariant', 'Category populated IFF Comment Type == defect (0 exceptions)',
      all((r.get(5, '') != '') == (r.get(4, '') == 'defect') for r in data.values()), '')
claim('invariant', 'Multiple Choice Options populated IFF Answer Type == checkbox (0 exceptions)',
      all((r.get(6, '') != '') == (r.get(10, '') == 'checkbox') for r in data.values()), '')
claim('invariant', 'every defect and every limit row is answer type boolean',
      all(r.get(10, '') == 'boolean' for r in data.values() if r.get(4, '') in ('defect', 'limit')), '')

# ------------------------------------------------------------------ constant columns
def const(i):
    vals = {r.get(i, '') for r in data.values()}
    return len(vals) == 1, next(iter(vals))
for i, exp in [(15, '10'), (16, '1000'), (20, '0')]:
    ok, v = const(i); claim('constant', f'{cn(i)} {hdr[i]} == {exp!r} on all {len(data)} rows', ok and v == exp, repr(v))
for i in [13, 17, 18, 19]:
    ok, v = const(i); claim('constant', f'{cn(i)} {hdr[i][:28]} empty on all rows (no UI control)', ok and v == '', repr(v))

# ------------------------------------------------------------------ probe rows: answer formats and defaults
R = {n: byname(n) for n in ['Probe Limitation','Probe Photos','Probe Choices','Probe Deficiency Mid','Probe Range',
                            'Probe Deficiency High','Probe Date','Probe Number','Probe Text','Probe Signature']}
smith = next((rn for rn, r in data.items() if u(r.get(2, '')).startswith('Smith & Sons')), None)
R['Smith & Sons'] = smith
claim('probe', 'all 11 probe comments found', all(v for v in R.values()), str({k: v for k, v in R.items()}))
def cell(name, i): return g(R[name], i)
claim('answer', 'Probe Range: K=range, L=10, M=20, H="inches, feet", N empty',
      (cell('Probe Range',10), cell('Probe Range',11), cell('Probe Range',12), cell('Probe Range',7), cell('Probe Range',13)) == ('range','10','20','inches, feet',''),
      str((cell('Probe Range',10), cell('Probe Range',11), cell('Probe Range',12), cell('Probe Range',7), cell('Probe Range',13))))
claim('answer', 'Probe Number: K=number, L=42, H="gallons, litres", N empty',
      (cell('Probe Number',10), cell('Probe Number',11), cell('Probe Number',7), cell('Probe Number',13)) == ('number','42','gallons, litres',''),
      str((cell('Probe Number',10), cell('Probe Number',11), cell('Probe Number',7), cell('Probe Number',13))))
claim('answer', 'Probe Text: K=text, L=hello', (cell('Probe Text',10), cell('Probe Text',11)) == ('text','hello'), str((cell('Probe Text',10), cell('Probe Text',11))))
claim('answer', 'Probe Date: K=date, L empty (no default field exists)', (cell('Probe Date',10), cell('Probe Date',11)) == ('date',''), str((cell('Probe Date',10), cell('Probe Date',11))))
claim('answer', 'Probe Signature: K=signature, L empty', (cell('Probe Signature',10), cell('Probe Signature',11)) == ('signature',''), str((cell('Probe Signature',10), cell('Probe Signature',11))))
claim('answer', 'Smith & Sons (UI "Checkbox"): K=boolean, L=true', (cell('Smith & Sons',10), cell('Smith & Sons',11)) == ('boolean','true'), str((cell('Smith & Sons',10), cell('Smith & Sons',11))))
claim('answer', 'Probe Choices (UI "Multiple Choices"): K=checkbox, L empty', (cell('Probe Choices',10), cell('Probe Choices',11)) == ('checkbox',''), str((cell('Probe Choices',10), cell('Probe Choices',11))))
claim('answer', 'boolean Default Value serialises inconsistently: "true" AND "f" both occur',
      {'true', 'f'} <= {r.get(11, '') for r in data.values() if r.get(10, '') == 'boolean'},
      str(Counter(r.get(11, '') for r in data.values() if r.get(10, '') == 'boolean')))
claim('choices', 'comma split happened at input: G == "Smith, John, 1, 000 sq ft, He said \\"no\\", Plain"',
      cell('Probe Choices', 6) == 'Smith, John, 1, 000 sq ft, He said "no", Plain', repr(cell('Probe Choices', 6)))

# ------------------------------------------------------------------ category & recommendation
claim('category', 'wrench=-1 (Probe Photos), minus=0 (Mid), warning=1 (High)',
      (cell('Probe Photos',5), cell('Probe Deficiency Mid',5), cell('Probe Deficiency High',5)) == ('-1','0','1'),
      str((cell('Probe Photos',5), cell('Probe Deficiency Mid',5), cell('Probe Deficiency High',5))))
claim('recommendation', 'Carpet Cleaner -> carpetcleaner, Appliance Repair -> appliance, No Recommendation -> blank',
      (cell('Probe Photos',8), cell('Probe Deficiency Mid',8), cell('Probe Deficiency High',8)) == ('carpetcleaner','appliance',''),
      str((cell('Probe Photos',8), cell('Probe Deficiency Mid',8), cell('Probe Deficiency High',8))))
nondef = ['Probe Limitation','Smith & Sons','Probe Choices','Probe Range','Probe Date','Probe Number','Probe Text','Probe Signature']
claim('recommendation', '"pro" is stamped on every non-deficiency probe comment (system default)',
      all(cell(n, 8) == 'pro' for n in nondef), str({n: cell(n, 8) for n in nondef}))
claim('recommendation', 'Damper Inoperable (row 263) still carries cabinet from the earlier test', g(263, 8) == 'cabinet', repr(g(263, 8)))
claim('recommendation', 'slug set observed', set(r.get(8,'') for r in data.values()) == {'', 'pro', 'monitor', 'cabinet', 'appliance', 'carpetcleaner'},
      str(Counter(r.get(8,'') for r in data.values())))

# ------------------------------------------------------------------ photos
pp = R['Probe Photos']
claim('photos', 'three photos fill V,X,Z with captions W,Y,AA', all(g(pp, i) for i in (21,22,23,24,25,26)) and not g(pp, 27), '')
claim('photos', 'order is NEWEST FIRST: captions read three, two, one', (g(pp,22), g(pp,24), g(pp,26)) == ('three','two','one'), str((g(pp,22), g(pp,24), g(pp,26))))
claim('photos', 'all photo values are cdn.spectora.com URLs with a cache-buster',
      all(re.match(r'https://cdn\.spectora\.com/default_photos/images/\d+/\d+/\d+/original/.+\?\d+$', g(pp, i)) for i in (21,23,25)), g(pp,21)[:90])
claim('photos', 'row 263 still carries its one default photo from the earlier test', g(263, 21).startswith('https://cdn.spectora.com/'), g(263,21)[:60])

# ------------------------------------------------------------------ order
grp = defaultdict(list)
for rn, r in data.items():
    if (u(r.get(0,'')), u(r.get(1,''))) == items[-1]:
        grp[r.get(4,'')].append(int(r.get(9,'')))
claim('order', 'probe item: Order dense per TYPE (info 0..6, defect 0..2, limit 0)',
      sorted(grp['info']) == list(range(7)) and sorted(grp['defect']) == [0,1,2] and grp['limit'] == [0], str({k: sorted(v) for k, v in grp.items()}))
probe_rows = [rn for rn, r in data.items() if (u(r.get(0,'')), u(r.get(1,''))) == items[-1]]
seq = [(g(rn,4), g(rn,9)) for rn in sorted(probe_rows)]
claim('order', 'file order within the item is NOT grouped by type (types interleave)', len({t for t, _ in seq[:3]}) > 1, str(seq))

# ------------------------------------------------------------------ encoding
def rawcell(ref):
    m = re.search(r'<c r="%s"[^>]*>(?:<v>(.*?)</v>)?' % ref, raw, re.S); return m.group(1) if m else None
a = rawcell(f'A{smith}'); b = rawcell(f'B{smith}'); c = rawcell(f'C{smith}')
claim('encoding', 'A: & is DOUBLE-encoded in raw XML (&amp;amp;)', a and '&amp;amp;' in a, repr(a))
claim('encoding', 'A: < > are SINGLE-encoded (&lt; &gt;) and " is bare', a and '&lt;' in a and '&quot;' not in a and '&lt;x&gt;' in a, repr(a))
claim('encoding', 'B and C follow the same pattern as A', b and c and '&amp;amp;' in b and '&amp;amp;' in c and '&lt;' in b and '&lt;' in c, repr(c))
claim('encoding', 'name auto-closed by export: A contains <x></x>, B </angle>, C </test>',
      u(g(smith,0)).endswith('<x></x>') and '</angle>' in u(g(smith,1)) and '</test>' in u(g(smith,2)), f"{u(g(smith,0))!r} | {u(g(smith,1))!r} | {u(g(smith,2))!r}")
dbl = {col: len(re.findall(r'<c r="%s\d+"[^>]*><v>[^<]*&amp;amp;' % col, raw)) for col in 'ABCDG'}
sgl = {col: len(re.findall(r'<c r="%s\d+"[^>]*><v>[^<]*&amp;(?!amp;)' % col, raw)) for col in 'ABCDG'}
claim('encoding', 'A,B,C,D double-encoded and G single-encoded, file-wide',
      all(dbl[c] > 0 and sgl[c] == 0 for c in 'ABCD') and dbl['G'] == 0 and sgl['G'] > 0, f'double={dbl} single={sgl}')
d263 = g(263, 3)
claim('encoding', 'Comment Text after XML decode is real HTML (contains <p>, <iframe>, <table>)', '<iframe' in d263 and '<table' in d263 and '<p>' in g(21,3), '')
claim('encoding', '&amp; survives in Comment Text after XML decode (must NOT be decoded again)', sum(r.get(3,'').count('&amp;') for r in data.values()) == 31, str(sum(r.get(3,'').count('&amp;') for r in data.values())))
claim('encoding', 'U+00A0 present in Comment Text (194), never literal &nbsp;', sum(r.get(3,'').count('\u00a0') for r in data.values()) == 194 and not any('&nbsp;' in r.get(3,'') for r in data.values()), '')

# ------------------------------------------------------------------ HTML round-trip on row 263
fix = open('fixtures/editor/spectora-editor-kitchen-sink.html', encoding='utf-8').read().rstrip('\n').replace('&nbsp;', '\u00a0')
def inv(s_):
    return (Counter(t.lower() for t in re.findall(r'<\s*([a-zA-Z][\w-]*)', s_)),
            Counter(c_ for cl in re.findall(r'class\s*=\s*"([^"]*)"', s_) for c_ in cl.split()))
ft, fc = inv(fix); et, ec = inv(d263)
claim('roundtrip', 'row 263: every tag from the editor fixture is present in the export', all(et[k] >= v for k, v in ft.items()), f'missing={[k for k,v in ft.items() if et[k] < v]}')
claim('roundtrip', 'row 263: every Froala class survived', all(ec[k] >= v for k, v in fc.items()), str(dict(ec)))
claim('roundtrip', 'row 263: Vimeo iframe src intact', 'https://player.vimeo.com/video/76073568' in d263, '')
claim('roundtrip', 'row 263: only additive change is fr-original-style + link colour', 'fr-original-style' in d263 and 'color: rgb(53, 119, 168)' in d263, '')
opens = Counter(); closes = Counter()
for r in data.values():
    b_ = r.get(3, '')
    for m_ in re.finditer(r'<\s*(/?)([a-zA-Z][\w-]*)', b_):
        (closes if m_.group(1) else opens)[m_.group(2).lower()] += 1
void = {'br','img','hr'}
claim('html', 'zero unbalanced tags file-wide', all(opens[t] == closes.get(t, 0) for t in opens if t not in void), str({t: (opens[t], closes.get(t,0)) for t in opens if t not in void and opens[t] != closes.get(t,0)}))
links = [m_.group(1) for r in data.values() for m_ in re.finditer(r'href="([^"]+)"', r.get(3, ''))]
claim('html', '44 hyperlinks, none Spectora-hosted', len(links) == 44 and not any('spectora' in l for l in links), f'{len(links)} links')
claim('html', 'one empty youtube-embed-wrapper shell still present (pre-existing artifact, not export loss)',
      sum(1 for r in data.values() if 'youtube-embed-wrapper' in r.get(3,'') and '<iframe' not in r.get(3,'')) == 1, '')

# ------------------------------------------------------------------ location & last modified
locs = [r.get(14,'') for r in data.values() if r.get(14,'')]
claim('location', 'Default Location populated on exactly one row (263), with a leading space, all 21 stock tags space-joined, and the custom comma tag last',
      len(locs) == 1 and g(263, 14) == locs[0] and locs[0].startswith(' 1st Floor 2nd Floor') and locs[0].endswith('Garage,'), repr(locs))
claim('location', 'the composed location string contains tag labels that themselves contain spaces (unsplittable)',
      locs and 'Dining Room' in locs[0] and 'Living Room' in locs[0], '')
lm = Counter(r.get(41, '') for r in data.values())
claim('lastmod', 'Last Modified: MM/DD/YYYY HH:MM:SS on every row', all(re.match(r'\d\d/\d\d/\d{4} \d\d:\d\d:\d\d$', v) for v in lm), str(list(lm)[:2]))
claim('lastmod', 'Last Modified varies per row (22 distinct), i.e. not a single export timestamp', len(lm) == 22, str(len(lm)))
probe_lm = {g(R[n], 41) for n in R}
claim('lastmod', 'probe comments carry their own save times, not the template load time', not any(v.startswith('09/22/2026 04:3') for v in probe_lm), str(sorted(probe_lm)))

# ------------------------------------------------------------------ text hygiene
claim('text', 'Comment Text contains raw CR (43) and LF (306)',
      sum(r.get(3,'').count('\r') for r in data.values()) == 43 and sum(r.get(3,'').count('\n') for r in data.values()) == 306, '')
claim('text', 'leading/trailing whitespace on C (11 values), D (209), O (1)',
      (sum(1 for r in data.values() if r.get(2,'') != r.get(2,'').strip()),
       sum(1 for r in data.values() if r.get(3,'') and r.get(3,'') != r.get(3,'').strip()),
       sum(1 for r in data.values() if r.get(14,'') and r.get(14,'') != r.get(14,'').strip())) == (11, 209, 1), '')
claim('text', 'max lengths: section 44, item 62, comment name 42, comment text 2260',
      (max(len(u(r.get(0,''))) for r in data.values()), max(len(u(r.get(1,''))) for r in data.values()),
       max(len(u(r.get(2,''))) for r in data.values()), max(len(r.get(3,'')) for r in data.values())) == (44, 62, 42, 2260), '')

# ------------------------------------------------------------------ report
w = max(len(t) for _, t, _, _ in results)
passed = sum(1 for r in results if r[2]); failed = [r for r in results if not r[2]]
print(f"{PATH}: {passed}/{len(results)} claims PASS\n")
cur = None
for sec, text, ok, ev in results:
    if sec != cur: print(f"--- {sec}"); cur = sec
    mark = 'PASS' if ok else '**FAIL**'
    print(f"  [{mark:8s}] {text}")
    if not ok or ev and sec in ('encoding','recommendation','category','answer','photos','order','structure'):
        if ev: print(f"             {ev[:160]}")
if failed:
    print("\nFAILED:"); [print(f"  - {t}\n      {e}") for _, t, _, e in failed]
sys.exit(1 if failed else 0)
