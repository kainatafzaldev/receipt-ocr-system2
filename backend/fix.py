import pathlib, re
path=pathlib.Path(r'c:\Users\Kainat\Documents\OCR_Project\backend\main.py')
text=path.read_text()
start = text.find('# ==================== DYNAMIC DISCOUNT DETECTION FUNCTION ====================')
end = text.find('# ==================== ODOO DATA PREPARATION ====================')
print('start,end', start, end)
if start == -1 or end == -1:
    print('Markers not found', start, end)
else:
    before=text[:start]
    after=text[end:]
    # just for test
    print('before excerpt', before[-100:])
    print('after excerpt', after[:100])
    path.write_text(before + '# REPLACED\n' + after)
    print('wrote file')
