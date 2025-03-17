from __future__ import annotations

from pathlib import Path

from aws_lambda_powertools.utilities.data_classes import SQSEvent, event_source
from hls_vi.generate_indices import generate_vi_granule
from hls_vi.generate_metadata import generate_metadata
from hls_vi.generate_stac_items import create_item


@event_source(data_class=SQSEvent)
def handler(event: SQSEvent, _context):
    # Handle and cleanup records sequentially to avoid disk space issues, assuming we're
    # downloading (and unzipping?) HLS granules?
    for record in event.records:
        granule_id = record.json_body["granule_id"]
        print(f"{granule_id=}")
        input_dir = Path()  # some arbitrary path?
        output_dir = Path()  # some arbitrary path?

        # generate_vi_granule(input_dir, output_dir, granule_id)
        # generate_metadata(input_dir, output_dir)
        # create_item(cmr_xml_path, stac_json_file, endpoint, version)
