"""Rebuild the two retention sheets from the Screening sheet (confirmed rows only)."""
import re
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from screening_cols import index_map
from copy import copy
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

VAL = {'alto': 0, 'medio': 1, 'bajo': 2}

def _value(text, key):
    m = re.search(key + r'\s*:\s*(alto|medio|bajo)', text or '', re.I)
    return m.group(1).lower() if m else ''

def _sheet(wb, name, headers, rows, widths):
    if name in wb.sheetnames:
        del wb[name]
    ws = wb.create_sheet(name)
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(1, c)
        cell.font = Font(bold=True, color='FFFFFF'); cell.fill = PatternFill('solid', fgColor='1E2761')
        cell.alignment = Alignment(vertical='top', wrap_text=True)
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical='top', wrap_text=True)
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions
    return ws

def rebuild(wb):
    ws = wb['Screening']
    h = index_map(ws)
    e4, c8 = [], []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[h['Decision']]:
            continue
        rid, year, title, venue, doi, notes, code = r[h['ID']], r[h['Year']], r[h['Title']], r[h['Venue']], r[h['DOI']], r[h['Notes']] or '', r[h['Código final']]
        if code == 'E4':
            e4.append((VAL.get(_value(notes, 'snowballing'), 3), rid, year, title, venue, doi, _value(notes, 'snowballing'), notes))
        elif code == 'E3' and 'Antecedente C8' in notes:
            c8.append((VAL.get(_value(notes, 'Antecedente C8'), 3), rid, year, title, venue, doi, _value(notes, 'Antecedente C8'), notes))
    e4.sort(); c8.sort()
    hdr = ['ID', 'Year', 'Title', 'Venue', 'DOI', 'Value', 'Screening note']
    _sheet(wb, 'Snowballing_E4', hdr, [x[1:] for x in e4], [8, 6, 60, 30, 28, 8, 90])
    _sheet(wb, 'Antecedentes_C8', hdr, [x[1:] for x in c8], [8, 6, 60, 30, 28, 8, 90])
    inc = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[h['Decision']] == 'Include':
            inc.append((r[h['ID']], r[h['Year']], r[h['Title']], r[h['Venue']], r[h['DOI']], r[h['Doc type']], r[h['Lote']], 'Make' if r[h['Nota Make']] == 'Make' else '', r[h['Notes']] or ''))
    _sheet(wb, 'Includes_fulltext', ['ID', 'Year', 'Title', 'Venue', 'DOI', 'Doc type', 'Batch', 'Make', 'Screening note'], inc,
           [8, 6, 60, 30, 28, 14, 6, 6, 90])
    return len(e4), len(c8)
