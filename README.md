# HLS Vegetation Indices (HLS-VI) Historical

An AWS Lambda function to generate a suite of Vegetation Indices (VI) for
historical HLS Products, which were ingested _prior_ to the deployment of HLS-VI
forward processing into production.

## Development

### Python Virtual Environment

If you wish to create a Python virtual environment for resolving dependencies in
your development environment, the following are required:

1. [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/)
1. Run `uv venv`, which will create a virtual environment in the `.venv` directory

You may activate the virtual environment like so:

```plain
source .venv/bin/activate
```

### Local Testing

Testing the AWS Lambda function locally requires Docker.  To start a container
that exposes an endpoint for sending messages to the lambda function, run the
following:

```plain
docker compose up --build -w
```

This will do the following:

1. build the image (if necessary)
1. watch for local changes (see `compose.yaml`)
1. expose the endpoint
   `http://localhost:9000/2015-03-31/functions/function/invocations`

The lambda function assumes that it receives SQS events, so you should send JSON
messages with `"Records"` as the top-level name, associated with an array of
records representing SQS messages (at a minimum, a `"body"` key and a JSON
string value):

```plain
curl "http://localhost:9000/2015-03-31/functions/function/invocations" \
    -d '{"Records":[{"body":"{\"granule_id\":\"HLS.L30.T06WVS.2024120T211159.v2.0\"}"}]}'
```
