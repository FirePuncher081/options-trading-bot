"""Execute every maintained notebook offline; preserve tracked notebook files."""
from pathlib import Path
import nbformat
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]
output=ROOT/'artifacts/executed-notebooks'
output.mkdir(parents=True,exist_ok=True)
for path in sorted((ROOT/'notebooks').glob('*.ipynb')):
    notebook=nbformat.read(path,as_version=4)
    nbformat.validate(notebook)
    NotebookClient(notebook,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(ROOT/'notebooks')}}).execute()
    nbformat.write(notebook,output/path.name)
    print(f'PASS {path.name}',flush=True)
