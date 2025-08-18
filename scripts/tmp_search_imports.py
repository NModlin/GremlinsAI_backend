import os, re, sys

roots = sys.argv[1:] or ['app','cli','scripts','sdk','tests','examples']
pattern = re.compile(r'\b(import\s+aiohttp|from\s+aiohttp\s+import)')

for base in roots:
    if not os.path.isdir(base):
        continue
    for dirpath, _, files in os.walk(base):
        for f in files:
            if f.endswith('.py'):
                p = os.path.join(dirpath, f)
                try:
                    with open(p, encoding='utf-8') as fh:
                        lines = fh.readlines()
                except Exception:
                    continue
                for i, line in enumerate(lines, 1):
                    if pattern.search(line):
                        print(f"{p}:{i}: {line.strip()}")

