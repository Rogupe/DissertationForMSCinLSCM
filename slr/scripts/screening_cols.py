"""Header-based column lookup for the Screening sheet.

The repository copy of the workbook has no Abstract column, so the scripts locate columns by header
name instead of fixed positions. Usage:
    C = cols(ws)            # C('Decision') -> 1-based column index
    h = index_map(ws)       # h['Decision'] -> 0-based index into values_only rows
"""
NAMES = ('ID', 'Source', 'Authors', 'Year', 'Title', 'Abstract', 'Venue', 'Doc type', 'DOI', 'Stage (TA/FT)', 'Decision',
         'Exclusion reason', 'Pre-flag (auto)', 'Notes', 'Código final', 'Lote', 'Decisión propuesta', 'Código propuesto',
         'Justificación propuesta (cita)', 'Nota Make')

def index_map(ws):
    return {ws.cell(1, c).value: c - 1 for c in range(1, ws.max_column + 1) if ws.cell(1, c).value}

def cols(ws):
    h = {name: i + 1 for name, i in index_map(ws).items()}
    def C(name):
        if name not in h:
            raise KeyError(f'Screening sheet has no column {name!r}; headers: {list(h)}')
        return h[name]
    C.has = lambda name: name in h
    return C
