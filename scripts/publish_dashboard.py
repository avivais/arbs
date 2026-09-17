#!/usr/bin/env python3
"""Publish only explicit read-only dashboard/report artifacts."""
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from arbs.publication import publish_public, render_directory

if __name__ == '__main__':
    render_directory(ROOT)
    print(json.dumps({'published': publish_public(ROOT)}))
