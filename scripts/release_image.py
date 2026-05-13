#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


DEFAULT_REGION = "us-east-1"
DEFAULT_REGISTRY = "000000000000.dkr.ecr.us-east-1.amazonaws.com"
DEFAULT_REPOSITORY = "example/demo-app"
PYPROJECT = Path("pyproject.toml")
ENV_FILE = Path(".env")
COLORS = {
    "bold": "\033[1m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "cyan": "\033[36m",
    "reset": "\033[0m",
}


def colorize(text, color):
    if os.environ.get("NO_COLOR") and not os.environ.get("FORCE_COLOR"):
        return text

    return f"{COLORS[color]}{text}{COLORS['reset']}"


def load_dotenv(path=ENV_FILE):
    if not path.is_file():
        return

    for line in path.read_text().splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")

        if key:
            os.environ.setdefault(key, value)


def run(command, *, input_text=None, dry_run=False):
    print(colorize("+ " + " ".join(command), "cyan"))

    if dry_run:
        return ""

    completed = subprocess.run(
        command,
        input=input_text,
        capture_output=input_text is None,
        check=True,
        text=True,
    )

    return completed.stdout if completed.stdout else ""


def read_project_version():
    content = PYPROJECT.read_text()
    match = re.search(r'(?m)^version = "([^"]+)"$', content)

    if not match:
        raise RuntimeError("Could not find project version in pyproject.toml")

    return match.group(1)


def parse_version(version):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)

    if not match:
        raise ValueError(f"Version must use MAJOR.MINOR.PATCH, got {version!r}")

    return tuple(int(part) for part in match.groups())


def bump_version(version, release):
    major, minor, patch = parse_version(version)

    if release == "major":
        return f"{major + 1}.0.0"

    if release == "minor":
        return f"{major}.{minor + 1}.0"

    if release == "patch":
        return f"{major}.{minor}.{patch + 1}"

    return version


def write_project_version(version, *, dry_run=False):
    content = PYPROJECT.read_text()
    updated = re.sub(r'(?m)^version = "[^"]+"$', f'version = "{version}"', content, count=1)

    if content == updated:
        raise RuntimeError("Could not update project version in pyproject.toml")

    if dry_run:
        print(colorize(f"Would update pyproject.toml version to {version}", "yellow"))
        return

    PYPROJECT.write_text(updated)


def ecr_login(region, registry, *, dry_run=False):
    if dry_run:
        print(
            colorize(
                f"+ aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {registry}",
                "cyan",
            )
        )
        return

    password = run(["aws", "ecr", "get-login-password", "--region", region])
    run(
        ["docker", "login", "--username", "AWS", "--password-stdin", registry],
        input_text=password,
    )


def print_publish_config_help(errors):
    lines = [
        colorize("Release configuration is incomplete.", "red"),
        "",
        colorize("Fix:", "bold"),
        "  1. Configure ECR settings in .env before publishing.",
        "  2. You can also pass them as shell environment variables or CLI flags.",
        "",
        colorize(".env setup:", "bold"),
        colorize("  AWS_REGION=us-east-1", "green"),
        colorize(
            "  ECR_REGISTRY=<aws-account-id>.dkr.ecr.us-east-1.amazonaws.com",
            "green",
        ),
        colorize("  ECR_REPOSITORY=<namespace>/<image-name>", "green"),
        "",
        colorize("Or pass flags:", "bold"),
        colorize("  uv run python scripts/release_image.py patch \\", "cyan"),
        colorize(
            "    --registry <aws-account-id>.dkr.ecr.us-east-1.amazonaws.com \\",
            "cyan",
        ),
        colorize("    --repository <namespace>/<image-name>", "cyan"),
        "",
        colorize("Problems found:", "bold"),
        *[colorize(f"  - {error}", "red") for error in errors],
        "",
        colorize("Preview without publishing:", "bold"),
        colorize("  uv run python scripts/release_image.py patch --dry-run", "cyan"),
        "",
    ]

    print("\n".join(lines), file=sys.stderr)


def validate_publish_config(args):
    errors = []

    if args.registry == DEFAULT_REGISTRY:
        errors.append("ECR registry is still using the public template value")

    if args.repository == DEFAULT_REPOSITORY:
        errors.append("ECR repository is still using the public template value")

    if errors:
        print_publish_config_help(errors)
        raise SystemExit(
            colorize(
                "Release failed: missing ECR registry/repository configuration", "red"
            )
        )


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Bump the app version, build the Docker image, and push version/latest tags to ECR."
    )
    parser.add_argument(
        "release",
        choices=["major", "minor", "patch", "current"],
        help="Version bump type. Use 'current' to publish the version already in pyproject.toml.",
    )
    parser.add_argument("--version", help="Explicit version to publish, for example 1.2.3.")
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", DEFAULT_REGION))
    parser.add_argument("--registry", default=os.environ.get("ECR_REGISTRY", DEFAULT_REGISTRY))
    parser.add_argument("--repository", default=os.environ.get("ECR_REPOSITORY", DEFAULT_REPOSITORY))
    parser.add_argument("--skip-login", action="store_true", help="Skip ECR docker login.")
    parser.add_argument("--no-push", action="store_true", help="Build and tag locally, but do not push.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without changing files or running Docker/AWS commands.")
    args = parser.parse_args()

    current_version = read_project_version()
    next_version = args.version or bump_version(current_version, args.release)
    parse_version(next_version)

    if not args.dry_run:
        validate_publish_config(args)

    if next_version != current_version:
        write_project_version(next_version, dry_run=args.dry_run)

    local_version_tag = f"{args.repository}:{next_version}"
    local_latest_tag = f"{args.repository}:latest"
    remote_version_tag = f"{args.registry}/{args.repository}:{next_version}"
    remote_latest_tag = f"{args.registry}/{args.repository}:latest"

    if not args.skip_login:
        ecr_login(args.region, args.registry, dry_run=args.dry_run)

    run(
        ["docker", "build", "-t", local_version_tag, "-t", local_latest_tag, "."],
        dry_run=args.dry_run,
    )
    run(["docker", "tag", local_version_tag, remote_version_tag], dry_run=args.dry_run)
    run(["docker", "tag", local_version_tag, remote_latest_tag], dry_run=args.dry_run)

    if not args.no_push:
        run(["docker", "push", remote_version_tag], dry_run=args.dry_run)
        run(["docker", "push", remote_latest_tag], dry_run=args.dry_run)

    print(colorize(f"Released {remote_version_tag}", "green"))
    print(colorize(f"Updated latest tag {remote_latest_tag}", "green"))


if __name__ == "__main__":
    main()
