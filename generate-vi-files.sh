#!/usr/bin/env bash
set -euo pipefail

if [[ ${#@} != 1 ]]; then
    echo >&2 "usage: generate-vi-files.sh GRANULE_ID"
    exit 1
fi

# Remove files on exit
trap 'rm -rf ${workdir}; exit' INT TERM EXIT

granule_id=${1}
workdir=/var/scratch/${granule_id}
indir="${workdir}/inputs"
mkdir -p "${indir}"
outdir="${workdir}/outputs"
mkdir -p "${outdir}"

# TODO Download relevant granule files for supplied granule ID to indir

vi_generate_indices -i "${indir}" -o "${outdir}" -s "${granule_id}"
vi_generate_metadata -i "${indir}" -o "${outdir}"
vi_generate_stac_items \
    --cmr_xml "${outdir}/${granule_id}.cmr.xml" \
    --endpoint data.lpdaac.earthdatacloud.nasa.gov \
    --version 020 \
    --out_json "${outdir}/${granule_id}_stac.json"

# TODO Copy generated files to relevant bucket for LPDAAC to see
# TODO Write manifest.json to bucket to trigger LPDAAC notification
