"""Owner-device client: standard OpenSSH over a private network."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


def request(connection: dict, message: dict):
    host = connection["ssh_host"]
    if not isinstance(host, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", host):
        raise ValueError("Use a simple Host alias from ~/.ssh/config")
    # No remote shell command: authorized_keys must force the restricted endpoint.
    args = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=2", host]
    output = subprocess.run(args, input=json.dumps(message) + "\n", capture_output=True, text=True, timeout=45)
    try:
        response = json.loads(output.stdout)
    except ValueError as exc:
        raise ValueError("SSH endpoint did not return benchmark JSON; check the connection and forced command") from exc
    if output.returncode or response.get("ok") is not True:
        raise ValueError(response.get("error", "Remote request failed"))
    return response["result"]


def main():
    parser = argparse.ArgumentParser(description="Send a JSON request to the remote benchmark worker")
    parser.add_argument("--connection", type=Path, required=True)
    parser.add_argument("request", help="JSON object, or @path to a JSON request file")
    args = parser.parse_args()
    try:
        message = json.loads(Path(args.request[1:]).read_text() if args.request.startswith("@") else args.request)
        result = request(json.loads(args.connection.read_text()), message)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
