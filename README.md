# HLS Vegetation Indices (HLS-VI) Historical

Docker image for generating a suite of Vegetation Indices (VI) for historical
HLS Products, which were ingested _prior_ to the deployment of HLS-VI forward
processing into production.  However, there is nothing preventing its use for
_re_-creating VI granules that have already been produced during forward
processing.

- [Running a Container](#running-a-container)
- [Development](#development)
  - [Running Unit Tests](#running-unit-tests)
  - [Bootstrapping MinIO](#bootstrapping-minio)
  - [Testing the Docker Image](#testing-the-docker-image)
  - [Inspecting MinIO Objects](#inspecting-minio-objects)
  - [Locally Testing the GitHub Workflow](#locally-testing-the-github-workflow)

## Running a Container

When running a container from an image published from this repository, the
following environment variables must/can be set:

- `AWS_BATCH_JOB_ID`: It is assumed that the container will be used in an AWS
  batch job, so this should be set to the job ID.
- `GRANULE_ID`: ID of the HLS granule from which to produce the associated HLS
  VI granule files.
- `LPDAAC_PROTECTED_BUCKET_NAME` (_optional_): Name of the bucket containing
  ingested HLS granule files (default: `"lp-prod-protected"`).
- `LPDAAC_PUBLIC_BUCKET_NAME` (_optional_): Name of the bucket containing
  HLS thumbnails (`.jpg`) (default: `"lp-prod-public"`) associated with the
  granule files in the other bucket.
- `OUTPUT_BUCKET`: Name of the bucket in which to put the produced HLS VI
  granule files.
- LPDAAC AWS Credentials (_optional_): AWS credentials for accessing LPDAAC
  data buckets may be provided.
  - `LPDAAC_ACCESS_KEY_ID`
  - `LPDAAC_SECRET_ACCESS_KEY`
  - `LPDAAC_SESSION_TOKEN`
  - **Note**: The `hls-vi-historical-orchestration` system injects these environment
    variables into this container when running AWS Batch jobs.
    This works by defining "secrets" in the JobDefinition's configuration settings
    that instruct the AWS Batch worker to pull from SecretsManager and pass the values
    as environment variables when running the container.
    Since these S3 credentials expire after 1 hour, a scheduled Lambda function refreshes
    the value of the secret with new credentials provided by the LPDAAC `/s3credentials`
    endpoint.
- `DEBUG_BUCKET` (_optional_): Name of the bucket to use _instead of_
  `OUTPUT_BUCKET`, so that the produced outputs can be inspected for debugging
  purposes, without triggering LPDAAC notification.

## Development

Prerequisites:

- [Install uv](https://docs.astral.sh/uv/getting-started/installation/) and run
  `uv sync` to create a Python virtual environment in the directory `.venv` with
  all dependencies listed in `pyproject.toml` installed.  This will allow your
  IDE to resolve references.
- Install [Docker Desktop]
- Install [AWS CLI] (optional, for inspecting S3 objects in your MinIO store)
- Install [act] (optional, for locally testing Docker image publication GitHub workflow)

### Running Unit Tests

Run unit tests as follows:

```plain
uv run pytest
```

### Bootstrapping MinIO

To locally simulate AWS S3, we use [MinIO] so we can locally test the Docker
image.  This requires us to first "bootstrap" MinIO with some HLS granule files
so that our local MinIO server can mock the real LPDAAC buckets.

HLS granule files are hosted in LPDAAC AWS S3 buckets requiring Earthdata Login
credentials in order to read (download) them, which is what we must do in order
to bootstrap our local MinIO server with granule files.  To keep things simple,
the bootstrapping script relies upon having your `~/.netrc` file populated an
entry of the following form:

```plain
machine urs.earthdata.nasa.gov login USERNAME password PASSWORD
```

where `USERNAME` and `PASSWORD` are your credentials for [Earthdata Login].

To populate local MinIO buckets with some files for an L30 or S30 granule (into
the `.minio` directory; ignored by Git), first, **make sure your Docker daemon
is running**, then run the following commands:

```plain
docker compose up -d minio
uv run scripts/bootstrap-minio.py GRANULE_ID
```

where `GRANULE_ID` is any HLS [L30] or [S30] granule ID.

For example:

```plain
uv run scripts/bootstrap-minio.py HLS.L30.T58UFF.2025105T234951.v2.0
uv run scripts/bootstrap-minio.py HLS.S30.T59VNH.2025105T234641.v2.0
```

Once you're done, run `docker compose down` to shutdown the MinIO server.

### Testing the Docker Image

Once MinIO is bootstrapped with HLS granule files, you can locally run a Docker
container to check that it can produce corresponding VI files (data, metadata,
and manifest files) for any granule that you have bootstrapped into MinIO, like
so:

```plain
docker compose run --rm --build -e GRANULE_ID=<BOOTSTRAPPED_GRANULE_ID> cli
```

where `<BOOTSTRAPPED_GRANULE_ID>` is any granule ID that you have bootstrapped
into MinIO, as described above.

For example:

```plain
docker compose run --rm --build -e GRANULE_ID=HLS.L30.T58UFF.2025105T234951.v2.0 cli
```

Note that the command above will also automatically bring up the local MinIO
server if it is not already running, so you don't have to explicitly start it.

Once you're done, run `docker compose down` to shutdown the MinIO server.

### Inspecting MinIO Objects

S3 objects bootstrapped into MinIO are written to the `.minio` directory (which
is ignored by Git).  While they are written into a navigable directory
structure, the S3 objects themselves are not directly readable as local files.

However, since MinIO is an S3 store, you may use the `aws s3` and `aws s3api`
commands of the [AWS CLI], just as you would do against an AWS account, but you
must do a bit of configuration.

First, create a `minio` AWS profile:

```plain
aws configure --profile minio
```

When prompted, enter `minioadmin` for both the "AWS Access Key ID" and the
"AWS Secret Access Key". For "Default region name", enter `us-west-2` (although
any value is fine, as it doesn't matter), and whichever "Default output format"
you prefer (e.g., "json").

Next, add the following lines to your `~/.aws/config` file:

> [!NOTE]
>
> The `[profile minio]` section should have been created by the previous command, so
> you should simply need to add the `services = minio` line under that section, along
> with adding the `[services minio]` section.

```plain
[profile minio]
region = us-west-2
output = json
services = minio
[services minio]
s3 =
  endpoint_url = http://localhost:9000
```

Now you can specify `--profile minio` with various `aws s3` and `aws s3api`
commands to work with your local MinIO server.

For example, if you want to inspect a VI output from running the
`docker compose run` command shown in the previous section, you could run the
following command to copy it out of the bucket to a local file:

```plain
aws --profile minio s3 cp s3://hls-global-v2-forward/KEY .
```

If you want to empty and remove any of your MinIO buckets:

```plain
aws --profile minio s3 rb --force s3://BUCKET
```

### Locally Testing the GitHub Workflow

Locally testing the GitHub workflow to build, tag, and push an image to Amazon
ECR requires [act].  In addition, you must obtain AWS short-term access keys,
and optionally set the environment variables `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN` accordingly.

You may then run the following command to build, tag, and push an image.  If
you set the environment variables, then they will be used as the specified
secret values, otherwise `act` will prompt you for the values:

```plain
act -s AWS_ACCESS_KEY_ID -s AWS_SECRET_ACCESS_KEY -s AWS_SESSION_TOKEN pull_request
```

This will tag the image with the short SHA of your current git commit.  However,
in CI, for a pull request, the tag will be the PR number, and for a release, it
will be the repository tag.

**NOTE:** On macOS, you may need to add the following line to your `~/.actrc`
file in order for `act` to be able to reference your Docker Desktop socket:

```plain
--container-daemon-socket unix:///var/run/docker.sock
```

[act]:
  https://nektosact.com/
[AWS CLI]:
  https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
[Docker Desktop]:
  https://docs.docker.com/desktop/
[Earthdata Login]:
  https://urs.earthdata.nasa.gov/
[MinIO]:
  https://min.io/docs/minio/container/index.html
[L30]:
  https://search.earthdata.nasa.gov/search/granules?p=C2021957657-LPCLOUD
[S30]:
  https://search.earthdata.nasa.gov/search/granules?p=C2021957295-LPCLOUD
