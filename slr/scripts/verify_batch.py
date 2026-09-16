# Repository copy (2026-09-16): needs the working workbook WITH the Abstract column (the repository copy has it removed) and the batchN_proposals.py module of the batch being verified.
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from screening_cols import index_map
import openpyxl, json, re, sys, unicodedata, importlib, collections, os
mod = importlib.import_module(sys.argv[1]); P = mod.P
kw = json.load(open('keywords_by_id.json')) if os.path.exists('keywords_by_id.json') else {}  # keyword file derived from the raw exports (not in the repository)
wb = openpyxl.load_workbook('SLR_PRISMA_workbook_screening.xlsx')
ws = wb['Screening']
h = index_map(ws)
rec = {r[h['ID']]: r for r in ws.iter_rows(min_row=2, values_only=True)}
def norm(s):
    s = s.replace('’',"'").replace('‘',"'").replace('“','"').replace('”','"')
    s = s.replace('–','-').replace('—','-').replace(' ',' ')
    s = unicodedata.normalize('NFKC', s)
    return re.sub(r'\s+',' ', s).casefold()
codes_ok = {'I','E1','E2','E3','E4','E5','E6','DUDA'}
problems = 0
for rid,(dec,code,just,make) in P.items():
    r = rec[rid]
    hay = norm(' || '.join([r[h['Title']] or '', (r[h['Abstract']] or '') if 'Abstract' in h else ''] + [v for k,v in kw.get(rid, {}).items() if isinstance(v,str)]))
    assert code in codes_ok, (rid, code)
    assert (dec,code) in {('Include','I'),('DUDA','DUDA')} or (dec=='Exclude' and code.startswith('E')), (rid,dec,code)
    quotes = re.findall(r'"([^"]+)"', just)
    if not quotes:
        print('NO QUOTE', rid); problems += 1
    for q in quotes:
        if norm(q) not in hay:
            print('QUOTE NOT FOUND', rid, '->', q); problems += 1
    if '\n' in just: print('MULTILINE', rid); problems += 1
    if make and 'Make' not in just: print('MAKE NOTE MISMATCH', rid); problems += 1
    if code == 'E4' and 'snowballing' not in just: print('E4 WITHOUT SNOWBALLING NOTE', rid); problems += 1
print('records:', len(P), 'problems:', problems)
print(collections.Counter(c for _,c,_,_ in P.values()))
print('Make notes:', [k for k,v in P.items() if v[3]])
