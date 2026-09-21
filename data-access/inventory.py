#!/usr/bin/env python3
"""Collect a small read-only Linux host inventory. No credentials or network addresses."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import shutil
import subprocess


def command(arguments):
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=15, check=False)
        return {"exit_code": result.returncode, "stdout": result.stdout.strip()}
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"unavailable": type(exc).__name__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--host-id", required=True, help="A short alias chosen by the owner, e.g. ubuntu-01")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.data_root.expanduser().resolve(strict=True)
    disk = shutil.disk_usage(root)
    mem = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        if key in {"MemTotal", "MemAvailable"}:
            mem[key + "_bytes"] = int(value.split()[0]) * 1024
    report = {"schema_version": 1, "host_id": args.host_id, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "os": platform.freedesktop_os_release(), "kernel": platform.release(),
              "python": platform.python_version(), "cpu": command(["lscpu", "-J"]), "memory": mem,
              "gpu": command(["nvidia-smi", "--query-gpu=name,uuid,driver_version,memory.total,memory.free", "--format=csv,noheader,nounits"]),
              "data_root": str(root), "disk_bytes": {"total": disk.total, "used": disk.used, "free": disk.free},
              "data_filesystem": command(["findmnt", "--json", "--target", str(root), "--output", "TARGET,FSTYPE,OPTIONS"])}
    with args.out.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print("Inventory saved: " + str(args.out))


if __name__ == "__main__":
    main()
