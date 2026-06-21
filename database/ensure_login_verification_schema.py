"""
Ensure admin login 6-digit verification schema.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.login_verification_service import ensure_login_verification_schema


def main():
    print(json.dumps(ensure_login_verification_schema(), indent=2, default=str))


if __name__ == "__main__":
    main()