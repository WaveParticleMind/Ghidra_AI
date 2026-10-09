"""Build a source-only ZIP for GitHub upload; excludes secrets and test output."""
from pathlib import Path
import re
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent
DIRECTORIES = ('ghidra_scripts', 'tests', 'examples', '.github')
FILES = ('ghidra_ai.py', 'package_source.py', 'README.md', 'LICENSE',
         'requirements.txt', '.gitignore', '.env.example')


def main():
    selected = [ROOT / name for name in FILES]
    for name in DIRECTORIES:
        selected.extend(path for path in (ROOT / name).rglob('*') if path.is_file()
                        and '__pycache__' not in path.parts and path.suffix != '.pyc')
    for path in selected:
        if re.search(rb'sk-(?:or-v1-|proj-)[A-Za-z0-9_-]{20,}', path.read_bytes()):
            raise RuntimeError('Possible API credential detected; refusing archive: ' + path.name)
    destination = ROOT / 'dist/ghidra-ai-source.zip'
    destination.parent.mkdir(exist_ok=True)
    with ZipFile(destination, 'w', ZIP_DEFLATED) as archive:
        for path in selected:
            archive.write(path, 'ghidra-ai/' + path.relative_to(ROOT).as_posix())
    print('Source archive: ' + str(destination))


if __name__ == '__main__':
    main()
