# The Trinity v2 · 完整发行版

克隆仓库或解压 v2 的源代码 ZIP 后，在包含 `cli.mjs` 的仓库根目录运行以下命令。Windows 建议选短路径，例如 `C:\Trinity`。

| 目录 | 内容 |
| --- | --- |
| `cli.mjs`、`src/`、`pipeline/`、`stage2/`、`harness/` | 核心代码、CLI、Harness 源码及构建工具 |
| `environments/` | 34 项基准的正式任务定义、配置、随包数据、驱动、评测程序及外部资源清单 |
| `iter4-harness/` | 从随包源码生成的可运行 Harness |
| `level-api-44/` | 11 种关卡、44 个内置课程实例及渲染代码；与 34 项基准不是同一组 |
| `trinity-studio/` | Web 前端与本地服务 |

## 启动 Web

建议使用 Linux x86-64、Node.js 22+、npm 和 Python 3.10+。从零运行时，Stage 2 的 Python 规则检查需要 Linux 上的 `bwrap` 和 `/usr/bin/python3`。

```sh
(cd level-api-44 && npm install --no-audit --no-fund && npx playwright install chromium)
node trinity-studio/server.mjs --allow-local-env --port 8188 --runs ../trinity-data/runs --trees ../trinity-data/trees
```

打开 `http://127.0.0.1:8188/`。首次启动为空白项目。启用 `--allow-local-env` 后，预览会执行关卡代码，请只打开可信项目。手动编辑和保存项目时可以省略此参数，无需安装 Chromium 或填写模型密钥。上面的命令将新产生的数据保存在发行目录之外。首次安装浏览器通常需要网络，最小化 Linux 还可能需要 Chromium 系统库。调用模型时由使用者提供凭据；ALE 的 OpenAI 兼容服务可使用 `OPENAI_API_KEY`。

## 环境和 Harness

Web 的「环境」面板与 Harness 使用相同的任务登记。可以运行 `node iter4-harness/run.mjs --list-tasks` 查看任务。BuildArena 只登记一次。任务脚本与 Harness 使用 `environments/unseen/tasks/07-buildarena/BuildArena-1.0/` 这一份源码；Web 读取同一份任务清单。可选 Linux 适配器只带源码；不含其系统运行库、Besiege 游戏、Steam Workshop 模组或 Observer 插件，也不会自动下载它们。仅原生仿真需要另行安装，详见 `environments/unseen/tasks/07-buildarena/README.md`。

完整发行版包含 Trinity 代码和基准集成。第三方源码、数据和受限资源的许可范围见 [THIRD-PARTY.md](THIRD-PARTY.md)。依赖版本见 `environments/runtime-dependencies.json`。默认的 8 组大型外部资源保留原有按需下载方式；首次显示「缺失」不是缺少环境代码。可在 Web 环境面板下载，或按任务操作：

```sh
python3 download-environments.py --task video_index_meta_benchmark --check
python3 download-environments.py --task video_index_meta_benchmark
```

第一条只检查本地资源，未安装时返回非零；第二条实际下载。部分资源处理依赖 `environments/requirements-download.txt`。正式题目、判分数据及裁判代码是环境的一部分，不是随包附送的测试结果。

## 共享资源

34 项正式任务每项只保留一个定义目录。Coup 与 Colonel Blotto 共用一套 TextArena；Entity Deduction Arena 的任务与数据加载器共用解开的上游源码和数据；CAPX 两侧相同的网格只保留一个 STL。少量必须按不同路径读取的内容（如许可证、Python 包标记和实例数据）在 ZIP 中是各自独立的普通文件。这些路径不是额外的任务或环境。Harness 的构建源码与可运行发行目录仍然独立，可从源码重新构建。
