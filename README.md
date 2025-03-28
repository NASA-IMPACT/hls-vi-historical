# HLS Vegetation Indices (HLS-VI) Historical

Docker image for generating a suite of Vegetation Indices (VI) for historical
HLS Products, which were ingested _prior_ to the deployment of HLS-VI forward
processing into production.

## Local Image Testing

Testing the functionality locally requires [Docker Desktop].  To build the image
and run a container, run the following command, where `GRANULE_ID` is an HLS L30
or S30 granule ID:

```plain
docker compose up --rm --build cli GRANULE_ID
```

**NOTE:** Currently, this allows you to only validate that the image is built
without error and runs the `generate-vi-files.sh` script as expected, but the
script will fail when attempting to download files, due to lack of permissions.

## Local GitHub Workflow Testing

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

**NOTE:** On macOS, you may need to add the following line to your `~/.netrc`
file in order for `act` to be able to reference your Docker Desktop socket:

```plain
--container-daemon-socket unix:///var/run/docker.sock
```

[act]:
    https://nektosact.com/
[Docker Desktop]:
    https://docs.docker.com/desktop/
