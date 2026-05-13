# Python Hello Server Info

A lightweight FastAPI demo service for testing Python runtime setup,
Docker-based deployment, load balancer behavior, and distributed system
visibility.

The main use case is running the same service on multiple EC2 instances,
containers, or pods behind an AWS Application Load Balancer (ALB), Network Load
Balancer (NLB), or ingress controller, then checking which backend handled each
request.

## Features

- Supports common HTTP methods on `/`.
- Shows a browser-friendly dashboard when `/` is opened in a web browser.
- Provides a dedicated `/health` endpoint for liveness checks.
- Supports an optional `serverInfo=true` query parameter.
- Returns server/container metadata to identify the responding backend.
- Useful for ALB, NLB, ingress, EC2, container, and load balancing debugging.
- Minimal FastAPI setup using `uv` for dependency management.

## API Endpoints

### Root Endpoint

Endpoint: `/`

Supported methods:

- `GET`
- `POST`
- `PUT`
- `DELETE`
- `PATCH`
- `OPTIONS`
- `TRACE`
- `HEAD`

Example request:

```bash
curl http://localhost:8002/
```

Example response:

```json
{
  "message": "Hello World",
  "method": "GET"
}
```

Open the same URL in a browser to view a dashboard with server metadata and the
live JSON payload:

```text
http://localhost:8002/
```

To explicitly request JSON from clients that normally prefer HTML, send an
`Accept: application/json` header:

```bash
curl -H "Accept: application/json" http://localhost:8002/
```

### Health Endpoint

Endpoint: `/health`

Example request:

```bash
curl http://localhost:8002/health
```

Example response:

```json
{
  "status": "healthy"
}
```

The `/health` endpoint can also include server metadata:

```bash
curl "http://localhost:8002/health?serverInfo=true"
```

### Database Health Endpoint

Set `POSTGRES_URI` to enable a PostgreSQL connectivity check:

```env
POSTGRES_URI=postgresql://user:password@hostname:5432/database
```

Check database connectivity directly:

```bash
curl "http://localhost:8002/health/database"
```

Or include it in the main health response:

```bash
curl "http://localhost:8002/health?database=true"
```

When the database is reachable, the response includes:

```json
{
  "status": "healthy",
  "database": {
    "configured": true,
    "connected": true,
    "latencyMs": 12.34
  }
}
```

If `POSTGRES_URI` is missing or the connection fails, the database health check
returns `503` with an `unhealthy` status. The response never includes the
Postgres URI.

## Server Info Mode

Add `serverInfo=true` to include details about the backend handling the request:

```bash
curl "http://localhost:8002/?serverInfo=true"
```

Example response:

```json
{
  "message": "Hello World",
  "method": "GET",
  "serverInfo": {
    "hostname": "container-id",
    "containerId": "container-id",
    "ipAddress": "172.17.0.2",
    "platform": "Linux-...",
    "pythonVersion": "3.12.x",
    "processId": 1,
    "serverTimeUtc": "2026-05-10T10:00:00+00:00",
    "clientHost": "client-ip",
    "headers": {
      "host": "localhost:8002",
      "xForwardedFor": "...",
      "xForwardedProto": "...",
      "xForwardedPort": "..."
    }
  }
}
```

Useful for:

- Verifying load balancing behavior.
- Debugging sticky sessions.
- Identifying the backend EC2 instance, container, or pod.
- Checking forwarded headers from ALB, NLB, reverse proxies, or ingress.

## HEAD Request Behavior

`HEAD` responses do not include a response body.

When `serverInfo=true` is passed with a `HEAD` request, the app returns selected
metadata through response headers:

```bash
curl -I "http://localhost:8002/?serverInfo=true"
```

Example headers:

```text
X-Hostname: ...
X-Container: ...
X-PID: ...
```

## Run Locally

Install dependencies:

```bash
uv sync
```

Start the app:

```bash
uv run python -m app.main
```

The app loads `.env` automatically when the file exists. `APP_HOST`, `APP_PORT`,
and `DATABASE_CONNECT_TIMEOUT` are required. If any of them are missing or
invalid, startup fails with a clear error.

Test it:

```bash
curl http://localhost:8002/
curl "http://localhost:8002/?serverInfo=true"
curl http://localhost:8002/health
```

## Build the First Docker Image

Make sure Docker is running, then build the image from the project root:

```bash
docker build -t python-hello-server-info .
```

Confirm the image exists:

```bash
docker images python-hello-server-info
```

Run the image locally:

```bash
docker run --rm --env-file .env -p 8002:8002 python-hello-server-info
```

If you change `APP_PORT` in `.env`, publish the same container port in the
Docker run command. For example, `APP_PORT=9000` should use `-p 9000:9000`.

In another terminal, test the running container:

```bash
curl http://localhost:8002/
curl http://localhost:8002/health
curl "http://localhost:8002/?serverInfo=true"
```

Stop the container with `Ctrl+C` when you are done testing.

## Publish Image to AWS ECR

This project can publish to a private AWS ECR repository such as
`<aws-account-id>.dkr.ecr.<region>.amazonaws.com/<namespace>/<image-name>`.

Use the release helper to keep incremental version tags and update `latest` at
the same time.

Choose the release type based on the impact of the change. The project uses
semantic versioning: `MAJOR.MINOR.PATCH`.

Patch release:

Use this for small, backward-compatible fixes. Examples include bug fixes,
documentation updates, dependency patch updates, or small internal cleanup.

If the current version is `1.0.0`, this publishes `1.0.1` and updates `latest`.

```bash
uv run python scripts/release_image.py patch
```

Minor release:

Use this when adding backward-compatible functionality. Examples include new
endpoints, new optional environment variables, or new response fields that do
not break existing clients.

If the current version is `1.0.1`, this publishes `1.1.0` and updates `latest`.

```bash
uv run python scripts/release_image.py minor
```

Major release:

Use this for breaking changes. Examples include removing endpoints, changing
required environment variables, changing response formats, or changing runtime
behavior in a way existing deployments must account for.

If the current version is `1.1.0`, this publishes `2.0.0` and updates `latest`.

```bash
uv run python scripts/release_image.py major
```

The script reads the current version from `pyproject.toml`, increments it, logs
in to ECR, builds the image, and pushes both tags:

```text
<aws-account-id>.dkr.ecr.<region>.amazonaws.com/<namespace>/<image-name>:<version>
<aws-account-id>.dkr.ecr.<region>.amazonaws.com/<namespace>/<image-name>:latest
```

Configure your registry and repository with environment variables:

```bash
export AWS_REGION=us-east-1
export ECR_REGISTRY=<aws-account-id>.dkr.ecr.us-east-1.amazonaws.com
export ECR_REPOSITORY=<namespace>/<image-name>
```

Or pass them directly:

```bash
uv run python scripts/release_image.py patch \
  --registry <aws-account-id>.dkr.ecr.us-east-1.amazonaws.com \
  --repository <namespace>/<image-name>
```

To publish a specific version:

```bash
uv run python scripts/release_image.py current --version 1.2.3
```

To preview the commands without changing files, building, or pushing:

```bash
uv run python scripts/release_image.py patch --dry-run
```

After publishing, update your AWS deployment to use the versioned image tag.
`latest` is also updated for convenience, but the versioned tag is safer for
repeatable deployments.

## Run the ECR Docker Image

Pull the ECR image:

```bash
docker pull <aws-account-id>.dkr.ecr.<region>.amazonaws.com/<namespace>/<image-name>:latest
```

Run it:

```bash
docker run --rm --env-file .env -p 8002:8002 <aws-account-id>.dkr.ecr.<region>.amazonaws.com/<namespace>/<image-name>:latest
```

Test it:

```bash
curl http://localhost:8002/
curl "http://localhost:8002/?serverInfo=true"
```

## ALB / EC2 Testing

Deploy the same Docker image to multiple EC2 instances behind an AWS ALB.

Use the ALB DNS name with `serverInfo=true`:

```bash
curl "http://<alb-dns-name>/?serverInfo=true"
```

Repeat the request a few times. The `hostname`, `containerId`, `ipAddress`, and
`processId` values help show which backend node responded.

The `/health` endpoint can be used as the ALB target group health check path:

```text
/health
```

## Use Cases

- AWS ALB and NLB debugging.
- Kubernetes ingress validation.
- EC2 and container routing checks.
- Load balancing demos.
- Blue-green and canary deployment validation.
- Troubleshooting distributed routing and forwarded headers.

## Project Structure

```text
.
|-- app/
|   `-- main.py
|-- scripts/
|   `-- release_image.py
|-- .vscode/
|   |-- extensions.json
|   |-- launch.json
|   |-- settings.json
|   `-- tasks.json
|-- .gitignore
|-- .dockerignore
|-- Dockerfile
|-- LICENSE
|-- README.md
|-- pyproject.toml
`-- uv.lock
```

## Future Enhancements

- Add a `/ready` endpoint for readiness probes.
- Add AWS ECS or EC2 metadata integration.
- Add Kubernetes pod metadata.
- Add structured JSON logging.
- Add OpenTelemetry tracing support.

## License

MIT License. See `LICENSE` for details.

## Author

Built for practical debugging and observability in modern distributed systems.
