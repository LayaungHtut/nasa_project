"""Read an AOI window from a GCOV granule on ASF without downloading it.

A full granule is ~6 GB; a 14 km AOI touches only a few of its 512 x 512
HDF5 chunks per layer. An authenticated request to the granule URL is
redirected (via Earthdata Login) to a short-lived signed URL. h5py then
reads that file through fsspec's HTTP range requests, so only the metadata
and the requested chunks cross the network.

The signed URL is used immediately and never logged or stored -- it grants
temporary access with the user's Earthdata Login identity.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import IO

import aiohttp
import fsspec

BLOCK_SIZE = 4 * 1024 * 1024


def signed_url(session, url: str) -> str:
    """Follow ASF's Earthdata Login redirects and return the final signed URL
    without downloading the body."""
    with session.get(url, stream=True, timeout=120) as response:
        if response.status_code != 200:
            raise RuntimeError(f"ASF returned HTTP {response.status_code} for {url.rsplit('/', 1)[-1]}")
        return response.url


@contextmanager
def open_remote_granule(session, url: str, block_size: int = BLOCK_SIZE) -> Iterator[IO[bytes]]:
    """Yield a seekable file object for an ASF granule, for h5py.File(...).
    A smaller block_size wastes less on scattered HDF5 metadata reads over slow links."""
    # A stalled range request otherwise waits forever; fail it so the caller can retry.
    fs = fsspec.filesystem("http", client_kwargs={"timeout": aiohttp.ClientTimeout(sock_connect=30, sock_read=60)})
    with fs.open(signed_url(session, url), "rb", block_size=block_size, cache_type="blockcache") as fobj:
        yield fobj
