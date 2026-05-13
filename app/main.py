import os
import socket
import platform
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response

REQUIRED_ENV_VARS = (
    "APP_HOST",
    "APP_PORT",
    "DATABASE_CONNECT_TIMEOUT",
)


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.is_file():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")

        if key:
            os.environ.setdefault(key, value)


def get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()

    if not value:
        raise RuntimeError(f"{name} must be configured in environment or .env")

    return value


def validate_required_env() -> None:
    for name in REQUIRED_ENV_VARS:
        get_required_env(name)

    get_app_port()
    get_database_connect_timeout()


def get_app_host() -> str:
    return get_required_env("APP_HOST")


def get_app_port() -> int:
    raw_port = get_required_env("APP_PORT")

    try:
        return int(raw_port)
    except ValueError as exc:
        raise ValueError(f"APP_PORT must be an integer, got {raw_port!r}") from exc


def get_database_connect_timeout() -> float:
    raw_timeout = get_required_env("DATABASE_CONNECT_TIMEOUT")

    try:
        return float(raw_timeout)
    except ValueError as exc:
        raise ValueError(
            f"DATABASE_CONNECT_TIMEOUT must be a number, got {raw_timeout!r}"
        ) from exc


def check_database_connectivity():
    postgres_uri = os.environ.get("POSTGRES_URI", "").strip()
    result = {
        "configured": bool(postgres_uri),
        "connected": False,
    }

    if not postgres_uri:
        result["message"] = "POSTGRES_URI is not set"
        return result

    started_at = time.monotonic()

    try:
        import psycopg

        with psycopg.connect(
            postgres_uri,
            connect_timeout=get_database_connect_timeout(),
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        result["connected"] = True
        result["latencyMs"] = round((time.monotonic() - started_at) * 1000, 2)
    except Exception as exc:
        result["error"] = str(exc)
        result["latencyMs"] = round((time.monotonic() - started_at) * 1000, 2)

    return result


load_dotenv()
validate_required_env()

app = FastAPI(title=os.environ.get("APP_NAME", "Python Hello Server Info"))


def get_server_info(request: Request):
    hostname = socket.gethostname()

    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = None

    return {
        "appName": os.environ.get("APP_NAME"),
        "appEnv": os.environ.get("APP_ENV"),
        "appMode": os.environ.get("APP_MODE"),
        "appHost": get_app_host(),
        "appPort": get_app_port(),
        "databaseConfigured": bool(os.environ.get("POSTGRES_URI", "").strip()),
        "hostname": hostname,
        "containerId": os.environ.get("HOSTNAME"),
        "ipAddress": ip,
        "platform": platform.platform(),
        "pythonVersion": platform.python_version(),
        "processId": os.getpid(),
        "serverTimeUtc": datetime.now(timezone.utc).isoformat(),
        "clientHost": request.client.host if request.client else None,
        "headers": {
            "host": request.headers.get("host"),
            "xForwardedFor": request.headers.get("x-forwarded-for"),
            "xForwardedProto": request.headers.get("x-forwarded-proto"),
            "xForwardedPort": request.headers.get("x-forwarded-port"),
        },
    }


def build_response(method: str, request: Request, include_server: bool):
    data = {
        "message": "Hello World",
        "method": method,
    }

    if include_server:
        data["serverInfo"] = get_server_info(request)

    return data


def prefers_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept.lower()


def build_dashboard_html() -> str:
    initial_payload = json.dumps(
        {
            "message": "Hello World",
            "method": "GET",
            "serverInfo": {
                "hostname": "loading...",
                "containerId": "loading...",
                "ipAddress": "loading...",
                "platform": "loading...",
                "pythonVersion": "loading...",
                "processId": "loading...",
                "serverTimeUtc": "loading...",
                "clientHost": "loading...",
                "headers": {
                    "host": "loading...",
                    "xForwardedFor": "loading...",
                    "xForwardedProto": "loading...",
                    "xForwardedPort": "loading...",
                },
            },
        }
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Python Hello Server Info</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f8fb;
      --panel: #ffffff;
      --text: #18202b;
      --muted: #5c6878;
      --line: #d9e0ea;
      --accent: #0f766e;
      --accent-dark: #115e59;
      --code: #101828;
      --ok: #15803d;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(135deg, rgba(15, 118, 110, 0.08), transparent 35%),
        linear-gradient(315deg, rgba(37, 99, 235, 0.08), transparent 30%),
        var(--bg);
      color: var(--text);
      font-family:
        Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    }}

    main {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 42px 0;
    }}

    .hero {{
      display: grid;
      grid-template-columns: 1.25fr 0.75fr;
      gap: 24px;
      align-items: stretch;
      margin-bottom: 24px;
    }}

    .panel {{
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 18px 50px rgba(26, 38, 61, 0.08);
    }}

    .intro {{
      padding: 30px;
    }}

    .eyebrow {{
      margin: 0 0 12px;
      color: var(--accent-dark);
      font-size: 0.82rem;
      font-weight: 800;
      letter-spacing: 0;
      text-transform: uppercase;
    }}

    h1 {{
      margin: 0;
      max-width: 740px;
      font-size: clamp(2.1rem, 6vw, 4.7rem);
      line-height: 0.96;
      letter-spacing: 0;
    }}

    .summary {{
      margin: 18px 0 0;
      max-width: 720px;
      color: var(--muted);
      font-size: 1.05rem;
      line-height: 1.65;
    }}

    .status {{
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 250px;
    }}

    .status-code {{
      display: inline-flex;
      width: fit-content;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      border: 1px solid rgba(21, 128, 61, 0.22);
      border-radius: 999px;
      color: var(--ok);
      background: rgba(21, 128, 61, 0.08);
      font-weight: 800;
    }}

    .pulse {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--ok);
      box-shadow: 0 0 0 6px rgba(21, 128, 61, 0.12);
    }}

    .method {{
      margin: 22px 0 0;
      font-size: 3.5rem;
      line-height: 1;
      font-weight: 900;
      letter-spacing: 0;
    }}

    .timestamp {{
      margin-top: 16px;
      color: var(--muted);
      line-height: 1.45;
      overflow-wrap: anywhere;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin-bottom: 24px;
    }}

    .metric {{
      min-height: 116px;
      padding: 18px;
    }}

    .label {{
      margin: 0 0 9px;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0;
      text-transform: uppercase;
    }}

    .value {{
      margin: 0;
      color: var(--code);
      font-family:
        "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      font-size: 0.95rem;
      line-height: 1.45;
      overflow-wrap: anywhere;
    }}

    .details {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }}

    .section {{
      padding: 22px;
    }}

    h2 {{
      margin: 0 0 16px;
      font-size: 1.15rem;
      letter-spacing: 0;
    }}

    dl {{
      display: grid;
      grid-template-columns: 150px 1fr;
      gap: 12px;
      margin: 0;
    }}

    dt {{
      color: var(--muted);
      font-weight: 700;
    }}

    dd {{
      margin: 0;
      font-family:
        "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      overflow-wrap: anywhere;
    }}

    pre {{
      margin: 0;
      padding: 16px;
      max-height: 360px;
      overflow: auto;
      border-radius: 8px;
      background: #111827;
      color: #e5eefb;
      font-size: 0.86rem;
      line-height: 1.55;
    }}

    @media (max-width: 860px) {{
      main {{
        width: min(100% - 24px, 680px);
        padding: 24px 0;
      }}

      .hero,
      .details {{
        grid-template-columns: 1fr;
      }}

      .grid {{
        grid-template-columns: repeat(2, 1fr);
      }}
    }}

    @media (max-width: 560px) {{
      .grid {{
        grid-template-columns: 1fr;
      }}

      dl {{
        grid-template-columns: 1fr;
      }}

      .intro,
      .status,
      .section {{
        padding: 18px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="panel intro">
        <p class="eyebrow">FastAPI backend visibility</p>
        <h2>Python Hello Server Info</h2>
        <p class="summary">
          A lightweight service for checking Python, Docker, and which backend
          instance answered behind an ALB, NLB, or ingress controller.
        </p>
      </div>
      <aside class="panel status">
        <div>
          <div class="status-code"><span class="pulse"></span> Healthy</div>
          <div class="method" id="method">GET</div>
        </div>
        <div class="timestamp" id="serverTimeUtc">Loading server time...</div>
      </aside>
    </section>

    <section class="grid">
      <article class="panel metric">
        <p class="label">Hostname</p>
        <p class="value" id="hostname">Loading...</p>
      </article>
      <article class="panel metric">
        <p class="label">Container</p>
        <p class="value" id="containerId">Loading...</p>
      </article>
      <article class="panel metric">
        <p class="label">IP address</p>
        <p class="value" id="ipAddress">Loading...</p>
      </article>
      <article class="panel metric">
        <p class="label">Process</p>
        <p class="value" id="processId">Loading...</p>
      </article>
    </section>

    <section class="details">
      <article class="panel section">
        <h2>Request And Runtime</h2>
        <dl>
          <dt>Client</dt>
          <dd id="clientHost">Loading...</dd>
          <dt>Platform</dt>
          <dd id="platform">Loading...</dd>
          <dt>Python</dt>
          <dd id="pythonVersion">Loading...</dd>
          <dt>Host header</dt>
          <dd id="hostHeader">Loading...</dd>
          <dt>Forwarded for</dt>
          <dd id="xForwardedFor">Loading...</dd>
          <dt>Forwarded proto</dt>
          <dd id="xForwardedProto">Loading...</dd>
          <dt>Forwarded port</dt>
          <dd id="xForwardedPort">Loading...</dd>
        </dl>
      </article>

      <article class="panel section">
        <h2>JSON Response</h2>
        <pre id="jsonPayload"></pre>
      </article>
    </section>
  </main>

  <script>
    const initialPayload = {initial_payload};

    function text(value) {{
      return value === null || value === undefined || value === "" ? "not set" : value;
    }}

    function render(payload) {{
      const info = payload.serverInfo || {{}};
      const headers = info.headers || {{}};

      document.getElementById("method").textContent = text(payload.method);
      document.getElementById("serverTimeUtc").textContent = text(info.serverTimeUtc);
      document.getElementById("hostname").textContent = text(info.hostname);
      document.getElementById("containerId").textContent = text(info.containerId);
      document.getElementById("ipAddress").textContent = text(info.ipAddress);
      document.getElementById("processId").textContent = text(info.processId);
      document.getElementById("clientHost").textContent = text(info.clientHost);
      document.getElementById("platform").textContent = text(info.platform);
      document.getElementById("pythonVersion").textContent = text(info.pythonVersion);
      document.getElementById("hostHeader").textContent = text(headers.host);
      document.getElementById("xForwardedFor").textContent = text(headers.xForwardedFor);
      document.getElementById("xForwardedProto").textContent = text(headers.xForwardedProto);
      document.getElementById("xForwardedPort").textContent = text(headers.xForwardedPort);
      document.getElementById("jsonPayload").textContent =
        JSON.stringify(payload, null, 2);
    }}

    async function refresh() {{
      try {{
        const response = await fetch("/?serverInfo=true", {{
          headers: {{ "Accept": "application/json" }},
          cache: "no-store"
        }});
        render(await response.json());
      }} catch (error) {{
        render(initialPayload);
        document.getElementById("jsonPayload").textContent =
          "Unable to load JSON response: " + error;
      }}
    }}

    render(initialPayload);
    refresh();
    setInterval(refresh, 5000);
  </script>
</body>
</html>"""


@app.api_route(
    "/",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "TRACE", "HEAD"],
)
async def root(request: Request, serverInfo: bool = Query(False)):
    method = request.method

    if method == "HEAD":
        headers = {}
        if serverInfo:
            info = get_server_info(request)
            headers = {
                "X-Hostname": str(info["hostname"]),
                "X-Container": str(info["containerId"]),
                "X-PID": str(info["processId"]),
            }
        return Response(status_code=200, headers=headers)

    if method == "GET" and prefers_html(request) and not serverInfo:
        return HTMLResponse(content=build_dashboard_html())

    return JSONResponse(content=build_response(method, request, serverInfo))


@app.get("/health")
async def health(
    request: Request,
    serverInfo: bool = Query(False),
    database: bool = Query(False),
):
    data = {"status": "healthy"}
    status_code = 200

    if serverInfo:
        data["serverInfo"] = get_server_info(request)

    if database:
        data["database"] = check_database_connectivity()
        if not data["database"]["connected"]:
            data["status"] = "unhealthy"
            status_code = 503

    return JSONResponse(content=data, status_code=status_code)


@app.get("/health/database")
async def database_health():
    database_status = check_database_connectivity()
    status_code = 200 if database_status["connected"] else 503

    return JSONResponse(
        content={
            "status": "healthy" if database_status["connected"] else "unhealthy",
            "database": database_status,
        },
        status_code=status_code,
    )


def run() -> None:
    import uvicorn

    uvicorn.run(app, host=get_app_host(), port=get_app_port())


if __name__ == "__main__":
    run()
