"""Earthdata Login (EDL) authentication for ASF downloads.

Credentials come from a project-local `.env` (never committed -- see
.gitignore), loaded via python-dotenv, never from a `_netrc`/`.netrc`
file. This module never prints, logs, or returns the actual credential
values -- only booleans/exceptions about whether auth succeeded.
"""

from __future__ import annotations

import os
from pathlib import Path

import asf_search as asf
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = REPO_ROOT / ".env"


class MissingCredentialsError(RuntimeError):
    pass


def load_credentials() -> tuple[str, str]:
    """Load EARTHDATA_USERNAME/PASSWORD from .env. Raises
    MissingCredentialsError (message never includes the values) if the
    file or either variable is absent."""
    if not ENV_PATH.exists():
        raise MissingCredentialsError(f".env not found at {ENV_PATH}. Copy .env.example to .env and fill in your Earthdata Login credentials.")

    load_dotenv(ENV_PATH)
    username = os.environ.get("EARTHDATA_USERNAME")
    password = os.environ.get("EARTHDATA_PASSWORD")

    missing = [name for name, val in (("EARTHDATA_USERNAME", username), ("EARTHDATA_PASSWORD", password)) if not val]
    if missing:
        raise MissingCredentialsError(f".env is missing required variable(s): {', '.join(missing)} (values are never logged).")

    return username, password  # type: ignore[return-value]


def get_authenticated_session() -> asf.ASFSession:
    """Returns an ASFSession authenticated against Earthdata Login.
    Raises MissingCredentialsError if .env isn't set up, or whatever
    asf_search itself raises if the credentials are present but wrong
    (that exception's message comes from asf_search/EDL, not from us --
    we never construct or alter it)."""
    username, password = load_credentials()
    session = asf.ASFSession()
    session.auth_with_creds(username, password)
    return session
