import os, re
pattern = re.compile(r"\b(from\s+crewai\b|import\s+crewai\b|from\s+crewai_tools\b|import\s+crewai_tools\b)")
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

