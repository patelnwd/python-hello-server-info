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
curl http://localhost:8080/
```

Example response:

```json
{
  "message": "Hello World",
  "method": "GET"
}
```

### Health Endpoint

Endpoint: `/health`

Example request:

```bash
curl http://localhost:8080/health
```

Example response:

```json
{
  "status": "healthy"
}
```

The `/health` endpoint can also include server metadata:

```bash
curl "http://localhost:8080/health?serverInfo=true"
```

## Server Info Mode

Add `serverInfo=true` to include details about the backend handling the request:

```bash
curl "http://localhost:8080/?serverInfo=true"
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
      "host": "localhost:8080",
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
curl -I "http://localhost:8080/?serverInfo=true"
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
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Test it:

```bash
curl http://localhost:8080/
curl "http://localhost:8080/?serverInfo=true"
curl http://localhost:8080/health
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
docker run --rm -p 8080:8080 python-hello-server-info
```

In another terminal, test the running container:

```bash
curl http://localhost:8080/
curl http://localhost:8080/health
curl "http://localhost:8080/?serverInfo=true"
```

Stop the container with `Ctrl+C` when you are done testing.

## Publish Image to Docker Hub

This project uses the Docker Hub image name
`patelnwd/python-hello-server-info`.

In Docker Hub, create a repository named `python-hello-server-info` under the
`patelnwd` account and set the visibility to public if you want anyone to be
able to pull it.

Log in to Docker Hub:

```bash
docker login
```

Tag the local image with your Docker Hub repository name:

```bash
docker tag python-hello-server-info patelnwd/python-hello-server-info:latest
```

Push the image:

```bash
docker push patelnwd/python-hello-server-info:latest
```

After the push completes, the image can be pulled publicly if the Docker Hub
repository visibility is set to public.

## Run the Public Docker Image

Pull the public image:

```bash
docker pull patelnwd/python-hello-server-info:latest
```

Run it:

```bash
docker run --rm -p 8080:8080 patelnwd/python-hello-server-info:latest
```

Test it:

```bash
curl http://localhost:8080/
curl "http://localhost:8080/?serverInfo=true"
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
