"""Render the current report without retraining or reusing legacy scores."""
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from options_lab.plotting import plot_report

if __name__ == '__main__':
    report=json.loads((ROOT/'artifacts/research/report.json').read_text())
    plot_report(report,ROOT/'artifacts/figures')
    print('Rendered current report figures under artifacts/figures.')
