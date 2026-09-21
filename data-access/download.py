#!/usr/bin/env python3
"""Download the selected Kaggle source archives; never extract, train, or submit."""
from __future__ import annotations

import argparse
from collections import Counter
import contextlib
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import threading
import time
import zipfile

HERE = Path(__file__).resolve().parent
GIB = 1024 ** 3


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest(path):
    content = path.read_bytes()
    manifest = json.loads(content)
    tasks = manifest.get("tasks", [])
    ids = [row.get("id") for row in tasks]
    if (manifest.get("schema_version") != 1 or len(tasks) != 60
            or any(not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", cid) for cid in ids)
            or len(set(ids)) != 60
            or Counter(row.get("tier") for row in tasks) != {"easy": 20, "medium": 20, "hard": 20}):
        raise ValueError("Manifest must contain exactly 60 unique competitions, 20 per tier")
    for row in tasks:
        if row.get("url") != "https://www.kaggle.com/competitions/" + row["id"]:
            raise ValueError("Competition URL disagrees with its ID")
    return manifest, hashlib.sha256(content).hexdigest()


def no_symlink(path):
    if path.is_symlink():
        raise ValueError("Refusing a symlink inside the managed archive directory")
    return path


def atomic_json(path, value):
    no_symlink(path)
    fd, temporary = tempfile.mkstemp(prefix=".receipt-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_receipt(path):
    no_symlink(path)
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def matches_receipt(archive, receipt, cid, manifest_hash, deep=False):
    no_symlink(archive)
    if (receipt.get("status") != "downloaded" or receipt.get("competition_id") != cid
            or receipt.get("manifest_sha256") != manifest_hash or not archive.is_file()):
        return False
    stat = archive.stat()
    if stat.st_size != receipt.get("bytes"):
        return False
    if deep:
        return sha256(archive) == receipt.get("sha256")
    return stat.st_mtime_ns == receipt.get("mtime_ns")


def inspect_archive(path, full_crc=False):
    no_symlink(path)
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if not entries:
            raise ValueError("Archive has no entries")
        if full_crc and archive.testzip() is not None:
            raise zipfile.BadZipFile("Archive CRC check failed")
        metadata = {"zip_entries": len(entries),
                    "declared_uncompressed_bytes": sum(row.file_size for row in entries),
                    "crc_checked": full_crc}
    metadata.update(bytes=path.stat().st_size, mtime_ns=path.stat().st_mtime_ns, sha256=sha256(path))
    return metadata


@contextlib.contextmanager
def quiet_sdk(archive=None):
    """Hide SDK errors containing signed URLs; print only safe byte progress."""
    output = sys.stdout
    stopped = threading.Event()
    def progress():
        while not stopped.wait(30):
            try:
                size = archive.stat().st_size if archive and archive.is_file() else 0
                print(f"  transfer active; {size / GIB:.2f} GiB currently on disk", file=output, flush=True)
            except OSError:
                pass
    thread = threading.Thread(target=progress, daemon=True) if archive else None
    with open(os.devnull, "w") as sink:
        try:
            if thread:
                thread.start()
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                yield
        finally:
            stopped.set()
            if thread:
                thread.join()


def get_api():
    with quiet_sdk():
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
    return api


def safe_error(exc):
    response = getattr(exc, "response", None)
    http = getattr(response, "status_code", None)
    if http == 401:
        status = "authentication_required"
    elif http == 403:
        status = "access_denied_check_rules"
    elif http == 404:
        status = "not_found_or_unavailable"
    elif http == 429:
        status = "rate_limited"
    elif getattr(exc, "errno", None) == errno.ENOSPC:
        status = "disk_full"
    elif isinstance(exc, (zipfile.BadZipFile, ValueError)):
        status = "archive_validation_failed"
    else:
        status = "download_failed"
    return {"status": status, "exception_type": type(exc).__name__, "http_status": http}


def download_one(api, task, directory, manifest_hash, reserve_bytes, attempts=2, full_crc=False):
    cid = task["id"]
    no_symlink(directory)
    directory.mkdir(exist_ok=True)
    archive = no_symlink(directory / (cid + ".zip"))
    marker = no_symlink(Path(str(archive) + ".kaggle-partial"))
    receipt_path = no_symlink(directory / "receipt.json")
    previous = read_receipt(receipt_path)
    base = {"competition_id": cid, "tier": task["tier"], "url": task["url"],
            "rules_url": task["url"] + "/rules", "manifest_sha256": manifest_hash,
            "updated_at_utc": now(), "archive": f"source-archives/{cid}/{cid}.zip"}
    if matches_receipt(archive, previous, cid, manifest_hash) and not marker.exists():
        return {**previous, "last_action": "skipped_existing_size_and_mtime_match"}
    if previous.get("status") == "downloaded" and archive.exists():
        # Preserve a changed completed archive. An unfinished download has no successful receipt.
        saved = directory / (cid + ".changed-" + str(time.time_ns()) + ".zip")
        archive.rename(saved)
        atomic_json(Path(str(saved) + ".receipt.json"), previous)
        if marker.exists():
            marker.rename(Path(str(saved) + ".kaggle-partial"))
    for attempt in range(1, attempts + 1):
        if shutil.disk_usage(directory).free < reserve_bytes:
            result = {**base, "status": "insufficient_free_space", "attempts": attempt - 1}
            atomic_json(receipt_path, result)
            return result
        print(f"  download attempt {attempt}/{attempts}", flush=True)
        try:
            with quiet_sdk(archive):
                api.competition_download_files(cid, path=str(directory), force=False, quiet=True)
            print("  checking ZIP structure and calculating SHA-256", flush=True)
            details = inspect_archive(archive, full_crc)
            if marker.exists():
                raise ValueError("Kaggle still reports a partial download")
            result = {**base, **details, "status": "downloaded", "attempts": attempt,
                      "updated_at_utc": now(), "last_action": "downloaded_and_hashed",
                      "verification_scope": "local SHA-256 and ZIP structure; not a Kaggle-published checksum or task admission"}
            atomic_json(receipt_path, result)
            return result
        except (Exception, SystemExit) as exc:
            error = safe_error(exc)
            result = {**base, **error, "attempts": attempt, "updated_at_utc": now()}
            atomic_json(receipt_path, result)
            if error["status"] in {"authentication_required", "access_denied_check_rules", "not_found_or_unavailable", "disk_full"}:
                return result
            if error["status"] == "archive_validation_failed" and archive.exists() and not marker.exists():
                archive.rename(directory / (cid + ".invalid-" + str(time.time_ns()) + ".zip"))
            if attempt < attempts:
                delay = 60 if error["status"] == "rate_limited" else 10
                print(f"  {error['status']}; retrying in {delay}s", flush=True)
                time.sleep(delay)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=HERE / "competitions.json")
    parser.add_argument("--root", type=Path, help="Existing directory on the large data disk")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--plan", action="store_true", help="List tasks without credentials or network")
    action.add_argument("--download", action="store_true")
    action.add_argument("--verify", action="store_true", help="Offline SHA-256 verification against download receipts")
    parser.add_argument("--tier", choices=["easy", "medium", "hard"])
    parser.add_argument("--only", nargs="+", help="Exact selected competition IDs")
    parser.add_argument("--reserve-gib", type=float, default=20, help="Minimum free space checked before each attempt; not a total capacity estimate")
    parser.add_argument("--attempts", type=int, default=2, help="Outer attempts; the Kaggle client also retries transfers")
    parser.add_argument("--full-crc", action="store_true", help="Also decompress internally for ZIP CRC checks; does not extract files")
    args = parser.parse_args(argv)
    manifest, manifest_hash = load_manifest(args.manifest)
    if args.attempts < 1 or args.attempts > 5 or not (args.reserve_gib >= 0):
        parser.error("Attempts must be 1..5 and reserve-gib must be nonnegative")
    known = {row["id"] for row in manifest["tasks"]}
    if args.only and not set(args.only) <= known:
        parser.error("--only contains an ID outside the selected 60 competitions")
    tasks = [row for row in manifest["tasks"] if (not args.tier or row["tier"] == args.tier)
             and (not args.only or row["id"] in args.only)]
    if not tasks:
        parser.error("The requested filters select no competitions")
    if args.plan:
        for row in tasks:
            print(f"{row['tier']:6} {row['id']} {row['url']}/rules")
        print(f"Selected: {len(tasks)} competitions. No downloads started.")
        return 0
    if not args.root or not args.root.expanduser().is_dir():
        parser.error("--root must be an existing directory on your selected data disk")
    root = args.root.expanduser().resolve()
    os.umask(0o077)
    archives = no_symlink(root / "source-archives")
    reports = no_symlink(root / "download-reports")
    archives.mkdir(exist_ok=True)
    reports.mkdir(exist_ok=True)
    lock_path = no_symlink(root / ".download.lock")
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("Another downloader/verifier is already using this root")
        api = None
        if args.download:
            try:
                api = get_api()
            except (Exception, SystemExit):
                print("Kaggle authentication failed. Run .venv/bin/kaggle auth login; do not share tokens.", file=sys.stderr)
                return 2
        report = {"schema_version": 1, "manifest_sha256": manifest_hash, "started_at_utc": now(),
                  "operation": "download" if args.download else "verify", "requested_task_count": len(tasks),
                  "records": [], "all_requested_succeeded": False}
        report_path = reports / ("download-summary.json" if args.download else "verification-summary.json")
        atomic_json(report_path, report)
        try:
            for index, task in enumerate(tasks, 1):
                cid = task["id"]
                print(f"[{index}/{len(tasks)}] {task['tier']} / {cid}", flush=True)
                directory = no_symlink(archives / cid)
                if args.download:
                    result = download_one(api, task, directory, manifest_hash,
                                          args.reserve_gib * GIB, args.attempts, args.full_crc)
                else:
                    receipt = read_receipt(directory / "receipt.json")
                    archive = directory / (cid + ".zip")
                    good = (not no_symlink(Path(str(archive) + ".kaggle-partial")).exists()
                            and matches_receipt(archive, receipt, cid, manifest_hash, deep=True))
                    if good and args.full_crc:
                        try:
                            with zipfile.ZipFile(archive) as zf:
                                good = zf.testzip() is None
                        except (OSError, ValueError, zipfile.BadZipFile):
                            good = False
                    result = {"competition_id": cid, "status": "verified" if good else "missing_or_changed",
                              "crc_checked": bool(good and args.full_crc), "updated_at_utc": now()}
                report["records"].append(result)
                report["updated_at_utc"] = now()
                atomic_json(report_path, report)
                print("  " + result["status"], flush=True)
                if result["status"] == "access_denied_check_rules":
                    print("  Review access and rules: " + task["url"] + "/rules", flush=True)
                if result["status"] in {"authentication_required", "disk_full", "insufficient_free_space"}:
                    break
        except KeyboardInterrupt:
            report["interrupted"] = True
            print("Interrupted. Keep partial files and rerun the same command to continue.", flush=True)
        finally:
            report["finished_at_utc"] = now()
            report["all_requested_succeeded"] = (len(report["records"]) == len(tasks)
                and all(row["status"] in {"downloaded", "verified"} for row in report["records"]))
            atomic_json(report_path, report)
            print("Report: " + str(report_path), flush=True)
        return 0 if report["all_requested_succeeded"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"Local setup error ({type(error).__name__}); check paths, permissions and free disk space.", file=sys.stderr)
        raise SystemExit(2)
