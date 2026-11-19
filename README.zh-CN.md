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

打开 <http://127.0.0.1:5885/demo/> 即可使用内嵌英中调试器。页面、3D 预览和 API 都在同一个程序内，无需 Node 服务或浏览器 USB 授权。Preview 可选，Play 才控制实体灯。

## 安装范围

Formula 从已发布的 [nb1 v0.1.3 源码](https://github.com/b1ug/nb1/releases/tag/v0.1.3)编译，使用 Homebrew 提供的 Go（至少 1.27.4）和本机 C 编译器。Mac 要求 macOS 15 或更新；Linux 以 Homebrew 支持的构建环境为准。这是源码安装，尚未提供预编译 bottle。GitHub 预编译 CLI 的 glibc 2.38 门槛不能直接套用于每个本机源码构建，具体依赖以安装后的二进制和 Homebrew 系统要求为准。

CLI 帮助、错误与诊断消息在不同语言环境下仍保持英文；内嵌调试器有独立英中切换。`NO_COLOR=1` 禁用终端样式。应用源码最低要求 Go 1.25.8，Formula 使用上方列出的较新构建工具链。

运行 `nb1 mcp` 即可启动 stdio MCP。升级已有 Agent 时，将可执行程序从 `nb1-mcp` 改为 `nb1`，并在原有参数前加上 `mcp`。[Agent Skill](https://github.com/b1ug/nb1/releases/tag/v0.1.3) 单独下载。

默认端口从 8931 迁至 5885。已显式配置的监听地址和客户端地址优先生效，迁移时请一并更新。

安装不会自动启动 server 或注册服务。初次体验可直接保留前台 `nb1 server`。需要后台用户服务时显式执行：

```sh
nb1 service install --devices YOUR_DEVICE_SERIAL
nb1 service start
nb1 service status
```

`service install` 配置登录加载；未指定 `--start` 时，不立即启动。Mac 使用 LaunchAgent，Linux 使用 systemd 用户服务。没有用户 systemd manager 的 Linux 容器无法托管该服务，但仍可前台运行 server。当前没有 `brew services` 集成。

## 选择设备

daemon 可以持有多个已配置设备。CLI 控制命令未显式指定目标时，优先使用配置中的默认设备；否则按 serial 字节序选择首个在线设备。配置多只设备时，自动选择会在 stderr 提示配置数量与所选 serial。这是 serial 排序，不是 USB 插入顺序。可用 `--device SERIAL` 另选设备。目标忙碌或显式目标缺失时，不会静默改到另一只灯。内嵌工作台在刷新或切换语言后保留当前选择，包括离线目标。

## 升级与卸载

```sh
brew update
brew upgrade b1ug/tap/nb1
nb1 service status
# 准备好切换已经运行的托管进程时，显式重启：
nb1 service stop
nb1 service start
```

Formula 把服务注册绑定到稳定的 Homebrew `opt` 路径。升级安装包不会自动重启 daemon、改写用户配置或替换已保存颜色／Pattern。卸载正在托管的服务前，先运行 `nb1 service uninstall --stop`，再运行 `brew uninstall nb1`。

## 发布来源

`Formula/nb1.rb` 直接使用已核验 v0.1.3 发布源码中的 renderer/template 原始输出，不再追加本地适配。源码归档构建禁用无关父目录的 VCS 自动识别；人类 `nb1 version` 输出仍显示显式 nb1 source commit，JSON 的 VCS revision 在这类构建中为未知。

[`releases/nb1-0.1.3.json`](releases/nb1-0.1.3.json) 保存显式输入。旁边的来源记录把公开 Release、tag 对象、精确 source commit/tree、源码归档与 renderer/template 哈希绑定到 Formula；原始输出和提交后的 Formula 哈希相同，适配列表为空。安装源不使用 branch、Actions 产物或合成 fixture。

原有 [v0.1.0 输入](releases/nb1-0.1.0.json) 与来源记录保留首版所需的四项精确哈希限定包装修正。历史文件与窄范围 adapter 保持原样；这些修正不会套到后续版本；已核验的 [v0.1.1](releases/nb1-0.1.1.json) 与 [v0.1.2](releases/nb1-0.1.2.json) 输入和来源记录也完整保留。

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

[完整安装说明](https://github.com/b1ug/nb1/blob/v0.1.3/docs/install.zh-CN.md) · [Homebrew 系统要求](https://docs.brew.sh/Installation)
