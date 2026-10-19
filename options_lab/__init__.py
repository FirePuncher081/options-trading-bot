"""Contract-aware options research. No order execution or broker connections."""
__version__ = '0.2.0'


def code_fingerprint():
    """Hash maintained pipeline sources to reject stale report exports."""
    from hashlib import sha256
    from pathlib import Path
    digest = sha256()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()
