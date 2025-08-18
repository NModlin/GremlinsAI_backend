import ast
import os
import sys
from typing import Set, Dict, List

ROOT = os.getcwd()
SEARCH_BASES = ['app','cli','scripts','sdk','tests','examples']

def gather_py_files(bases: List[str]) -> List[str]:
    files = []
    for base in bases:
        base_path = os.path.join(ROOT, base)
        if not os.path.isdir(base_path):
            continue
        for dirpath, _, filenames in os.walk(base_path):
            for f in filenames:
                if f.endswith('.py'):
                    files.append(os.path.join(dirpath, f))
    return files

STDLIB_APPROX = set('''
abc argparse array ast asyncio base64 binascii bisect builtins calendar cmath collections colorsys compileall concurrent configparser contextlib copy copyreg csv ctypes dataclasses datetime decimal difflib dis json logging enum errno faulthandler fcntl fnmatch fractions functools gc getpass getopt glob grp hashlib heapq html http importlib inspect io ipaddress itertools keyword lib2to3 linecache locale logging mailbox math mimetypes mmap multiprocessing numbers operator os pathlib pickle pkgutil platform plistlib pprint pty pydoc queue random re reprlib resource sched selectors signal site socket sqlite3 ssl statistics string struct subprocess sys sysconfig tarfile tempfile textwrap threading time timeit tokenize traceback types typing unicodedata unittest urllib uuid warnings wave weakref webbrowser xml xmlrpc zipfile zoneinfo
'''.split())


def extract_top_level_imports(path: str) -> Set[str]:
    src = None
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            src = fh.read()
        tree = ast.parse(src, filename=path)
    except Exception:
        return set()
    mods: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                top = n.name.split('.')[0]
                mods.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import
            if node.module:
                top = node.module.split('.')[0]
                mods.add(top)
    return mods

if __name__ == '__main__':
    py_files = gather_py_files(SEARCH_BASES)
    all_mods: Set[str] = set()
    per_file: Dict[str, List[str]] = {}
    for p in py_files:
        mods = extract_top_level_imports(p)
        if mods:
            per_file[p] = sorted(mods)
            all_mods.update(mods)

    third_party = sorted(m for m in all_mods if m not in STDLIB_APPROX)
    print(f"Scanned {len(py_files)} files. Unique non-stdlib imports: {len(third_party)}")
    for m in third_party:
        print(m)

