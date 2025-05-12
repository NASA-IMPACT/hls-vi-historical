#!/usr/bin/env python
from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import boto3

if TYPE_CHECKING:
    from types_boto3_s3 import S3Client
    from types_boto3_s3.literals import ObjectCannedACLType

from hls_vi.generate_indices import generate_vi_granule, GranuleId, L30Band, S30Band
from hls_vi.generate_metadata import generate_metadata
from hls_vi.generate_stac_items import create_item

# A downloader expects a (bucket, key) tuple and a destination file Path.
# The destination directory is expected to exist.  In production, we use an
# S3 downloader to avoid incurring egress costs, but for local development, we
# use an HTTPS downloader.
type Downloader = Callable[[tuple[str, str], Path], None]


def granule_sources(granule_id: str) -> tuple[tuple[str, str], ...]:
    """Return LPDAAC bucket-key 2-tuples of HLS files for a granule that are
    necessary to create corresponding HLS VI files.

    Since L30 and S30 use different bands, returned tuples differ slightly
    between L30 and S30 granules.  Further, to avoid unnecessary downloads, only
    HLS files necessary for producing a corresponding VI granule are returned,
    since not all of them are required to create VI outputs.

    Parameters
    ----------
    granule_id:
        ID of the granule to generate bucket-key pairs for of HLS files required
        to create corresponding HLS VI files.

    Returns
    -------
    Tuple of 2-tuples, where each 2-tuple is of the form (bucket, key), indicating
    the bucket and key of an HLS file required as an input for producing the
    corresponding HLS VI granule files.

    Examples
    --------
    Sources of an L30 granule:

    >>> granule_sources("HLS.L30.T58UFF.2025105T234951.v2.0")
    (('lp-prod-public', 'HLSL30.020/HLS.L30.T58UFF.2025105T234951.v2.0/HLS.L30.T58UFF.2025105T234951.v2.0.jpg'),
     ('lp-prod-protected', 'HLSL30.020/HLS.L30.T58UFF.2025105T234951.v2.0/HLS.L30.T58UFF.2025105T234951.v2.0.B02.tif'),
     ('lp-prod-protected', 'HLSL30.020/HLS.L30.T58UFF.2025105T234951.v2.0/HLS.L30.T58UFF.2025105T234951.v2.0.B03.tif'),
     ('lp-prod-protected', 'HLSL30.020/HLS.L30.T58UFF.2025105T234951.v2.0/HLS.L30.T58UFF.2025105T234951.v2.0.B04.tif'),
     ('lp-prod-protected', 'HLSL30.020/HLS.L30.T58UFF.2025105T234951.v2.0/HLS.L30.T58UFF.2025105T234951.v2.0.B05.tif'),
     ('lp-prod-protected', 'HLSL30.020/HLS.L30.T58UFF.2025105T234951.v2.0/HLS.L30.T58UFF.2025105T234951.v2.0.B06.tif'),
     ('lp-prod-protected', 'HLSL30.020/HLS.L30.T58UFF.2025105T234951.v2.0/HLS.L30.T58UFF.2025105T234951.v2.0.B07.tif'),
     ('lp-prod-protected', 'HLSL30.020/HLS.L30.T58UFF.2025105T234951.v2.0/HLS.L30.T58UFF.2025105T234951.v2.0.Fmask.tif'),
     ('lp-prod-protected', 'HLSL30.020/HLS.L30.T58UFF.2025105T234951.v2.0/HLS.L30.T58UFF.2025105T234951.v2.0.cmr.xml'))

    Sources of an S30 granule:

    >>> granule_sources("HLS.S30.T59VNH.2025105T234641.v2.0")
    (('lp-prod-public', 'HLSS30.020/HLS.S30.T59VNH.2025105T234641.v2.0/HLS.S30.T59VNH.2025105T234641.v2.0.jpg'),
     ('lp-prod-protected', 'HLSS30.020/HLS.S30.T59VNH.2025105T234641.v2.0/HLS.S30.T59VNH.2025105T234641.v2.0.B02.tif'),
     ('lp-prod-protected', 'HLSS30.020/HLS.S30.T59VNH.2025105T234641.v2.0/HLS.S30.T59VNH.2025105T234641.v2.0.B03.tif'),
     ('lp-prod-protected', 'HLSS30.020/HLS.S30.T59VNH.2025105T234641.v2.0/HLS.S30.T59VNH.2025105T234641.v2.0.B04.tif'),
     ('lp-prod-protected', 'HLSS30.020/HLS.S30.T59VNH.2025105T234641.v2.0/HLS.S30.T59VNH.2025105T234641.v2.0.B8A.tif'),
     ('lp-prod-protected', 'HLSS30.020/HLS.S30.T59VNH.2025105T234641.v2.0/HLS.S30.T59VNH.2025105T234641.v2.0.B11.tif'),
     ('lp-prod-protected', 'HLSS30.020/HLS.S30.T59VNH.2025105T234641.v2.0/HLS.S30.T59VNH.2025105T234641.v2.0.B12.tif'),
     ('lp-prod-protected', 'HLSS30.020/HLS.S30.T59VNH.2025105T234641.v2.0/HLS.S30.T59VNH.2025105T234641.v2.0.Fmask.tif'),
     ('lp-prod-protected', 'HLSS30.020/HLS.S30.T59VNH.2025105T234641.v2.0/HLS.S30.T59VNH.2025105T234641.v2.0.cmr.xml'))
    """
    is_l30 = granule_id.startswith("HLS.L30")
    collection = f"HLS{'L' if is_l30 else 'S'}30.020"
    bands = L30Band if is_l30 else S30Band
    suffixes = (*(f".{band.name}.tif" for band in bands), ".Fmask.tif", ".cmr.xml")

    return (
        # The thumbnail lives in the "public" bucket, and all other files live in
        # the "protected" bucket.
        ("lp-prod-public", f"{collection}/{granule_id}/{granule_id}.jpg"),
        *(
            ("lp-prod-protected", f"{collection}/{granule_id}/{granule_id}{suffix}")
            for suffix in suffixes
        ),
    )


def make_s3_downloader(s3: S3Client) -> Downloader:
    """Make a downloader that downloads from S3 URLs via an S3 client."""

    def s3_download_file(src: tuple[str, str], dst: Path) -> None:
        bucket, key = src
        print(f"Downloading s3://{bucket}/{key} to {dst}")
        s3.download_file(bucket, key, str(dst))

    return s3_download_file


def download_files(
    downloader: Downloader,
    srcs: Sequence[tuple[str, str]],
    dst_dir: Path,
) -> tuple[Sequence[tuple[str, str]], Sequence[Path]]:
    """Download objects from AWS S3 to a local directory.

    Parameters
    ----------
    downloader:
        Callable that downloads a single file to a local directory.
    srcs:
        Sequence of source 2-tuples of the form (bucket, key).
    dst_dir:
        Path to local destination directory.

    Returns
    -------
    Sequence of 2-tuples of the form `((bucket, key), path)`, where `path` is the
    full local path of the object downloaded from (bucket, key).  Each `path` is
    of the form `dst_dir / filename`, where `filename` is the "basename" of `key`.
    """
    from concurrent.futures import ThreadPoolExecutor

    src_names = [key[key.rfind("/") + 1 :] for _, key in srcs]
    dsts = [(dst_dir / src_name).absolute() for src_name in src_names]
    missing = [(src, dst) for src, dst in zip(srcs, dsts) if not dst.exists()]
    missing_srcs, missing_dsts = zip(*missing) if missing else ([], [])

    with ThreadPoolExecutor() as executor:
        # We don't care about collecting the results of the map method, but we
        # must force iteration over the returned iterator to make sure everything
        # is downloaded before proceeding.
        list(executor.map(downloader, missing_srcs, missing_dsts))

    return missing_srcs, missing_dsts


def strip_metadata_urls(cmr_xml: Path) -> None:
    """Strip all URL entries from a CMR XML metadata file (in place).

    Since an HLS CMR XML file contains URLs relevant to HLS granule files, such
    URLs are not relevant to HLS VI artifacts.  Therefore we strip them out and
    let Cumulus re-populate them appropriately during ingestion.

    Besides, for some unexplained reason, there are entries containing checksums
    with the `Algorithm` value set to `SHA512`, but the granule schema does not
    permit such a value for `Algorithm` (it permits `SHA-512` -- with a dash),
    so the VI "generate metadata" step fails validation when these entries remain.

    Parameters
    ----------
    cmr_xml:
        Path to the CMR XML file from which URL entries are to be stripped.
        The result is produced in-place.  See `resources/strip-urls.xslt` for
        details on how the XML is transformed.
    """
    from importlib.resources import files
    from lxml import etree

    transform = etree.XSLT(
        etree.XML(
            files("hls_vi_historical")
            .joinpath("resources", "strip-urls.xslt")
            .read_text(),
            None,
        )
    )

    # We must use write_c14n (canonicalization) so that empty elements are NOT
    # collapsed (e.g. <foo></foo> is NOT collapased to <foo/>) because the XML
    # SAXParser barfs on collapsed empty elements, causing the "generate metadata"
    # step to fail.
    transform(etree.parse(cmr_xml, None)).write_c14n(cmr_xml)


def prepare_inputs(s3: S3Client, granule_id: str, dst_dir: Path) -> None:
    """Prepare HLS granule files for VI processing.

    Download granule's HLS files (from LPDAAC buckets) required for producing VI
    outputs, and strip all URL elements from the granule's CMR XML file because
    they are specific to the HLS files and won't be relevant to the VI outputs.
    The URL entries will be re-populated during Cumulus ingestion.

    Parameters
    ----------
    s3:
        Boto3 S3 client to use for downloading HLS granule files
    granule_id:
        ID of the granule to download files for
    dst_dir:
        Path to local directory to download files to
    """
    sources = granule_sources(granule_id)
    download_files(make_s3_downloader(s3), sources, dst_dir)
    strip_metadata_urls(dst_dir / f"{granule_id}.cmr.xml")


def create_outputs(granule_id: str, input_dir: Path, output_dir: Path) -> None:
    """Create HLS VI outputs for a granule from HLS inputs.

    Parameters
    ----------
    granule_id:
        ID of the granule to process
    input_dir:
        Path to directory containing HLS input files (band tifs and CMR XML
        metadata file)
    output_dir:
        Path to directory where VI outputs are to be written: vegetation indices
        (tifs), CMR XML metadata file, and STAC item JSON file.
    """
    print(f"Creating vegetation indices from {input_dir} to {output_dir}")
    generate_vi_granule(input_dir, output_dir, granule_id)

    vi_granule_id = granule_id.replace("HLS", "HLS-VI", 1)
    hls_cmr_xml_path = input_dir / f"{granule_id}.cmr.xml"
    hls_vi_cmr_xml_path = output_dir / f"{vi_granule_id}.cmr.xml"
    hls_vi_stac_json_path = output_dir / f"{vi_granule_id}_stac.json"

    print(f"Creating VI CMR metadata from {hls_cmr_xml_path} to {hls_vi_cmr_xml_path}")
    generate_metadata(input_dir, output_dir)

    print(f"Creating STAC item from {hls_vi_cmr_xml_path} to {hls_vi_stac_json_path}")
    create_item(
        hls_vi_metadata=str(hls_vi_cmr_xml_path),
        out_json=str(hls_vi_stac_json_path),
        endpoint="data.lpdaac.earthdatacloud.nasa.gov",
        version="020",
    )


def output_key_prefix(granule_id: str) -> str:
    """Construct an S3 key prefix for the HLS VI outputs created for an HLS granule.

    Parameters
    ----------
    granule_id:
        Granule ID for an HLS granule.

    Returns
    -------
    S3 key prefix for where HLS VI outputs for the specified HLS granule should
    be uploaded.

    Examples
    --------
    >>> output_key_prefix("HLS.L30.T58UFF.2025105T234951.v2.0")
    'L30_VI/data/2025105/HLS-VI.L30.T58UFF.2025105T234951.v2.0'
    >>> output_key_prefix("HLS.S30.T59VNH.2025105T234641.v2.0")
    'S30_VI/data/2025105/HLS-VI.S30.T59VNH.2025105T234641.v2.0'
    """
    id_ = GranuleId.from_string(granule_id)
    vi_granule_id = granule_id.replace("HLS", "HLS-VI", 1)
    yyyyddd = id_.acquisition_date[:7]

    return f"{id_.instrument.name}_VI/data/{yyyyddd}/{vi_granule_id}"


def create_manifest(
    job_id: str,
    granule_id: str,
    input_dir: Path,
    bucket: str,
) -> Path:
    from hls_manifest import hls_manifest

    key_prefix = output_key_prefix(granule_id)
    collection_suffix, *_, vi_granule_id = key_prefix.split("/")
    manifest_filename = f"{vi_granule_id}.json"
    manifest_path = input_dir / manifest_filename

    # This is a CLI function (via the "click" library), so we must call it with
    # a list of string arguments.
    hls_manifest.main(
        [
            str(input_dir),
            str(manifest_path),
            f"s3://{bucket}/{key_prefix}",
            f"HLS{collection_suffix}",
            vi_granule_id,
            job_id,
            "false",
        ],
        # Prevent "click" from exiting the process.
        standalone_mode=False,
    )

    return manifest_path


def upload_outputs(
    s3: S3Client,
    job_id: str,
    granule_id: str,
    output_dir: Path,
    bucket: str,
    debug: bool,
) -> None:
    """Upload all VI outputs in a directory for a granule to an S3 bucket."""

    key_prefix = output_key_prefix(granule_id)
    acl: ObjectCannedACLType = "public-read" if debug else "private"

    for src in output_dir.iterdir():
        key = f"{key_prefix}/{src.name}"

        with open(src, "rb") as body:
            print(f"Uploading {src} to s3://{bucket}/{key}")
            s3.put_object(Bucket=bucket, Key=key, Body=body, ACL=acl)

    src = create_manifest(job_id, granule_id, output_dir, bucket)

    with open(src, "rb") as body:
        key = f"{key_prefix}/{src.name}"
        print(f"Uploading manifest to s3://{bucket}/{key}")
        s3.put_object(Bucket=bucket, Key=key, Body=body, ACL=acl)


def main() -> None:
    job_id = os.environ["AWS_BATCH_JOB_ID"]
    granule_id = os.environ["GRANULE_ID"]
    output_bucket = os.environ.get("DEBUG_BUCKET", os.environ["OUTPUT_BUCKET"])
    debug = os.environ.get("DEBUG_BUCKET") is not None

    working_dir = Path("/var") / "scratch" / job_id
    input_dir = working_dir / "hls"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir = working_dir / "hls-vi"
    output_dir.mkdir(parents=True, exist_ok=True)

    s3 = boto3.client("s3")

    prepare_inputs(s3, granule_id, input_dir)
    create_outputs(granule_id, input_dir, output_dir)
    upload_outputs(s3, job_id, granule_id, output_dir, output_bucket, debug)


if __name__ == "__main__":
    main()
