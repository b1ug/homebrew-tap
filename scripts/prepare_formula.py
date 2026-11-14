#!/usr/bin/env python3
"""Verify a public nb1 release and prepare a new local Formula review directory."""

import argparse
import datetime as dt
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

REPOSITORY = "b1ug/nb1"
API = "https://api.github.com/repos/" + REPOSITORY
MAX_INPUT = 65536
MAX_METADATA = 8 * 1024 * 1024
MAX_ARCHIVE = 32 * 1024 * 1024
MAX_TAR = 128 * 1024 * 1024
MAX_MEMBER = 32 * 1024 * 1024
MAX_ENTRIES = 10000
RENDERER = "packaging/homebrew/render_formula.py"
TEMPLATE = "packaging/homebrew/nb1.rb.in"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate JSON field: " + key)
        result[key] = value
    return result


def decode(data):
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda value: require(False, "invalid JSON number"))
    except RecursionError as error:
        raise ValueError("JSON nesting is too deep") from error
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        require(depth <= 64, "JSON nesting exceeds 64 levels")
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
    return value


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


class Redirects(urllib.request.HTTPRedirectHandler):
    def __init__(self, permitted):
        self.permitted = permitted

    def redirect_request(self, request, fp, code, message, headers, url):
        require(url in self.permitted, "redirect outside the exact official archive URLs")
        return super().redirect_request(request, fp, code, message, headers, url)


class PublicHTTP:
    """Unauthenticated, bounded GETs; no tokens, netrc, proxies, or retries."""
    def __init__(self, archive_url, codeload_url):
        self.archive_urls = {archive_url, codeload_url}
        self.deadline = time.monotonic() + 180

    def __call__(self, url, limit):
        is_api = url == API or url.startswith(API + "/")
        require(is_api or url in self.archive_urls, "URL outside the official repository")
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), Redirects(set() if is_api else self.archive_urls))
        request = urllib.request.Request(url, headers={
            "User-Agent": "nb1-tap-release-preparation", "Accept-Encoding": "identity",
            "Accept": "application/vnd.github+json" if is_api else "application/octet-stream",
            "X-GitHub-Api-Version": "2026-03-10",
        })
        remaining = self.deadline - time.monotonic()
        require(remaining > 0, "verification network budget expired")
        with opener.open(request, timeout=min(20, remaining)) as response:
            require(response.status == 200, "expected HTTP 200")
            size = response.headers.get("Content-Length")
            if size is not None:
                require(size.isdigit() and int(size) <= limit, "response exceeds size limit")
            chunks, total = [], 0
            while True:
                require(time.monotonic() < self.deadline, "verification network budget expired")
                block = response.read(min(65536, limit + 1 - total))
                if not block:
                    break
                chunks.append(block)
                total += len(block)
                require(total <= limit, "response exceeds size limit")
            return b"".join(chunks)


def safe_path(value):
    require(isinstance(value, str) and value and "\0" not in value and "\\" not in value,
            "unsafe archive/tree path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and all(part not in {"", ".", ".."} for part in value.rstrip("/").split("/")),
            "unsafe archive/tree path")
    return path


def verify_archive(raw, expected, commit):
    require(len(raw) <= MAX_ARCHIVE, "source archive exceeds size limit")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as compressed:
            expanded = compressed.read(MAX_TAR + 1)
    except (OSError, EOFError) as error:
        raise ValueError("invalid gzip source archive") from error
    require(len(expanded) <= MAX_TAR, "expanded archive exceeds size limit")
    selected, seen, roots = {}, set(), set()
    with tarfile.open(fileobj=io.BytesIO(expanded), mode="r:") as archive:
        if archive.pax_headers.get("comment"):
            require(archive.pax_headers["comment"] == commit, "archive commit comment mismatch")
        for index, member in enumerate(archive):
            require(index < MAX_ENTRIES, "too many archive entries")
            path = safe_path(member.name)
            roots.add(path.parts[0])
            require(len(roots) == 1, "archive must have one source root")
            require(member.isdir() or member.isfile(), "archive links and special entries are not allowed")
            if member.isdir():
                continue
            require(len(path.parts) > 1, "file outside the source root")
            relative = str(PurePosixPath(*path.parts[1:]))
            require(relative not in seen and relative in expected, "duplicate or unexpected archive file: " + relative)
            require(0 <= member.size <= MAX_MEMBER and not member.mode & 0o7000, "unsafe archive file size/mode")
            content = archive.extractfile(member).read(MAX_MEMBER + 1)
            require(len(content) == member.size, "truncated archive file")
            entry = expected[relative]
            require(git_blob(content) == entry["sha"], "archive/tree content mismatch: " + relative)
            require(bool(member.mode & 0o111) == (entry["mode"] == "100755"), "archive/tree mode mismatch")
            seen.add(relative)
            if relative in {RENDERER, TEMPLATE}:
                selected[relative] = content
    require(seen == set(expected), "archive does not contain the complete verified source tree")
    require(set(selected) == {RENDERER, TEMPLATE}, "release has no supported renderer/template")
    return selected, len(expanded)


def child_environment():
    result = {"PATH": os.defpath, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    if "SYSTEMROOT" in os.environ:
        result["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return result


def check_ruby(path):
    ruby = shutil.which("ruby")
    require(ruby is not None, "Ruby is required for the syntax check; no installation is attempted")
    result = subprocess.run([ruby, "--disable-gems", "-c", str(path)], capture_output=True,
                            text=True, timeout=20, env=child_environment())
    require(result.returncode == 0, "Ruby syntax check failed: " + result.stderr[-2000:])


def prepare(value, output, fetch=None):
    # Only network-routing safety is checked here. The verified upstream
    # renderer remains the authority for SemVer, version floor and Formula rules.
    require(isinstance(value, dict) and value.get("fixture_only") is False, "real release input is required")
    version = value.get("version")
    require(isinstance(version, str) and re.fullmatch(r"[0-9A-Za-z.-]{1,128}", version), "invalid tag path component")
    tag = "v" + version
    source_url = "https://github.com/" + REPOSITORY + "/archive/refs/tags/" + tag + ".tar.gz"
    require(value.get("source_url") == source_url, "source_url must be the exact official tag archive")
    require(sha(value.get("source_commit")), "source_commit must be an explicit lowercase commit SHA")
    require(isinstance(value.get("source_sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", value["source_sha256"]),
            "source_sha256 must be an explicit lowercase SHA-256")
    output = Path(output)
    require(output.name not in {"", ".", ".."}, "an explicit new output directory is required")
    output = output.parent.resolve(strict=True) / output.name
    require(not os.path.lexists(output), "output already exists; it will not be overwritten")
    fetch = fetch or PublicHTTP(source_url, "https://codeload.github.com/" + REPOSITORY + "/tar.gz/refs/tags/" + tag)
    evidence = []

    def metadata(path):
        url = API + path
        data = fetch(url, MAX_METADATA)
        require(len(data) <= MAX_METADATA, "metadata exceeds size limit")
        evidence.append({"url": url, "sha256": digest(data)})
        answer = decode(data)
        require(isinstance(answer, dict), "metadata must be an object")
        return answer

    repo = metadata("")
    require(repo.get("full_name") == REPOSITORY and repo.get("private") is False, "upstream must be the public official repository")

    def release():
        answer = metadata("/releases/tags/" + tag)
        require(answer.get("tag_name") == tag and answer.get("draft") is False,
                "a published Release for the exact tag is required")
        require(type(answer.get("id")) is int and answer["id"] > 0 and type(answer.get("prerelease")) is bool,
                "invalid release metadata")
        require(answer.get("html_url") == "https://github.com/" + REPOSITORY + "/releases/tag/" + tag,
                "release belongs to another repository/tag")
        stamp = answer.get("published_at")
        require(isinstance(stamp, str) and dt.datetime.fromisoformat(stamp.replace("Z", "+00:00")).tzinfo is not None,
                "release is not published")
        return {key: answer.get(key) for key in ("id", "tag_name", "published_at", "prerelease", "immutable")}

    def resolve_tag():
        reference = metadata("/git/ref/tags/" + tag)
        require(reference.get("ref") == "refs/tags/" + tag, "tag reference mismatch")
        obj, visited, chain = reference.get("object"), set(), []
        for depth in range(9):
            require(isinstance(obj, dict) and sha(obj.get("sha")), "invalid tag object")
            chain.append({"type": obj.get("type"), "sha": obj["sha"]})
            if obj.get("type") == "commit":
                return obj["sha"], chain
            require(obj.get("type") == "tag" and obj["sha"] not in visited and depth < 8, "unsupported/cyclic tag chain")
            visited.add(obj["sha"])
            annotated = metadata("/git/tags/" + obj["sha"])
            require(annotated.get("sha") == obj["sha"] and (depth != 0 or annotated.get("tag") == tag), "annotated tag mismatch")
            obj = annotated.get("object")
        raise ValueError("tag chain too deep")

    published = release()
    resolved_commit, tag_objects = resolve_tag()
    require(resolved_commit == value["source_commit"], "tag/commit mismatch")
    commit = metadata("/git/commits/" + value["source_commit"])
    require(commit.get("sha") == value["source_commit"] and isinstance(commit.get("tree"), dict) and sha(commit["tree"].get("sha")), "commit metadata mismatch")
    tree_sha = commit["tree"]["sha"]
    tree = metadata("/git/trees/" + tree_sha + "?recursive=1")
    require(tree.get("sha") == tree_sha and tree.get("truncated") is False and isinstance(tree.get("tree"), list), "incomplete source tree")
    require(len(tree["tree"]) <= MAX_ENTRIES, "source tree exceeds entry limit")
    expected = {}
    for entry in tree["tree"]:
        require(isinstance(entry, dict), "invalid tree entry")
        path = str(safe_path(entry.get("path")))
        if entry.get("type") == "tree":
            continue
        require(entry.get("type") == "blob" and entry.get("mode") in {"100644", "100755"} and sha(entry.get("sha")),
                "source links/submodules are not supported")
        require(path not in expected, "duplicate tree path")
        expected[path] = entry
    raw = fetch(source_url, MAX_ARCHIVE)
    require(digest(raw) == value["source_sha256"], "archive SHA-256 mismatch")
    sources, expanded_size = verify_archive(raw, expected, value["source_commit"])
    require(resolve_tag() == (value["source_commit"], tag_objects) and release() == published, "release/tag changed during verification")

    with tempfile.TemporaryDirectory(prefix="nb1-tap-") as temporary:
        temporary = Path(temporary)
        for name, data in sources.items():
            (temporary / Path(name).name).write_bytes(data)
        source_input, candidate = temporary / "release-input.json", temporary / "candidate.rb"
        source_input.write_bytes((json.dumps(value, sort_keys=True) + "\n").encode("utf-8"))
        result = subprocess.run([sys.executable, "-I", "-B", str(temporary / "render_formula.py"),
                                 "--input", str(source_input), "--out", str(candidate)], cwd=temporary,
                                capture_output=True, text=True, timeout=30, env=child_environment())
        require(result.returncode == 0 and candidate.is_file() and not candidate.is_symlink(), "upstream renderer rejected input: " + result.stderr[-2000:])
        require(0 < candidate.stat().st_size <= MAX_INPUT, "rendered Formula is empty or exceeds size limit")
        formula = candidate.read_bytes()
        check_ruby(candidate)
    provenance = {
        "schema_version": 1, "repository": REPOSITORY, "tag": tag, "tag_objects": tag_objects, "release": published,
        "source_commit": value["source_commit"], "source_tree": tree_sha,
        "archive": {"url": source_url, "sha256": digest(raw), "bytes": len(raw), "tar_bytes": expanded_size, "files": len(expected)},
        "upstream_files": {name: {"git_blob": expected[name]["sha"], "sha256": digest(data)} for name, data in sources.items()},
        "formula_sha256": digest(formula), "release_input": value, "metadata_evidence": evidence,
        "generator_sha256": digest(Path(__file__).read_bytes()), "python": sys.version.split()[0],
        "ruby_syntax_checked": True, "prepared_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "homebrew_installed": False, "service_installed": False, "published": False,
    }
    # Reserve a fresh directory exclusively. Errors remove only our new output;
    # no existing tap, Formula, input or user configuration is replaced.
    output.mkdir(mode=0o700)
    try:
        (output / "Formula").mkdir()
        (output / "Formula/nb1.rb").write_bytes(formula)
        (output / "provenance.json").write_bytes((json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    except BaseException:
        shutil.rmtree(output)
        raise
    return provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.input.open("rb") as stream:
            raw = stream.read(MAX_INPUT + 1)
        require(len(raw) <= MAX_INPUT, "release input exceeds 64 KiB")
        result = prepare(decode(raw), args.output_dir)
        print(json.dumps({"prepared": True, "tag": result["tag"], "formula_sha256": result["formula_sha256"], "published": False}))
    except (OSError, ValueError, TypeError, tarfile.TarError, subprocess.SubprocessError) as error:
        parser.exit(1, "No Formula prepared: " + str(error) + "\n")


if __name__ == "__main__":
    main()
