import pathlib
path=pathlib.Path(r'c:\Users\Kainat\Documents\OCR_Project\backend\main.py')
lines=path.read_text().splitlines()
out=[]
skip=False
for line in lines:
    if skip:
        # if we are skipping until end of block
        if line.strip().startswith('def fallback_parse_receipt') or line.strip().startswith('# ==================== ITEM RECONSTRUCTION'):
            skip=False
            out.append(line)
        else:
            # continue skipping
            continue
    else:
        if line.strip().startswith('def fallback_parse_receipt'):
            # check upcoming lines to see if faulty pattern exists
            idx = lines.index(line)
            snippet = '\n'.join(lines[idx:idx+10])
            if 'newString on line 1 might be truncated' in snippet or '\\n,' in snippet:
                # skip this faulty block entirely
                skip=True
                continue
            else:
                out.append(line)
        else:
            out.append(line)

# write back
path.write_text("\n".join(out))
print('cleaned fallback definitions. lines count', len(out))
