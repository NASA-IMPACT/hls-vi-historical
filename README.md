# HLS Vegetation Indices (HLS-VI) Historical

Docker image for generating a suite of Vegetation Indices (VI) for historical
HLS Products, which were ingested _prior_ to the deployment of HLS-VI forward
processing into production.

## Local Testing

Testing the functionality locally requires [Docker Desktop].  To build the image
and run a container, run the following command, where `GRANULE_ID` is an HLS L30
or S30 granule ID:

```plain
docker compose up --rm --build cli GRANULE_ID
```

**NOTE:** Currently, this allows you to only validate that the image is built
without error and runs the `generate-vi-files.sh` script as expected, but the
script will fail when attempting to download files, due to lack of permissions.

[Docker Desktop]:
    https://docs.docker.com/desktop/
