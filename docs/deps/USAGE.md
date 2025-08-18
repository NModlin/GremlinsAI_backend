# Dependency Management: Fast, Reliable Installs

This project uses pip constraints to speed up resolver decisions and avoid long backtracking on Windows + Python 3.11.

Quick start:

- Base install (use constraints):
  pip install -r requirements.txt -c constraints/win-py311.txt

- Extras (multi-agent features):
  pip install -r requirements.extras.txt -c constraints/win-py311.txt

Why constraints?
- They pin a set of tested, compatible versions for your platform, dramatically reducing pip's backtracking time.
- We keep requirements.txt ranges for portability, but recommend constraints for reproducible setups.

Notes:
- If you're on Linux/macOS or a different Python version, you may omit the constraints file or create a platform-specific one.
- If a dependency changes, update constraints and re-validate with a fresh install.

