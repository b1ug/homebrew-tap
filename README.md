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

Open <http://127.0.0.1:5885/demo/> for the embedded English/Chinese debugger.
The workbench, 3D preview and API are part of the same executable; no Node server
or browser USB permission is required. Preview is optional; Play controls the light.

## Supported installation

The Formula builds the published [nb1 v0.1.4 source](https://github.com/b1ug/nb1/releases/tag/v0.1.4)
with Homebrew's Go dependency (Go 1.27.4 or newer) and a native C compiler.
It requires macOS 15 or newer on Mac; Linux follows Homebrew's supported Linux
build environment. It is a source installation, not a prebuilt bottle. The
prebuilt GitHub CLI's glibc 2.38 requirement does not describe every local source
build; inspect the installed binary and your platform's Homebrew requirements.

The CLI help, errors and diagnostic messages remain English across locale
settings; the embedded workbench has its own English/Chinese switch. `NO_COLOR=1`
disables terminal styling. The application source minimum is Go 1.25.8; the
Formula deliberately uses the newer build toolchain stated above.

Launch MCP over stdio with `nb1 mcp`. When upgrading an existing agent, change the executable from `nb1-mcp` to `nb1` and add `mcp` before its existing arguments. v0.1.4 adds per-device `reject`, `queue` and `preempt` policies plus guarded MK2 Flash startup-preset reset (`nb1 device reset SERIAL [off|rainbow|starlight|fireflies]`). The [Agent Skill](https://github.com/b1ug/nb1/releases/tag/v0.1.4) is a separate download.

The default port moved from 8931 to 5885. Existing explicit listeners and client endpoints take precedence. Keep them together when migrating a service.

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

## Choosing a device

The daemon can own several configured devices. Without an explicit target, CLI
control commands use the configured default; otherwise they choose the first
online serial in byte order. With multiple configured devices, automatic choice
announces the count and selected serial on stderr. This is serial order, not USB
insertion order. Use
`--device SERIAL` to choose another device. A busy or missing explicit target
never silently redirects playback to another light. The embedded workbench keeps
your selection through refresh and language changes, including offline targets.

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
run `nb1 service uninstall --stop`, then `brew uninstall nb1`.

## Release provenance

`Formula/nb1.rb` is the unchanged output of the renderer/template in the
verified published v0.1.4 source. Its source-archive build disables unrelated
parent-repository VCS stamping. Human `nb1 version` output still includes the
explicit nb1 source commit; the JSON VCS revision remains unknown for this build.

[`releases/nb1-0.1.4.json`](releases/nb1-0.1.4.json) contains the explicit input.
The adjacent provenance binds the public Release, tag object, exact source
commit/tree, source archive and renderer/template hashes to the Formula. The raw
renderer output and committed Formula have identical hashes and no adaptations.
No branch, Actions artifact or synthetic fixture is an installation source.

The original [v0.1.0 input](releases/nb1-0.1.0.json) and its provenance retain
the four exact-hash-bound packaging corrections required by that initial
release. Those historical records and the narrowly scoped adapter are preserved;
the corrections do not apply to later releases. The verified
[v0.1.1](releases/nb1-0.1.1.json) and
[v0.1.2](releases/nb1-0.1.2.json) and [v0.1.3](releases/nb1-0.1.3.json)
inputs and provenance are also preserved.

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

[Installation guide](https://github.com/b1ug/nb1/blob/v0.1.4/docs/install.md)
· [Homebrew support requirements](https://docs.brew.sh/Installation)
