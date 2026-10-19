"""Compatibility entry point; append snapshots via the shared collector."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from options_lab.collect import collect

if __name__ == '__main__':
    for path in collect(['AAPL', 'MSFT', 'TSLA', 'GOOGL', 'AMD']):
        print(path)
