"""Step 1 of the real-data pipeline: verify Earthdata Login auth works
BEFORE attempting any multi-GB download.

Checks, in order:
  1. .env exists
  2. EARTHDATA_USERNAME and EARTHDATA_PASSWORD are both present (values
     are never printed, logged, or returned)
  3. an authenticated ASFSession can be constructed
  4. a small authenticated GET against the real, already-identified
     Track 40 / Frame 10 baseline granule's QA_SUMMARY.csv sidecar
     succeeds (chosen because it's a few hundred bytes, not the 5.96 GB
     main product)

Exits 0 and prints a small JSON summary (no secrets) on success.
Exits 1 and prints the exact, non-secret error on failure -- never
fabricates a success.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, so `services.*` imports work when run directly

from services.processing.auth import MissingCredentialsError, get_authenticated_session

QA_SUMMARY_URL = (
    "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_PROVISIONAL_V1/"
    "NISAR_L2_PR_GCOV_029_040_A_010_4005_DHDH_A_20260827T230239_20260827T230313_P05023_N_F_J_001/"
    "NISAR_L2_PR_GCOV_029_040_A_010_4005_DHDH_A_20260827T230239_20260827T230313_P05023_N_F_J_001_QA_SUMMARY.csv"
)


def main() -> int:
    try:
        session = get_authenticated_session()
    except MissingCredentialsError as e:
        print(json.dumps({"ok": False, "stage": "credentials", "error": str(e)}, indent=2))
        return 1
    except Exception as e:
        print(json.dumps({"ok": False, "stage": "session_auth", "error": f"{type(e).__name__}: {e}"}, indent=2))
        return 1

    try:
        response = session.get(QA_SUMMARY_URL, allow_redirects=True, timeout=30)
    except Exception as e:
        print(json.dumps({"ok": False, "stage": "request", "error": f"{type(e).__name__}: {e}"}, indent=2))
        return 1

    if response.status_code != 200:
        print(
            json.dumps(
                {
                    "ok": False,
                    "stage": "http_response",
                    "status_code": response.status_code,
                    "final_url_host": response.url.split("/")[2] if "://" in response.url else response.url,
                    "body_snippet": response.text[:200],
                },
                indent=2,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "status_code": response.status_code,
                "bytes_received": len(response.content),
                "content_type": response.headers.get("Content-Type"),
                "message": "Authenticated request to the real Track 40/Frame 10 baseline granule's QA sidecar succeeded.",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
