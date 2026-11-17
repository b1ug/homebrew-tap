# nb1 Homebrew tap

[简体中文](README.zh-CN.md)

Install **nb1**, the local control tool for **blink(1)**:

```sh
brew tap b1ug/tap
brew install b1ug/tap/nb1
nb1 version --json
nb1 list
nb1 server --devices YOUR_DEVICE_SERIAL
```

Open <http://127.0.0.1:8931/demo/> for the embedded English/Chinese debugger.
The workbench, 3D preview and API are part of the same executable; no Node server
or browser USB permission is required. Preview is optional; Play controls the light.

## Supported installation

The Formula builds the published [nb1 v0.1.0 source](https://github.com/b1ug/nb1/releases/tag/v0.1.0)
with Homebrew's Go dependency (Go 1.27.4 or newer) and a native C compiler.
It requires macOS 15 or newer on Mac; Linux follows Homebrew's supported Linux
build environment. It is a source installation, not a prebuilt bottle. The
prebuilt GitHub CLI's glibc 2.38 requirement does not describe every local source
build; inspect the installed binary and your platform's Homebrew requirements.

The matching optional `nb1-mcp` and Agent Skill are separate
[release downloads](https://github.com/b1ug/nb1/releases/tag/v0.1.0), not bundled by this Formula.

Installation does not start a server or register a service. Keep the foreground
`nb1 server` while trying the debugger. For an explicitly managed user service:

```sh
nb1 service install --devices YOUR_DEVICE_SERIAL
nb1 service start
nb1 service status
```

`service install` configures login loading; it does not immediately start the
service without `--start`. Management uses macOS LaunchAgent or Linux systemd
user services. A Linux container without a user systemd manager cannot run that
managed-service path; foreground `nb1 server` still works. This Formula does not
provide `brew services` integration.

## Upgrade and remove

```sh
brew update
brew upgrade b1ug/tap/nb1
nb1 service status
# Restart explicitly when ready to switch an existing managed process:
nb1 service stop
nb1 service start
```

The Formula binds service registration to the stable Homebrew `opt` path.
Package upgrades do not restart a running daemon, rewrite user configuration,
or replace saved colors/Patterns. Before uninstalling an active managed service,
run `nb1 service uninstall`, then `brew uninstall nb1`.

## Release provenance

`Formula/nb1.rb` starts with the renderer/template in the verified published nb1
source. For this exact v0.1.0 source and original output hash, four reviewed
packaging corrections disable automatic parent-Git detection and satisfy three
strict Homebrew style rules. Go must not report Homebrew's enclosing Git commit as
nb1's source. The explicit nb1 commit remains in human `nb1 version` output; the
JSON VCS revision is unknown for this source-archive build. These corrections do
not change the upstream tag, application code, dependencies or lighting behavior,
and do not apply to future releases.

[`releases/nb1-0.1.0.json`](releases/nb1-0.1.0.json) contains the explicit input.
The adjacent provenance records the tag object, exact source commit/tree, archive
and renderer/template hashes, original/output Formula hashes and each adaptation
reason. No branch, Actions artifact or synthetic fixture is an installation source.

The preparation tool checks the public Release, tag, source archive and every
archived Git blob before calling that release's renderer:

```sh
python3 scripts/prepare_formula.py \
  --input /absolute/path/approved-release.json \
  --output-dir /absolute/path/new-nb1-formula-review
```

Python 3.11+ and Ruby are required for preparation only. Output must be a new
local directory. The tool does not install, publish or start anything.

## Checks

```sh
python3 -B -m unittest discover -s tests -v
```

Unit tests use mock HTTP and synthetic archives, not USB or user configuration.
Native macOS/Linux CI builds the real released source, runs the Formula's
USB-free tests, verifies installed version/source and exercises an offline daemon.
A successful software check is not physical USB, MK3, login or reboot acceptance.

[Installation guide](https://github.com/b1ug/nb1/blob/v0.1.0/docs/install.md)
· [Homebrew support requirements](https://docs.brew.sh/Installation)
