#!/usr/bin/env python
from __future__ import annotations

import os
from contextlib import suppress
from pathlib import Path
from tempfile import TemporaryDirectory

import boto3
import requests
from types_boto3_s3 import S3Client

from hls_vi_historical import Downloader, download_files, granule_sources


def http_download(src: tuple[str, str], dst: Path) -> None:
    """Download an object from and LPDAAC bucket to a local file, via HTTPS.

    For simplicity, assumes that an relevant entry exists in `~/.netrc` containing
    Earthdata Login credentials, of the following form:

        machine urs.earthdata.nasa.gov login USERNAME password PASSWORD

    where `USERNAME` and `PASSWORD` are valid credentials for Earthdata Login.
    """
    if dst.exists():
        return

    bucket, key = src
    url = f"https://data.lpdaac.earthdatacloud.nasa.gov/{bucket}/{key}"
    print(f"Downloading {url} to {dst}")

    with requests.Session() as session:
        r = session.get(url, stream=True)
        r.raise_for_status()

        with open(dst, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)


def make_downloader(s3: S3Client) -> Downloader:
    """Create a downloader to download an object from an LPDAAC bucket to its
    local MinIO-equivalent bucket.

    Return a downloader that can be passed to `main.download_files` that will
    seemlessly use HTTPS to download a file from an LPDAAC bucket to a local
    file, then "upload" the local file to the corresponding local MinIO bucket.
    """

    def transfer(src: tuple[str, str], dst: Path) -> None:
        bucket, key = src
        http_download(src, dst)

        with open(dst, "rb") as body:
            print(f"Uploading {dst} to local MinIO S3 server: s3://{bucket}/{key}")
            s3.put_object(Bucket=bucket, Key=key, Body=body)

    return transfer


def ensure_buckets(s3: S3Client, *buckets: str) -> None:
    """Ensure the specified buckets exist locally in MinIO."""
    for bucket in buckets:
        with suppress(
            s3.exceptions.BucketAlreadyExists,
            s3.exceptions.BucketAlreadyOwnedByYou,
        ):
            s3.create_bucket(Bucket=bucket)


def object_exists(s3: S3Client, obj: tuple[str, str]) -> bool:
    """Determine whether or not an object exists in a local MinIO bucket."""
    bucket, key = obj

    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except s3.exceptions.ClientError:
        return False


def transfer_granule_files(s3: S3Client, granule_id: str) -> None:
    """Transfer HLS files for a granule from LPDAAC buckets to local MinIO buckets.

    To avoid unnecessary egress costs, only files missing from the local MinIO
    buckets are transferred.
    """
    sources = granule_sources(
        granule_id,
        public_bucket="lp-prod-public",
        protected_bucket="lp-prod-protected",
    )

    with TemporaryDirectory() as tmpdir:
        missing = [source for source in sources if not object_exists(s3, source)]
        download_files(make_downloader(s3), missing, Path(tmpdir))


def main(granule_id: str) -> None:
    """Populate local MinIO buckets with HLS files for the specified granule.

    Enable local development testing by downloading (via HTTPS) only the HLS
    granule files for the specified granule from the real LPDAAC buckets and
    putting them into our local MinIO buckets (of the same names) that mock the
    LPDAAC buckets.
    """
    s3 = boto3.client(
        "s3",
        endpoint_url="http://localhost:9000",
        region_name="us-west-2",
        aws_access_key_id=os.environ.get("MINIO_ROOT_USER", "minioadmin"),
        aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin"),
        aws_session_token=None,
    )

    ensure_buckets(s3, "lp-prod-public", "lp-prod-protected", "hls-global-v2-forward")
    transfer_granule_files(s3, granule_id)


if __name__ == "__main__":
    import argparse
    import sys

    # We need only an HLS granule ID as the sole positional CLI argument.

    parser = argparse.ArgumentParser()
    parser.add_argument("GRANULE_ID")
    ns = parser.parse_args(sys.argv[1:])
    granule_id: str = ns.GRANULE_ID

    main(granule_id)
