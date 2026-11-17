"""Offline release-verification tests; all releases and archives are synthetic."""
import copy
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prepare_formula", ROOT / "scripts/prepare_formula.py")
producer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(producer)
COMMIT = hashlib.sha1(b"synthetic commit, not an upstream release").hexdigest()
TREE = hashlib.sha1(b"synthetic tree").hexdigest()
TAG_OBJECT = hashlib.sha1(b"synthetic annotated tag").hexdigest()
REWRITTEN_TAG = hashlib.sha1(b"rewritten annotation, same commit").hexdigest()
VERSION = "1.2.3"
# This tiny test double is not the product renderer or an installable Formula.
# It proves that the producer executes the verified upstream renderer instead
# of embedding Formula/SemVer rules. An optional integration uses real sources.
RENDERER = b'''import argparse, json, os, pathlib, re
p = argparse.ArgumentParser()
p.add_argument("--input", required=True); p.add_argument("--out", required=True)
a = p.parse_args(); v = json.loads(pathlib.Path(a.input).read_text())
assert not any(k in os.environ for k in ("GITHUB_TOKEN", "GH_TOKEN", "PYTHONPATH", "RUBYOPT"))
if not re.fullmatch(r"(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)", v["version"]): raise SystemExit("bad SemVer")
if tuple(map(int, v["version"].split("."))) <= (0, 0, 1): raise SystemExit("historical release")
if v["min_macos"] not in ("sequoia", "tahoe"): raise SystemExit("bad macOS")
template = pathlib.Path(__file__).with_name("nb1.rb.in").read_text()
pathlib.Path(a.out).write_text(template.replace("@VERSION@", v["version"]))
'''
TEMPLATE = b'# SYNTHETIC TEST ONLY, NOT A RELEASE\nclass Nb1 < Formula\n  version "@VERSION@"\nend\n'


def archive(files, extra=None):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        for path, data in files.items():
            member = tarfile.TarInfo("synthetic-root/" + path)
            member.size, member.mode = len(data), 0o644
            tar.addfile(member, io.BytesIO(data))
        if extra:
            member, data = extra
            tar.addfile(member, io.BytesIO(data) if data is not None else None)
    return gzip.compress(stream.getvalue(), mtime=0)


class ReleaseFixture:
    def __init__(self, version=VERSION, files=None):
        self.version, self.calls, self.tag_reads = version, [], 0
        self.files = files or {producer.RENDERER: RENDERER, producer.TEMPLATE: TEMPLATE, "README.md": b"synthetic source\n"}
        self.raw = archive(self.files)
        self.input = {"schema_version": 1, "fixture_only": False, "version": version,
                      "source_url": "https://github.com/b1ug/nb1/archive/refs/tags/v" + version + ".tar.gz",
                      "source_sha256": producer.digest(self.raw), "source_commit": COMMIT,
                      "min_macos": "sequoia", "components": "nb1-only"}
        self.repo = {"full_name": "b1ug/nb1", "private": False}
        self.release = {"id": 42, "tag_name": "v" + version, "draft": False, "prerelease": False,
                        "published_at": "2026-01-01T00:00:00Z", "immutable": False,
                        "html_url": "https://github.com/b1ug/nb1/releases/tag/v" + version}
        self.ref = {"ref": "refs/tags/v" + version, "object": {"type": "commit", "sha": COMMIT}}
        self.tree = {"sha": TREE, "truncated": False, "tree": [
            {"path": p, "sha": producer.git_blob(v), "type": "blob", "mode": "100644", "size": len(v)}
            for p, v in self.files.items()]}
        self.changed_tag = False
        self.changed_annotation = False

    def fetch(self, url, limit):
        self.calls.append(url)
        if url == self.input["source_url"]:
            return self.raw
        path = url.removeprefix(producer.API)
        if path == "":
            value = self.repo
        elif path == "/releases/tags/v" + self.version:
            value = self.release
        elif path == "/git/ref/tags/v" + self.version:
            self.tag_reads += 1
            value = copy.deepcopy(self.ref)
            if self.changed_tag and self.tag_reads > 1:
                value["object"] = {"type": "commit", "sha": hashlib.sha1(b"moved tag").hexdigest()}
            if self.changed_annotation and self.tag_reads > 1:
                value["object"] = {"type": "tag", "sha": REWRITTEN_TAG}
        elif path in {"/git/tags/" + TAG_OBJECT, "/git/tags/" + REWRITTEN_TAG}:
            value = {"sha": path.rsplit("/", 1)[1], "tag": "v" + self.version, "object": {"type": "commit", "sha": COMMIT}}
        elif path == "/git/commits/" + COMMIT:
            value = {"sha": COMMIT, "tree": {"sha": TREE}}
        elif path == "/git/trees/" + TREE + "?recursive=1":
            value = self.tree
        else:
            raise AssertionError("unexpected URL: " + url)
        return json.dumps(value).encode()

    def replace_archive(self, files, extra=None):
        self.raw = archive(files, extra)
        self.input["source_sha256"] = producer.digest(self.raw)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.out = Path(self.temporary.name) / "review"
        self.network = mock.patch.object(socket, "create_connection", side_effect=AssertionError("offline test attempted network"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def reject(self, fixture, expected=ValueError):
        with self.assertRaises(expected):
            producer.prepare(fixture.input, self.out, fixture.fetch)
        self.assertFalse(self.out.exists(), "failure left an output/Formula behind")

    def test_verified_lightweight_release_calls_upstream_renderer_and_records_provenance(self):
        fixture = ReleaseFixture()
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "not-a-real-token", "GH_TOKEN": "not-a-real-token", "PYTHONPATH": "not-used", "RUBYOPT": "not-used"}):
            result = producer.prepare(fixture.input, self.out, fixture.fetch)
        rendered = (self.out / "Formula/nb1.rb").read_bytes()
        self.assertIn(b'SYNTHETIC TEST ONLY', rendered)
        self.assertIn(b'version "1.2.3"', rendered)
        self.assertEqual(result["formula_sha256"], producer.digest(rendered))
        self.assertEqual(result["source_commit"], COMMIT)
        self.assertEqual(result["source_tree"], TREE)
        self.assertEqual(fixture.tag_reads, 2)
        self.assertTrue(result["ruby_syntax_checked"])
        self.assertFalse(result["published"])
        self.assertEqual(json.loads((self.out / "provenance.json").read_text()), result)

    def test_annotated_tag_is_peeled_to_the_explicit_commit(self):
        fixture = ReleaseFixture()
        fixture.ref["object"] = {"type": "tag", "sha": TAG_OBJECT}
        producer.prepare(fixture.input, self.out, fixture.fetch)
        self.assertEqual(fixture.calls.count(producer.API + "/git/tags/" + TAG_OBJECT), 2)

    def test_published_release_and_public_repository_are_required(self):
        for mutate in [lambda f: f.repo.update(private=True), lambda f: f.release.update(draft=True),
                       lambda f: f.release.update(published_at=None), lambda f: f.release.update(tag_name="v9.9.9")]:
            with self.subTest(mutate=mutate):
                fixture = ReleaseFixture(); mutate(fixture); self.reject(fixture)

    def test_tag_commit_mismatch_and_moving_tag_never_write(self):
        fixture = ReleaseFixture(); fixture.input["source_commit"] = hashlib.sha1(b"wrong commit").hexdigest(); self.reject(fixture)
        fixture = ReleaseFixture(); fixture.changed_tag = True; self.reject(fixture)
        fixture = ReleaseFixture(); fixture.ref["object"] = {"type": "tag", "sha": TAG_OBJECT}
        fixture.changed_annotation = True; self.reject(fixture)

    def test_official_url_and_real_input_are_required_before_network(self):
        for value in ["https://github.com/b1ug/nb1/archive/refs/heads/main.tar.gz", "https://example.com/nb1.tar.gz", "file:///tmp/nb1.tar.gz"]:
            fixture = ReleaseFixture(); fixture.input["source_url"] = value; self.reject(fixture); self.assertEqual(fixture.calls, [])
        fixture = ReleaseFixture(); fixture.input["fixture_only"] = True; self.reject(fixture); self.assertEqual(fixture.calls, [])

    def test_archive_checksum_and_commit_tree_tampering_are_rejected(self):
        fixture = ReleaseFixture(); fixture.input["source_sha256"] = producer.digest(b"wrong archive"); self.reject(fixture)
        fixture = ReleaseFixture(); changed = dict(fixture.files); changed[producer.RENDERER] = b'raise SystemExit("must never run")\n'
        fixture.replace_archive(changed); self.reject(fixture)

    def test_archive_missing_renderer_and_incomplete_tree_are_rejected(self):
        fixture = ReleaseFixture(); fixture.tree["truncated"] = True; self.reject(fixture)
        files = {producer.TEMPLATE: TEMPLATE, "README.md": b"fixture"}
        self.reject(ReleaseFixture(files=files))

    def test_links_traversal_and_duplicate_files_are_rejected(self):
        for name, kind in [("synthetic-root/../../escape", "file"), ("synthetic-root/link", "symlink"),
                           ("synthetic-root/README.md", "file")]:
            fixture = ReleaseFixture(); member = tarfile.TarInfo(name)
            member.mode, member.size = 0o644, 1
            data = b"x"
            if kind == "symlink":
                member.type, member.linkname, member.size, data = tarfile.SYMTYPE, "/tmp/foreign", 0, None
            fixture.replace_archive(fixture.files, (member, data)); self.reject(fixture)

    def test_compressed_and_expanded_size_limits_are_enforced(self):
        fixture = ReleaseFixture()
        with mock.patch.object(producer, "MAX_ARCHIVE", len(fixture.raw) - 1): self.reject(fixture)
        with mock.patch.object(producer, "MAX_TAR", 20): self.reject(ReleaseFixture())

    def test_invalid_or_truncated_gzip_leaves_no_output(self):
        for raw in [b"not a gzip archive", ReleaseFixture().raw[:20]]:
            fixture = ReleaseFixture(); fixture.raw = raw; fixture.input["source_sha256"] = producer.digest(raw)
            self.reject(fixture)

    def test_upstream_semver_floor_and_validation_failure_leave_no_output(self):
        self.reject(ReleaseFixture(version="0.0.1"))
        fixture = ReleaseFixture(); fixture.input["min_macos"] = "unknown"; self.reject(fixture)

    def test_renderer_failure_and_invalid_ruby_leave_no_output(self):
        self.reject(ReleaseFixture(files={producer.RENDERER: b'raise SystemExit("fixture failure")\n', producer.TEMPLATE: TEMPLATE}))
        self.reject(ReleaseFixture(files={producer.RENDERER: RENDERER, producer.TEMPLATE: b"class Nb1 < Formula\n  def\n"}))

    def test_existing_output_is_not_changed_or_fetched(self):
        self.out.mkdir(); sentinel = self.out / "keep.txt"; sentinel.write_text("keep")
        fixture = ReleaseFixture()
        with self.assertRaises(ValueError): producer.prepare(fixture.input, self.out, fixture.fetch)
        self.assertEqual(sentinel.read_text(), "keep")
        self.assertEqual(fixture.calls, [])

    def test_local_publication_failure_rolls_back_only_the_new_output(self):
        fixture = ReleaseFixture(); original = Path.write_bytes
        def fail_provenance(path, data):
            if path == self.out.resolve() / "provenance.json": raise OSError("synthetic disk failure")
            return original(path, data)
        with mock.patch.object(Path, "write_bytes", fail_provenance): self.reject(fixture, OSError)

    def test_duplicate_json_and_missing_output_cli_are_rejected(self):
        with self.assertRaises(ValueError): producer.decode(b'{"version":"1.2.3","version":"2.3.4"}')
        with self.assertRaises(ValueError): producer.decode(b"[" * 10000 + b"0" + b"]" * 10000)
        result = subprocess.run([sys.executable, str(ROOT / "scripts/prepare_formula.py"), "--input", "missing.json"], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.out.exists())

    def test_committed_production_formula_has_matching_verified_release_record(self):
        value = json.loads((ROOT / "releases/nb1-0.1.0.json").read_text())
        provenance = json.loads((ROOT / "releases/nb1-0.1.0.provenance.json").read_text())
        formula = (ROOT / "Formula/nb1.rb").read_bytes()
        self.assertIs(value["fixture_only"], False)
        self.assertEqual(provenance["release_input"], value)
        self.assertEqual(provenance["formula_sha256"], producer.digest(formula))
        self.assertEqual(provenance["source_commit"], value["source_commit"])
        self.assertEqual(provenance["tag"], "v" + value["version"])
        self.assertIs(provenance["release"]["prerelease"], False)
        self.assertIn(value["source_sha256"].encode(), formula)
        self.assertIn(value["source_url"].encode(), formula)
        self.assertIn(value["source_commit"].encode(), formula)
        producer.check_ruby(ROOT / "Formula/nb1.rb")

    @unittest.skipUnless(os.environ.get("NB1_TAP_TEST_UPSTREAM"), "optional real renderer integration")
    def test_actual_nb1_renderer_and_template_integration(self):
        source = Path(os.environ["NB1_TAP_TEST_UPSTREAM"])
        fixture = ReleaseFixture(files={name: (source / name).read_bytes() for name in [producer.RENDERER, producer.TEMPLATE]})
        producer.prepare(fixture.input, self.out, fixture.fetch)
        text = (self.out / "Formula/nb1.rb").read_text()
        self.assertIn('Gem::Version.new("1.27.4")', text)
        self.assertIn('class Nb1 < Formula', text)


class NetworkBoundaryTests(unittest.TestCase):
    def test_unexpected_redirects_are_rejected_before_following(self):
        handler = producer.Redirects({"https://codeload.github.com/b1ug/nb1/tar.gz/refs/tags/v1.2.3"})
        for target in ["http://github.com/b1ug/nb1/archive.tar.gz", "https://example.com/archive", "https://github.com/other/nb1/archive.tar.gz"]:
            with self.assertRaises(ValueError): handler.redirect_request(None, None, 302, "", {}, target)

    def test_public_get_does_not_forward_tokens_and_checks_response_size(self):
        class Response:
            status, headers = 200, {"Content-Length": "999"}
            def __enter__(self): return self
            def __exit__(self, *args): pass
        opener = mock.Mock(); opener.open.return_value = Response()
        with mock.patch("urllib.request.build_opener", return_value=opener), mock.patch.dict(os.environ, {"GH_TOKEN": "not-used"}):
            client = producer.PublicHTTP("https://github.com/b1ug/nb1/archive/refs/tags/v1.2.3.tar.gz", "https://codeload.github.com/b1ug/nb1/tar.gz/refs/tags/v1.2.3")
            with self.assertRaises(ValueError): client(producer.API, 10)
        request = opener.open.call_args.args[0]
        self.assertIsNone(request.get_header("Authorization"))


if __name__ == "__main__":
    unittest.main()
