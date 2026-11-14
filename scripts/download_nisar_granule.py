"""Download a single real NISAR GCOV granule (~5.96 GB) into data/raw/.

Deliberately NOT run automatically by any pipeline step -- multi-GB
downloads must be an explicit, individually-invoked action, per project
instructions ("Do not download the ~6 GB granules until this small
authentication test succeeds").

Usage:
    python scripts/download_nisar_granule.py <granule_id> <url> [--expected-bytes N]

Behavior:
  - Skips the download if the destination file already exists AND matches
    --expected-bytes (so re-running is safe and won't re-download).
  - Streams to a .part file and renames on success, so a failed/interrupted
    download never leaves a corrupt file at the final path.
  - Uses the authenticated ASFSession from services.processing.auth --
    fails loudly (no fabricated success) if .env / auth isn't set up.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.processing.auth import MissingCredentialsError, get_authenticated_session

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"


def download(granule_id: str, url: str, expected_bytes: int | None) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    dest = RAW_DIR / f"{granule_id}.h5"
    part = dest.with_suffix(".h5.part")

    if dest.exists() and (expected_bytes is None or dest.stat().st_size == expected_bytes):
        print(f"Already downloaded: {dest} ({dest.stat().st_size} bytes) -- skipping.")
        return dest

    try:
        session = get_authenticated_session()
    except MissingCredentialsError as e:
        print(f"AUTH ERROR: {e}", file=sys.stderr)
        raise SystemExit(1)

    print(f"Downloading {granule_id} ...")
    with session.get(url, stream=True, timeout=120) as response:
        if response.status_code != 200:
            print(
                f"DOWNLOAD FAILED: HTTP {response.status_code} from {response.url}\n"
                f"Body snippet: {response.text[:300]}",
                file=sys.stderr,
            )
            raise SystemExit(1)

        total = int(response.headers.get("Content-Length", 0))
        written = 0
        with open(part, "wb") as f:
            for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                f.write(chunk)
                written += len(chunk)
                if total:
                    pct = 100 * written / total
                    print(f"\r  {written / 1e9:.2f} / {total / 1e9:.2f} GB ({pct:.1f}%)", end="", flush=True)
        print()

    if expected_bytes is not None and written != expected_bytes:
        print(f"WARNING: downloaded {written} bytes, expected {expected_bytes}. Not renaming to final path -- inspect {part} manually.", file=sys.stderr)
        raise SystemExit(1)

    part.rename(dest)
    print(f"Done: {dest} ({written} bytes)")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("granule_id")
    parser.add_argument("url")
    parser.add_argument("--expected-bytes", type=int, default=None)
    args = parser.parse_args()
    download(args.granule_id, args.url, args.expected_bytes)


if __name__ == "__main__":
    main()
