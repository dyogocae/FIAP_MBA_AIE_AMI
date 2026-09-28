"""Sincroniza pins dos notebooks com requirements.txt; --check não modifica arquivos."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sync(check=False):
    pins = " ".join(line.strip() for line in (ROOT / "requirements.txt").read_text().splitlines()
                    if line.strip() and not line.startswith("#"))
    mismatches = []
    count = 0
    for notebook in sorted(ROOT.glob("Aula_*/notebooks/*.ipynb")):
        data = json.loads(notebook.read_text(encoding="utf8"))
        changed = False
        for cell in data["cells"]:
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"])
            lines = source.splitlines(keepends=True)
            for i, line in enumerate(lines):
                if line.lstrip().startswith(("%pip install", "%pip -q install")):
                    expected = "%pip install -q " + pins + ("\n" if line.endswith("\n") else "")
                    count += 1
                    if line != expected:
                        lines[i] = expected
                        changed = True
            cell["source"] = lines
        if changed:
            mismatches.append(str(notebook.relative_to(ROOT)))
            if not check:
                notebook.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    duplicates = list(ROOT.glob("Aula_*/requirements.txt"))
    if duplicates:
        raise SystemExit("Remova requirements duplicados por aula: " + str(duplicates))
    print(f"{count} células de instalação verificadas; {len(mismatches)} divergências" + (" (corrigidas)." if not check else "."))
    if check and mismatches:
        raise SystemExit("\n".join(mismatches))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    sync(parser.parse_args().check)
