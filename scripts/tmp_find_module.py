import os, re, sys
mod = sys.argv[1]
pattern = re.compile(rf"^(?:\s*from\s+{re.escape(mod)}\b|\s*import\s+{re.escape(mod)}\b)")
for base in ['app','cli','scripts','sdk','tests','examples']:
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
                for i, l in enumerate(lines, 1):
                    if pattern.search(l):
                        print(f"{p}:{i}: {l.strip()}")

