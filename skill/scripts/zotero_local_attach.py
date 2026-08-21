#!/usr/bin/env python3
"""Attach a local PDF through Zotero 10's authenticated Local API."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, unquote, urljoin, urlparse
from urllib.request import Request, build_opener


BASE = "http://127.0.0.1:23119"
API = f"{BASE}/api"
TIMEOUT = 300


class APIError(RuntimeError):
    def __init__(self, method: str, url: str, status: int, body: bytes, headers=None):
        self.method = method
        self.url = url
        self.status = status
        self.body = body
        self.headers = headers
        preview = body.decode("utf-8", "replace")[:500]
        super().__init__(f"{method} {url} returned HTTP {status}: {preview}")


def request(method: str, url: str, *, headers=None, data: bytes | None = None):
    req = Request(url, data=data, headers=headers or {}, method=method)
    try:
        with build_opener().open(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.headers, resp.read()
    except HTTPError as exc:
        raise APIError(method, url, exc.code, exc.read(), exc.headers) from exc
    except URLError as exc:
        raise RuntimeError(f"Cannot reach Zotero at {BASE}: {exc.reason}") from exc


def parse_json(body: bytes, context: str):
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{context} did not return valid JSON") from exc


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ZoteroLocal:
    def __init__(self, app_name: str):
        self.app_name = app_name
        self.server_id = ""
        self.api_key = os.environ.get("ZOTERO_LOCAL_API_KEY", "")

    def preflight(self):
        try:
            _, headers, _ = request("GET", f"{API}/")
        except APIError as exc:
            server_id = exc.headers.get("Zotero-Server-ID", "") if exc.headers else ""
            message = exc.body.decode("utf-8", "replace")
            if exc.status == 403 and "not enabled" in message.lower():
                raise RuntimeError(
                    "Zotero Local API is not enabled. Enable 'Allow other applications on "
                    "this computer to communicate with Zotero' in Settings > Advanced."
                ) from exc
            raise
        self.server_id = headers.get("Zotero-Server-ID", "")
        version = headers.get("X-Zotero-Version", "")
        if not self.server_id:
            raise RuntimeError("Zotero did not provide Zotero-Server-ID")
        try:
            major = int(version.split(".", 1)[0])
        except (ValueError, IndexError):
            major = 0
        if major < 10:
            raise RuntimeError(f"Zotero 10+ is required; running version is {version or 'unknown'}")

    def authorize(self):
        payload = json.dumps({"appName": self.app_name}).encode()
        headers = {
            "Content-Type": "application/json",
            "Zotero-Server-ID": self.server_id,
        }
        _, _, body = request("POST", f"{API}/local/authorize", headers=headers, data=payload)
        result = parse_json(body, "Local API authorization")
        key = result.get("key")
        if not isinstance(key, str) or not key:
            raise RuntimeError("Zotero authorization did not return an API key")
        self.api_key = key

    def read(self, path: str):
        headers = {"Zotero-Server-ID": self.server_id}
        return request("GET", f"{API}{path}", headers=headers)

    def write(self, method: str, path: str, *, headers=None, data: bytes | None = None):
        for _ in range(2):
            if not self.api_key:
                self.authorize()
            merged = {
                "Zotero-Server-ID": self.server_id,
                "Zotero-API-Key": self.api_key,
            }
            merged.update(headers or {})
            try:
                return request(method, f"{API}{path}", headers=merged, data=data)
            except APIError as exc:
                if exc.status != 401:
                    raise
                self.api_key = ""
        raise RuntimeError("Zotero Local API authorization was rejected twice")


def extract_created_key(result) -> str:
    bucket = result.get("successful") or result.get("success") or {}
    entry = bucket.get("0") or bucket.get(0)
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        key = entry.get("key") or entry.get("data", {}).get("key")
        if isinstance(key, str):
            return key
    failed = result.get("failed") or {}
    raise RuntimeError(f"Zotero did not create the attachment: {json.dumps(failed, ensure_ascii=False)}")


def storage_path_from_url(text: str) -> Path:
    parsed = urlparse(text.strip())
    if parsed.scheme != "file":
        raise RuntimeError(f"Zotero returned a non-file attachment URL: {text.strip()}")
    if parsed.netloc not in ("", "localhost"):
        raise RuntimeError(f"Unexpected host in Zotero file URL: {parsed.netloc}")
    return Path(unquote(parsed.path)).resolve()


def attach(args) -> dict:
    source = Path(args.file).expanduser().resolve()
    if not source.is_file():
        raise RuntimeError(f"Report PDF does not exist: {source}")
    if source.suffix.lower() != ".pdf":
        raise RuntimeError(f"Report must be a PDF: {source}")

    client = ZoteroLocal(args.app_name)
    client.preflight()

    _, _, body = client.read(f"/users/0/items/{args.source_attachment_key}")
    source_item = parse_json(body, "Source attachment lookup").get("data", {})
    if source_item.get("itemType") != "attachment":
        raise RuntimeError("The supplied source key is not an attachment")
    parent_key = source_item.get("parentItem")
    if not isinstance(parent_key, str) or not parent_key:
        raise RuntimeError("The source attachment has no parent item")

    # Zotero 10's Local API does not currently expose the Web API's
    # /items/new template endpoint, so construct the documented editable
    # attachment object directly.
    attachment = {
        "itemType": "attachment",
        "linkMode": "imported_file",
        "parentItem": parent_key,
        "title": args.title,
        "contentType": "application/pdf",
        "charset": "",
        "filename": source.name,
        "note": "",
        "tags": [],
        "relations": {},
        "md5": None,
        "mtime": None,
    }
    create_headers = {
        "Content-Type": "application/json",
        "Zotero-Write-Token": uuid.uuid4().hex,
    }
    _, _, body = client.write(
        "POST", "/users/0/items", headers=create_headers, data=json.dumps([attachment]).encode()
    )
    new_key = extract_created_key(parse_json(body, "Attachment creation"))

    digest = md5_file(source)
    size = source.stat().st_size
    mtime = int(source.stat().st_mtime * 1000)
    form = urlencode(
        {"md5": digest, "filename": source.name, "filesize": size, "mtime": mtime}
    ).encode()
    upload_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "If-None-Match": "*",
    }
    _, _, body = client.write(
        "POST", f"/users/0/items/{new_key}/file", headers=upload_headers, data=form
    )
    authorization = parse_json(body, "File upload authorization")

    if authorization.get("exists") != 1:
        upload_key = authorization.get("uploadKey")
        upload_url = authorization.get("url")
        if not isinstance(upload_key, str) or not upload_key or not isinstance(upload_url, str):
            raise RuntimeError("Zotero did not return a valid file upload authorization")
        content_type = authorization.get("contentType") or mimetypes.guess_type(source.name)[0]
        content_type = content_type or "application/octet-stream"
        raw_headers = {"Content-Type": content_type}
        status, _, _ = request(
            "POST", urljoin(BASE, upload_url), headers=raw_headers, data=source.read_bytes()
        )
        if status != 201:
            raise RuntimeError(f"Zotero file upload returned HTTP {status}, expected 201")

        register = urlencode({"upload": upload_key}).encode()
        status, _, _ = client.write(
            "POST", f"/users/0/items/{new_key}/file", headers=upload_headers, data=register
        )
        if status != 204:
            raise RuntimeError(f"Zotero upload registration returned HTTP {status}, expected 204")

    _, _, body = client.read(f"/users/0/items/{new_key}")
    saved = parse_json(body, "Created attachment verification").get("data", {})
    expected = {
        "itemType": "attachment",
        "parentItem": parent_key,
        "linkMode": "imported_file",
        "title": args.title,
        "contentType": "application/pdf",
        "filename": source.name,
    }
    mismatches = {key: [expected_value, saved.get(key)] for key, expected_value in expected.items()
                  if saved.get(key) != expected_value}
    if mismatches:
        raise RuntimeError(f"Created attachment fields did not verify: {mismatches}")

    _, _, body = client.read(f"/users/0/items/{new_key}/file/view/url")
    stored = storage_path_from_url(body.decode("utf-8", "replace"))
    if not stored.is_file():
        raise RuntimeError(f"Zotero storage file does not exist: {stored}")
    if stored.stat().st_size != size or md5_file(stored) != digest:
        raise RuntimeError("Zotero storage file differs from the uploaded report")

    return {
        "ok": True,
        "method": "zotero-local-api",
        "verified": True,
        "newAttachmentKey": new_key,
        "parentKey": parent_key,
        "storedPath": str(stored),
        "size": size,
        "md5": digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-attachment-key", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--app-name", default="Codex Paper Summary")
    args = parser.parse_args()
    try:
        result = attach(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
