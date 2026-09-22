"""Check parser-relevant invariants across any number of Spectora exports."""
import zipfile, html, re, sys
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict, defaultdict
M='http://schemas.openxmlformats.org/spreadsheetml/2006/main'; NS={'m':M}
def ci(c):
    n=0
    for ch in c: n=n*26+(ord(ch)-64)
    return n-1
def load(p):
    z=zipfile.ZipFile(p); root=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    out=[]
    for r in root.findall('.//m:row',NS):
        d={}
        for c in r.findall('m:c',NS):
            v=c.find('m:v',NS); d[ci(''.join(x for x in c.get('r') if x.isalpha()))]=(v.text or '') if v is not None else ''
        out.append(d)
    return out
def g(r,i): return r.get(i,'') or ''
def d1(v): return html.unescape(v)
for p in sys.argv[1:]:
    rows=load(p); hdr=rows[0]; data=rows[1:]
    print("="*78); print(p.split('/')[-1]); print("="*78)
    secs=list(OrderedDict.fromkeys(d1(g(r,0)) for r in data))
    items=list(OrderedDict.fromkeys((d1(g(r,0)),d1(g(r,1))) for r in data))
    names={i for _,i in items}
    print(f"  cols={len(hdr)} rows={len(data)} sections={len(secs)} items={len(items)} distinct item names={len(names)}")
    print(f"  types={dict(Counter(g(r,4) for r in data))}")
    print(f"  answer types={dict(Counter(g(r,10) for r in data))}")
    ok=lambda b:"PASS" if b else "**FAIL**"
    cat_iff_defect=all((g(r,5)!='')==(g(r,4)=='defect') for r in data)
    choice_iff_cb =all((g(r,6)!='')==(g(r,10)=='checkbox') for r in data)
    hdr42=len(hdr)==42
    nonblank=all(g(r,0).strip() and g(r,1).strip() for r in data)
    type_known=set(g(r,4) for r in data)<={'info','limit','defect'}
    ans_known=set(g(r,10) for r in data)<={'boolean','checkbox','date','number','range','text'}
    print(f"  [{ok(hdr42)}] 42 columns")
    print(f"  [{ok(nonblank)}] every row has non-blank Section and Item")
    print(f"  [{ok(type_known)}] Comment Type within documented enum")
    print(f"  [{ok(ans_known)}] Answer Type within documented enum")
    print(f"  [{ok(cat_iff_defect)}] Category populated IFF type==defect")
    print(f"  [{ok(choice_iff_cb)}] Choices populated IFF answer type==checkbox")
    # name reuse across sections
    reuse=defaultdict(set)
    for s,i in items: reuse[i].add(s)
    multi={i:sorted(ss) for i,ss in reuse.items() if len(ss)>1}
    print(f"  item names reused across sections: {len(multi)} -> {list(multi)[:5]}")
    # comment-name collisions within an item
    byitem=defaultdict(Counter)
    for r in data: byitem[(d1(g(r,0)),d1(g(r,1)))][d1(g(r,2))]+=1
    coll={k:{n:c for n,c in v.items() if c>1} for k,v in byitem.items() if any(c>1 for c in v.values())}
    print(f"  comment-name collisions within an item: {len(coll)} -> {list(coll.items())[:3]}")
    # order density
    TO={'info':0,'limit':1,'defect':2}
    grp=defaultdict(list)
    for r in data: grp[(d1(g(r,0)),d1(g(r,1)),g(r,4))].append(int(g(r,9)) if g(r,9).isdigit() else -1)
    dense=sum(1 for v in grp.values() if sorted(v)==list(range(len(v))))
    print(f"  Order dense 0..n-1 per (section,item,type): {dense}/{len(grp)}")
    # encoding depth per column
    raw=zipfile.ZipFile(p).read('xl/worksheets/sheet1.xml').decode('utf-8')
    for col in ['A','B','C','D','G']:
        dbl=len(re.findall(r'<c r="%s\d+"[^>]*><v>[^<]*&amp;amp;'%col,raw))
        sgl=len(re.findall(r'<c r="%s\d+"[^>]*><v>[^<]*&amp;(?!amp;)'%col,raw))
        print(f"    encoding {col}: double={dbl:4d} single={sgl:4d}")
    print()
