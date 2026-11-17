# nb1 Homebrew tap

[English](README.md)

通过 Homebrew 安装 **nb1**，在本机控制 **blink(1)**：

```sh
brew tap b1ug/tap
brew install b1ug/tap/nb1
nb1 version --json
nb1 list
nb1 server --devices YOUR_DEVICE_SERIAL
```

打开 <http://127.0.0.1:8931/demo/> 即可使用内嵌英中调试器。页面、3D 预览和 API 都在同一个程序内，无需 Node 服务或浏览器 USB 授权。Preview 可选，Play 才控制实体灯。

## 安装范围

Formula 从已发布的 [nb1 v0.1.0 源码](https://github.com/b1ug/nb1/releases/tag/v0.1.0)编译，使用 Homebrew 提供的 Go（至少 1.27.4）和本机 C 编译器。Mac 要求 macOS 15 或更新；Linux 以 Homebrew 支持的构建环境为准。这是源码安装，尚未提供预编译 bottle。GitHub 预编译 CLI 的 glibc 2.38 门槛不能直接套用于每个本机源码构建，具体依赖以安装后的二进制和 Homebrew 系统要求为准。

可选 `nb1-mcp` 和 Agent Skill 仍单独从[同版 Release](https://github.com/b1ug/nb1/releases/tag/v0.1.0)下载，当前 Formula 不捆绑它们。

安装不会自动启动 server 或注册服务。初次体验可直接保留前台 `nb1 server`。需要后台用户服务时显式执行：

```sh
nb1 service install --devices YOUR_DEVICE_SERIAL
nb1 service start
nb1 service status
```

`service install` 配置登录加载；未指定 `--start` 时，不立即启动。Mac 使用 LaunchAgent，Linux 使用 systemd 用户服务。没有用户 systemd manager 的 Linux 容器无法托管该服务，但仍可前台运行 server。当前没有 `brew services` 集成。

## 升级与卸载

```sh
brew update
brew upgrade b1ug/tap/nb1
nb1 service status
# 准备好切换已经运行的托管进程时，显式重启：
nb1 service stop
nb1 service start
```

Formula 把服务注册绑定到稳定的 Homebrew `opt` 路径。升级安装包不会自动重启 daemon、改写用户配置或替换已保存颜色／Pattern。卸载正在托管的服务前，先运行 `nb1 service uninstall`，再运行 `brew uninstall nb1`。

## 发布来源

`Formula/nb1.rb` 先由已核验发布源码中的 renderer/template 生成。仅针对精确 v0.1.0 源码与原始输出哈希，再应用四项已审包装修正：关闭父目录 Git 自动识别，并满足三条 Homebrew 严格样式规则。这样 Go 不会把外层 Homebrew 的 commit 误报为 nb1 来源。人类 `nb1 version` 输出仍保留显式 nb1 commit，JSON 的 VCS revision 在源码归档构建中为未知。修正不改上游 tag、程序代码、依赖或灯效，也不会套用于未来版本。

[`releases/nb1-0.1.0.json`](releases/nb1-0.1.0.json)保存显式输入。旁边的来源记录保存 tag 对象、精确 source commit/tree、归档和 renderer/template 哈希、修正前后 Formula 哈希及各项理由。安装源不会使用 branch、Actions 产物或合成 fixture。

准备工具先校验公开 Release、tag、源码归档中每个 Git blob，再运行对应版本的 renderer：

```sh
python3 scripts/prepare_formula.py \
  --input /absolute/path/approved-release.json \
  --output-dir /absolute/path/new-nb1-formula-review
```

仅发布准备需要 Python 3.11+ 和 Ruby，输出必须是新的本地目录。工具不会安装、发布或启动服务。

## 验证

```sh
python3 -B -m unittest discover -s tests -v
```

单元测试只用 mock HTTP 和合成归档，不访问 USB 或用户配置。Mac／Linux 原生 CI 编译真实发布源码，执行 Formula 无 USB 测试，检查安装版本与来源，并验证离线 daemon。软件检查通过不等于实体 USB、MK3、登录或重启验收通过。

[完整安装说明](https://github.com/b1ug/nb1/blob/v0.1.0/docs/install.zh-CN.md) · [Homebrew 系统要求](https://docs.brew.sh/Installation)
