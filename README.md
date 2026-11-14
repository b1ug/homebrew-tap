# nb1 Homebrew tap preparation

[简体中文](README.zh-CN.md)

This is a **private preparation repository, not an installable tap**. Its
remote is `b1ug/homebrew-tap`, kept private for review. No `Formula/nb1.rb` is present. No qualifying new nb1 Release has
been selected, and historical `v0.0.1` does not provide the current CLI/API.

The product is **nb1**; the hardware is **blink(1)**.

## Prepare a real release for local review

Requirements: Python 3.11+ and Ruby already installed. This tool installs neither
Homebrew nor a service. It uses unauthenticated public HTTPS GETs and does not read
GitHub credentials, netrc, proxy configuration or nb1/user service configuration.

Obtain the approved real release input matching the released nb1 source's
`packaging/homebrew/release-input.required.json`. Fill it with verified values;
keep its existing schema and set `fixture_only` to `false`.

| Input | Meaning |
| --- | --- |
| `version` | Released SemVer without `v`, newer than `0.0.1`; the upstream renderer validates this. |
| `source_url` | Exact `https://github.com/b1ug/nb1/archive/refs/tags/v<version>.tar.gz`. |
| `source_sha256` | Actual SHA-256 of that archive. |
| `source_commit` | Exact lowercase commit SHA reached by that tag. |
| `min_macos`, `components` | Explicit values supported by that release's renderer. |
| `schema_version`, `fixture_only` | Existing explicit renderer schema fields. |

Choose an **existing parent and a new output directory** explicitly:

```sh
python3 scripts/prepare_formula.py \
  --input /absolute/path/approved-release.json \
  --output-dir /absolute/path/new-nb1-formula-review
```

The producer verifies the public repository, a published Release for the exact
tag, lightweight or annotated tag resolution, commit/tree identity, official
archive URL and checksum, and every archived file's Git blob/mode. It rechecks the
tag and Release before rendering; a moved tag fails. `target_commitish` is not
used as proof of a commit. Published prerelease status is recorded for review.
GitHub distinguishes a Release from a bare tag, and refs can move.
([Release API](https://docs.github.com/en/rest/releases/releases),
[Git refs](https://docs.github.com/en/rest/git/refs))

Only then does it copy the verified archive's original `render_formula.py` and
`nb1.rb.in` to a temporary directory and call that renderer. There is no vendored
Formula, duplicated rendering rule, fixture/skip-verification CLI option, or
fallback to a branch/Actions artifact. The verified release's Python renderer
executes under the current user with isolated Python imports and a minimal child
environment; this is not an operating-system sandbox or a review of upstream code.

After upstream validation and `ruby --disable-gems -c` succeed, the tool creates:

```text
new-nb1-formula-review/
  Formula/nb1.rb
  provenance.json
```

The new output directory is reserved exclusively; an existing path is refused.
Verification failures create no output. A failure while publishing the local
files removes only that newly created directory. Inputs are never overwritten.
Provenance records source/tree/archive/renderer/template/Formula hashes, public
metadata response hashes, release status and verification scope.

This prepares local files only. Review the provenance and platform acceptance
evidence before manually bringing a real Formula into the private tap. Nothing
commits, pushes, publishes a Release, installs Homebrew, or starts a service.
Generated syntax checks do not constitute `brew audit`, installation, upgrade,
user-service, USB or optical acceptance.

## Limits and tests

GETs use a 180-second budget checked between reads, a 20-second socket timeout and
no retries. JSON nesting is limited to 64 levels. Input is bounded to 64 KiB;
metadata to 8 MiB per response; archive
to 32 MiB compressed / 128 MiB expanded; individual files to 32 MiB; entries to
10,000. Partial Git trees, links, submodules and export-filtered/incomplete source
archives are refused. These limits are deliberate checks for the current nb1
source layout; they are not silently weakened when a future layout changes.
([Git tree metadata](https://docs.github.com/en/rest/git/trees))

```sh
python3 -m unittest discover -s tests -v
```

Tests use synthetic release metadata, mock HTTP, temporary archives and local
Ruby syntax checks. They never fetch a real release or leave a Formula here.
To exercise an existing real nb1 renderer/template with the same mocked metadata:

```sh
NB1_TAP_TEST_UPSTREAM=/absolute/path/to/nb1 \
  python3 -m unittest discover -s tests -v
```

That optional test is still an offline software fixture, not a published release
or an installable channel. CI runs only offline verification tests.
