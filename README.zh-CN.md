# nb1 Homebrew tap 准备仓库

[English](README.md)

这是**私有准备仓库，目前不可安装**。远程仓库为 `b1ug/homebrew-tap`，保持私有供审核。当前没有 `Formula/nb1.rb`，也没有选定符合条件的新 nb1 Release；历史 `v0.0.1` 不提供当前 CLI/API。

产品名是 **nb1**，硬件名是 **blink(1)**。

## 为真实 Release 生成本地审核文件

需要已安装 Python 3.11+ 和 Ruby；工具不会安装 Homebrew 或服务。只通过未认证的公共 HTTPS GET 获取资料，不读取 GitHub 凭据、netrc、代理配置或用户的 nb1/系统服务配置。

从实际已发布源码取得对应的 `packaging/homebrew/release-input.required.json`，填入真实审核数据，保持原 schema，`fixture_only` 必须为 `false`：

| 字段 | 内容 |
| --- | --- |
| `version` | 不带 `v`、高于 `0.0.1` 的已发布 SemVer；由上游渲染器校验。 |
| `source_url` | 精确的 `https://github.com/b1ug/nb1/archive/refs/tags/v<version>.tar.gz`。 |
| `source_sha256` | 该真实归档的 SHA-256。 |
| `source_commit` | 该 tag 最终指向的精确小写 commit SHA。 |
| `min_macos`、`components` | 该版渲染器支持的显式值。 |
| `schema_version`、`fixture_only` | 渲染器原有的显式 schema 字段。 |

显式指定一个**父目录已存在、目标尚不存在**的本地目录：

```sh
python3 scripts/prepare_formula.py \
  --input /absolute/path/approved-release.json \
  --output-dir /absolute/path/new-nb1-formula-review
```

准备器核对公开仓库、与精确 tag 对应的 published Release、轻量/附注 tag 的最终 commit、源码树、官方归档 URL、SHA-256，以及归档中每个文件的 Git blob 和执行位；渲染前再次核对 tag/Release，发生移动就失败。`target_commitish` 不能作为 commit 身份依据。发布为 prerelease 时会将状态保留在来源记录中，供审核决定。GitHub 的 Release 与裸 tag 不相同，ref 本身也可能被移动。[Release API](https://docs.github.com/en/rest/releases/releases) · [Git refs](https://docs.github.com/en/rest/git/refs)

通过后才把已核验归档中的原始 `render_formula.py` 和 `nb1.rb.in` 放入临时目录，调用该版渲染器。不复制 Formula 规则，不提供 fixture/跳过校验开关，不回退到 branch、latest 或 Actions 包。上游已核验 Python 渲染器以当前用户运行，使用隔离的 Python 导入和最小子进程环境；这不是操作系统沙盒，也不代替源码审核。

上游输入校验和 `ruby --disable-gems -c` 均通过后，才生成：

```text
new-nb1-formula-review/
  Formula/nb1.rb
  provenance.json
```

目标目录以独占方式创建；拒绝覆盖任何已有路径。校验失败不产生输出，本地文件发布阶段失败则仅清理刚创建的目标目录，不覆盖输入。来源记录包含 source/tree/archive/renderer/template/Formula 哈希、公开元数据响应哈希、Release 状态和检查范围。

工具只准备本地文件。把真实 Formula 纳入私有 tap 前，应审核来源与各平台验收结果。它不会 commit、push、创建 Release、安装 Homebrew 或启动服务。Ruby 语法通过不代表 `brew audit`、安装升级、用户服务、USB 或光学验收通过。

## 边界与测试

网络预算 180 秒（在读取之间检查）、socket timeout 20 秒，不重试。JSON 嵌套最多 64 层；输入上限 64 KiB；每份元数据 8 MiB；归档压缩后 32 MiB、展开后 128 MiB；单文件 32 MiB；最多 10,000 项。拒绝截断的 Git tree、链接、submodule 和导出时过滤/缺失文件的归档。这些检查针对当前 nb1 源码布局，未来不兼容时应明确修改并验证，不会静默放宽。[Git tree 文档](https://docs.github.com/en/rest/git/trees)

```sh
python3 -m unittest discover -s tests -v
```

默认测试只使用合成 Release 元数据、mock HTTP、临时归档和 Ruby 语法检查，不获取真实 Release，不在此仓库留下 Formula。可额外对已有 nb1 工作区中的真实渲染器/模板进行离线集成：

```sh
NB1_TAP_TEST_UPSTREAM=/absolute/path/to/nb1 \
  python3 -m unittest discover -s tests -v
```

该集成依然使用 mock 元数据，是软件测试，不是已发布版本或可安装通道。CI 只运行离线检查。
