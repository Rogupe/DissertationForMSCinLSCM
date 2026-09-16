"""Consolidate the coding records (coding/ftcodes/*.json) into the workbook: Fulltext_eligibility (retrieval + FT decision),
Coding (extraction fields for FT includes) and FT_quotes (verbatim evidence). Re-runnable.
usage: python3 consolidate_ft.py <workbook>
"""
# Repository copy (2026-09-16): paths resolved relative to slr/ (override with SLR_FTCODES / SLR_FULLTEXT); the saved full texts are not distributed, so quote verification reports n/a unless SLR_FULLTEXT points to them.

import openpyxl, json, os, re, sys, unicodedata, datetime
_HERE = os.path.dirname(os.path.abspath(__file__))
FTCODES = os.environ.get('SLR_FTCODES', os.path.join(_HERE, '..', 'coding', 'ftcodes'))
FULLTEXT = os.environ.get('SLR_FULLTEXT', os.path.join(_HERE, '..', 'fulltext'))  # not in the repository; quotes verify as n/a without it
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
path = sys.argv[1]
D = datetime.date.today().isoformat()
wb = openpyxl.load_workbook(path)
ft = wb['Fulltext_eligibility']; cd = wb['Coding']
REASON = {'No AI/ML component': 'No AI/ML component', 'No digital twin / digital model': 'No digital twin / digital model',
          'No supply chain / logistics scope': 'No supply chain / logistics scope',
          'Not peer-reviewed / low-quality venue': 'Not peer-reviewed / low-quality venue', 'Other (note reason)': 'Other (note reason)'}
recs = {}
for f in sorted(os.listdir(FTCODES)):
    if f.endswith('.json'):
        d = json.load(open(os.path.join(FTCODES, f), encoding='utf-8')); recs[d['id']] = d

def norm(s):
    # tolerant matcher: ignore whitespace, punctuation and ligatures (PDF layout artefacts)
    s = unicodedata.normalize('NFKC', s).casefold().replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    return re.sub(r'[^a-z0-9]', '', s)

# ---- quote verification against saved full texts ----
qstats = {}
for rid, d in recs.items():
    p = os.path.join(FULLTEXT, f'{rid}.txt')
    if not os.path.exists(p) or d['status'] == 'NOT_RETRIEVED':
        qstats[rid] = None; continue
    hay = norm(open(p, encoding='utf-8', errors='replace').read())
    ok = bad = 0
    for q in d.get('quotes') or []:
        t = q['text']
        parts = [x.strip() for x in re.split(r'\[\.\.\.\]|\.\.\.|\[…\]|…', t) if x.strip()]
        found = all(norm(x) in hay for x in parts) if parts else False
        if not found:
            # tolerate hyphenation at line breaks in PDF text
            hay2 = hay.replace('- ', '').replace('-\n', '')
            found = all(norm(x).replace('-', '') in hay2.replace('-', '') for x in parts)
        ok += found; bad += (not found)
    qstats[rid] = (ok, bad)

# ---- Fulltext_eligibility ----
hdr = [ft.cell(1, c).value for c in range(1, ft.max_column + 1)]
col = {h: i + 1 for i, h in enumerate(hdr)}
if 'PDF file name' in col:
    ft.cell(1, col['PDF file name']).value = 'Source read (URL / local file)'
    col['Source read (URL / local file)'] = col.pop('PDF file name')
rowof = {ft.cell(r, 1).value: r for r in range(2, ft.max_row + 1) if ft.cell(r, 1).value and str(ft.cell(r, 1).value).startswith('R')}
n_written = 0
for rid, d in recs.items():
    r = rowof.get(rid)
    if not r:
        continue
    st = d['status']
    ft.cell(r, col['Retrieved (Y/N)']).value = 'Y' if st in ('FT_INCLUDE', 'FT_EXCLUDE') else 'N'
    ft.cell(r, col['Source read (URL / local file)']).value = (d.get('url_read') or '')[:250]
    ft.cell(r, col['FT decision']).value = 'Include' if st == 'FT_INCLUDE' else ('Exclude' if st == 'FT_EXCLUDE' else None)
    ft.cell(r, col['FT exclusion reason']).value = REASON.get(d.get('exclusion_reason') or '', d.get('exclusion_reason')) if st == 'FT_EXCLUDE' else None
    note = (d.get('ft_note') or '')
    qs = qstats.get(rid)
    if qs:
        note += f' [citas verificadas: {qs[0]} ok, {qs[1]} no encontradas]'
    if st == 'NOT_RETRIEVED':
        note = 'NO RECUPERADO. ' + note
    ft.cell(r, col['FT note (quote page/section)']).value = note
    ft.cell(r, col['FT date']).value = D
    for c in range(1, ft.max_column + 1):
        ft.cell(r, c).alignment = Alignment(vertical='top', wrap_text=True)
    n_written += 1

# ---- Coding ----
chdr = [cd.cell(1, c).value for c in range(1, cd.max_column + 1)]
ccol = {h: i + 1 for i, h in enumerate(chdr)}
crow = {cd.cell(r, 1).value: r for r in range(2, cd.max_row + 1) if cd.cell(r, 1).value}
n_coded = 0
for rid, d in recs.items():
    r = crow.get(rid)
    if not r:
        continue
    if d['status'] != 'FT_INCLUDE':
        cd.cell(r, ccol['Notes']).value = ('FT: EXCLUDED - ' + (d.get('exclusion_reason') or '') + '. ' + (d.get('ft_note') or '')) if d['status'] == 'FT_EXCLUDE' else ('FT: NOT RETRIEVED. ' + (d.get('ft_note') or ''))
        continue
    m = {'Evidence type': 'evidence_type', 'Sector': 'sector', 'SCOR: Plan': 'scor_plan', 'SCOR: Source': 'scor_source',
         'SCOR: Make': 'scor_make', 'SCOR: Deliver': 'scor_deliver', 'SCOR: Return': 'scor_return', 'End-to-end': 'end_to_end',
         'AI technique': 'ai_technique', 'AI role in twin': 'ai_role', 'Integration extent (1-5)': 'integration_extent',
         'HITL role': 'hitl_role', 'HITL function': 'hitl_function', 'Conditions under which HITL changes': 'hitl_conditions',
         'Key finding (own words)': 'key_finding', 'Page/section for citation': 'citation_locator', 'Use in typology (Y/N)': 'use_in_typology'}
    for h, k in m.items():
        cd.cell(r, ccol[h]).value = d.get(k)
    prev = cd.cell(r, ccol['Notes']).value or ''
    prev = re.sub(r'^(FT: .*?)(?=$)', '', prev).strip()
    cd.cell(r, ccol['Notes']).value = ('FT ' + D + ': ' + (d.get('ft_note') or '') + ((' | ' + d['ai_detail']) if d.get('ai_detail') else '') + (' | ' + prev if prev else '')).strip()
    for c in range(1, cd.max_column + 1):
        cd.cell(r, c).alignment = Alignment(vertical='top', wrap_text=c in (2, 4, 7, 19, 20, 21, 23))
    n_coded += 1

# ---- FT_quotes sheet ----
name = 'FT_quotes'
if name in wb.sheetnames:
    del wb[name]
qs_ws = wb.create_sheet(name)
qs_ws.append(['ID', 'Status', 'Quote (verbatim)', 'Section / page', 'Verified in saved full text'])
for rid in sorted(recs):
    d = recs[rid]
    p = os.path.join(FULLTEXT, f'{rid}.txt')
    hay = norm(open(p, encoding='utf-8', errors='replace').read()) if os.path.exists(p) else ''
    for q in d.get('quotes') or []:
        parts = [x.strip() for x in re.split(r'\[\.\.\.\]|\.\.\.|\[…\]|…', q['text']) if x.strip()]
        v = 'Y' if hay and parts and all(norm(x) in hay for x in parts) else ('n/a' if d['status'] == 'NOT_RETRIEVED' else 'check')
        qs_ws.append([rid, d['status'], q['text'], q.get('section'), v])
for c in range(1, 6):
    cell = qs_ws.cell(1, c); cell.font = Font(bold=True, color='FFFFFF'); cell.fill = PatternFill('solid', fgColor='1E2761')
for i, w in enumerate([8, 14, 90, 40, 12], start=1):
    qs_ws.column_dimensions[get_column_letter(i)].width = w
for row in qs_ws.iter_rows(min_row=2):
    for cell in row:
        cell.alignment = Alignment(vertical='top', wrap_text=True)
qs_ws.freeze_panes = 'A2'; qs_ws.auto_filter.ref = qs_ws.dimensions
wb.save(path)
st = {}
for d in recs.values():
    st[d['status']] = st.get(d['status'], 0) + 1
bad = {k: v for k, v in qstats.items() if v and v[1]}
print('records', len(recs), st, '| FT rows written', n_written, '| coded', n_coded, '| quote problems', bad)
