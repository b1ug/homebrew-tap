# Source URL, checksum, version and commit must be explicitly bound before use.
# Release inputs and installation evidence are recorded separately.
require "open3"
require "rubygems"

class Nb1 < Formula
  desc "Control blink(1) through a local CLI and daemon"
  homepage "https://github.com/b1ug/nb1"
  url "https://github.com/b1ug/nb1/archive/refs/tags/v0.1.3.tar.gz"
  sha256 "08a1ce843c6db0db38e839b1550f37a33a12f1ddde66b04ab6b23c138094e502"
  license "MIT"

  depends_on "go" => :build

  on_macos do
    depends_on macos: :sequoia
  end

  deny_network_access!

  def fetch
    ENV["GOWORK"] = "off"
    ENV["GOTOOLCHAIN"] = "local"
    check_go_version
    system "go", "mod", "download"
    system "go", "mod", "verify"
  end

  def install
    ENV["CGO_ENABLED"] = "1"
    ENV["GOWORK"] = "off"
    ENV["GOTOOLCHAIN"] = "local"
    check_go_version
    ldflags = ["-X", "github.com/b1ug/nb1/config.GitCommit=" + "48895be5babc11d6f3b2a7ab16e316bd564e726e",
               "-X", "github.com/b1ug/nb1/config.GitSummary=v#{version}",
               "-X", "github.com/b1ug/nb1/config.ServiceBinary=#{opt_bin}/nb1",
               "-X", "github.com/b1ug/nb1/config.ServiceBinaryRoot=#{rack}"]
    system "go", "build", "-buildvcs=false", *std_go_args(output: bin/"nb1", ldflags: ldflags), "-mod=readonly", "."
    # Go's linker uses 0775 before umask. The installed service executable
    # must remain protected even when the caller's umask permits group writes.
    (bin/"nb1").chmod 0755
    pkgshare.install "LICENSE"
    doc.install "README.md"
  end

  def check_go_version
    output, _error, status = Open3.capture3("go", "env", "GOVERSION")
    actual = output.strip
    match = /\Ago(\d+\.\d+\.\d+)\z/.match(actual)
    return if status.success? && match && Gem::Version.new(match[1]) >= Gem::Version.new("1.27.4")

    odie "nb1 requires Go 1.27.4 or newer; found #{actual.inspect}. Update Go before building."
  end

  test do
    (testpath/"setting.yaml").write "{}\n"
    # USB-free installation checks. Rendering a service exercises an installed
    # command without registering a service or requiring a user manager.
    platform = OS.mac? ? "darwin" : "linux"
    checks = [
      [["--help"], "nb1 [command]"],
      [["control", "--help"], "nb1 control [command]"],
      [["control", "run", "--help"], "nb1 control run [SERIAL] FILE"],
      [["service", "render", "--platform", platform, "--binary", (bin/"nb1").to_s,
        "--devices", "00000000"], OS.mac? ? "<key>ProgramArguments</key>" : "ExecStart="],
    ]
    checks.each do |arguments, usage|
      args = [bin/"nb1", "--config", testpath/"setting.yaml", *arguments]
      output, error, status = Open3.capture3(*args.map(&:to_s))
      assert status.success?, error
      assert_match usage, output
    end
    assert_equal "{}\n", (testpath/"setting.yaml").read
  end
end
