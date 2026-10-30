<p align="center">
  <img src="assets/infrec.png" alt="InfRec Cardinal AI Lab" width="240">
</p>

<h1 align="center">The Trinity</h1>

<p align="center">
  <strong>Capability-Driven Recursive Self-Improvement for Multimodal Agents</strong>
</p>

<p align="center">The Trinity Research Team</p>

<p align="center">
  <a href="README.md">English</a> · 简体中文 ·
  <a href="https://trinity-rsi.github.io/">项目主页</a> ·
  <a href="paper/The-Trinity.pdf">论文 PDF</a>
</p>

## 🔥 最新动态!!

- **2026-10-26：** 🤗 论文发布！The Trinity 曾登顶 [Hugging Face Daily Papers](https://huggingface.co/papers/2610.36077)（**#1**）。

## 📑 开源计划

1. [x] 发布代码。
2. [ ] 发布仿真环境。

## 📖 项目介绍

**The Trinity** 是面向多模态智能体的递归自我改进框架，将世界生成与智能体 Harness（运行框架）演化相结合。它按照共享能力需求组织任务，通过可验证的执行反馈连接三个角色：

- **Creator** 构建用于能力学习的简化、可验证世界。
- **Explorer** 与世界交互，通过选择性继承演化可复用的能力模块。
- **Evolver** 将任务需求组织为层次化能力树。

能力驱动的 **Real2Sim2Real** 将生成世界中的学习连接到原始任务上的评估；**Capability-Aware Harness Router** 则根据任务选择兼容的模块配置。方法、实验设置与结果见[技术报告](paper/The-Trinity.pdf)。

![The Trinity 概览：Creator、Explorer 与 Evolver 连接多模态任务空间扩展和能力驱动的 Harness 演化。](assets/overview.png)

## 🗂️ 代码结构与发布范围

本仓库包含任务发现与划分、轨迹分析与能力归纳、Creator–Explorer–Evolver 演化、Harness 路由，以及相关提示词和配置。

```text
cli.mjs                统一命令行入口
config/                模型服务配置
pipeline/              Stage 1：任务发现、审查、划分与导出
stage2/                Stage 2：轨迹分析、能力归纳与能力树
harness/               世界生成、模块演化、验证与路由
src/                   阶段集成与用量汇总
assets/                项目标识与概览图
paper/                 技术报告
```

运行实际实验还需要自行接入环境驱动、适配器配置和基准数据，并准备评估用的路由计划。本仓库未附带这些资源，也未附带论文实验快照，因此以下说明是框架接入流程，不能直接一键复现论文结果。

## 🛠️ 环境要求

- **Node.js 22 或更新版本**。JavaScript 部分仅使用 Node.js 内置模块，无需安装 npm 第三方依赖。
- **Python 3.10 或更新版本**。Stage 2 声明依赖 `anthropic>=1.0`，使用 setuptools 构建。
- 可用的模型服务账号、密钥及网络连接。Stage 1 的任务发现还需要服务支持相应的搜索能力。
- 完整 Creator 训练需要 **Linux、`/bin/bash`、位于 `/usr/bin/bwrap` 的 Bubblewrap 及可用的用户命名空间**。WSL 环境同样需要满足这些条件。
- 提取 PDF 来源证据需要 `pdftotext`，或安装了 `pypdf` 的 Python；扫描版 PDF 需要另行进行 OCR。
- 与目标任务匹配的环境驱动及其运行依赖。

仓库没有提供 demo 或测试脚本。下面的 `--help` 命令只检查 CLI 是否可以加载；它不验证模型服务、环境驱动或完整训练。

## 🚀 安装

以下命令在仓库根目录运行，使用 Bash：

```bash
git clone https://github.com/InfRec-Cardinal/The-Trinity.git
cd The-Trinity
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ./stage2
export TRINITY_PYTHON="$PWD/.venv/bin/python"
node cli.mjs stage2 --help
```

请保留完整仓库目录结构。Stage 2 会读取相邻的 `config/` 和 `harness/`，可编辑安装适合这一使用方式。

设置模型服务。请将占位值替换为账号实际可用的模型和服务支持的 API 版本：

```bash
export TRINITY_PROVIDER=anthropic
export ANTHROPIC_API_KEY='<your-api-key>'
export TRINITY_MODEL='<account-available-model>'
export TRINITY_API_VERSION='<supported-api-version>'
```

模型端点需要支持代码使用的 Anthropic Messages 协议、工具调用、adaptive thinking 和 effort 参数；图像任务还需要相应的多模态支持。仓库中的预设值不代表服务端已验证可用。程序读取进程环境变量，**不会自动加载 `.env` 文件**。

Windows PowerShell 可为 CLI 明确指定 Python，例如在创建 `.venv` 后设置：

```powershell
$env:TRINITY_PYTHON = (Resolve-Path .venv\Scripts\python.exe).Path
node cli.mjs stage2 --help
```

完整 Creator 训练仍需要满足上面的 Linux 运行条件。

## 🧭 使用流程

### 1. 发现任务并导出划分

```bash
export PIPELINE_DATA_DIR="$PWD/runs/stage1/data"
export PIPELINE_EXPORT_DIR="$PWD/runs/stage1/exports"
node cli.mjs stage1 connect-test
node cli.mjs stage1 search
node cli.mjs stage1 status
```

`connect-test` 会发出真实模型和搜索请求；`search` 也会产生服务用量。搜索未完成时，再次执行 `search` 会继续检查点；已经完成后再次执行则会开始新搜索。

请检查 `status`、搜索返回状态以及导出的任务划分。`incomplete` 状态可能仍以退出码 0 结束；只有搜索完成且划分的 `gaps`、`errors` 均为空时，才应继续。按实际导出文件名设置路径：

```bash
export HANDOFF="$PWD/runs/stage1/exports/stage2-handoff-YYYYMMDD.json"
```

将 `YYYYMMDD` 替换为实际文件名中的日期。Stage 1 发现任务描述与来源，不会自动安装对应的基准环境。

### 2. 收集训练任务的初始探索轨迹

先按下方“环境适配器”准备 `local/adapter.json` 和驱动模块，再运行：

```bash
node cli.mjs explore --handoff "$HANDOFF" --adapter local/adapter.json --out runs/explore-train
```

默认仅探索训练集，每项任务运行 5 个实例，生成 `runs.json`、轨迹与事件记录。后续集成训练会验证这些执行记录的来源和完整性。

### 3. 分析轨迹并归纳能力

```bash
node cli.mjs stage2 all --handoff "$HANDOFF" --runs runs/explore-train/runs.json --out runs/stage2
```

`all` 仅处理训练集，依次完成导入、摘要、分析、独立审核与修订、能力归纳、任务分配和能力树输出。审核未通过时流程会停止，需要根据输出检查原因。

也可以通过 `import-runs`、`digests`、`analyse`、`review`、`induce`、`assign`、`trees` 分步运行，具体参数见 `node cli.mjs stage2 <子命令> --help`。

### 4. 演化 Harness

可先导出配置以检查训练任务和能力划分，然后开始训练：

```bash
node cli.mjs prepare --stage2 runs/stage2 --adapter local/adapter.json --out runs/training-config.json
node cli.mjs train --stage2 runs/stage2 --adapter local/adapter.json --out runs/train
```

`prepare` 是可选步骤，其目标文件必须尚不存在。`train` 会从 Stage 2 和适配器重新构建配置，**不会读取上一步导出的 JSON**。训练和验证各固定运行 5 个回合。

每次 `explore`、`train`、`route` 都应使用新的输出目录；上面的路径适用于第一次运行。

### 5. 准备路由计划并评估

训练生成 `runs/train/routing-candidates.json`，仍需自行编写 `local/routing-plan.json`。计划应包含 `schema: "trinity-routing-plan-v1"`、`protocolId`、`split`、`candidates` 和 `tasks`。每项任务需要 `taskId`、`benchmarkId`、`world`、`publicTask`、正整数 `budget` 与 `modelCallBudget`。

候选模块必须与训练产物一致。每个基准与 Harness 组合还需要 5 个 `preparationWorlds`，或符合协议且可验证的已冻结技能。公开任务上下文中不得放入评估能力标签或真实答案。完整字段和校验规则见 [路由协议](harness/src/router-protocol.mjs) 与 [评估技能准备](harness/src/evaluation-skills.mjs)。

```bash
node cli.mjs route --plan local/routing-plan.json --adapter local/adapter.json --training-run runs/train --out runs/route
node cli.mjs metrics runs/explore-train runs/train runs/route
```

`metrics` 汇总指定目录内记录的用量与执行指标。上述命令未包含 Stage 1、Stage 2；如需汇总这些阶段，可额外传入 `runs/stage1/data` 和 `runs/stage2`。

### 未见任务

必须在 Harness 训练完成后，才可使用 `explore --cohort unseen --training-run runs/train` 收集未见任务轨迹。随后向同一 Stage 2 目录执行 `import-runs`、`digests`、`unseen` 和 `trees`；其中导入、`unseen`、`trees` 需传入 `--training-run runs/train`。

这一分析沿用训练时固定的能力目录。训练绑定的任务划分、能力目录及训练分配必须保持不变；旧的未见任务轨迹不能绕过训练完成验证。实现见 [Stage 2 CLI](stage2/trinity_stage2/cli.py) 和 [训练协议验证](harness/src/protocol-state.mjs)。

## 🔌 环境适配器

自行创建 `local/adapter.json`，最小配置如下。该 JSON 只负责连接你实现的驱动，不能独立提供运行环境：

```json
{
  "driverModule": "./driver.mjs",
  "driverOptions": {},
  "actionBudget": 4
}
```

`driverModule` 相对于适配器 JSON 所在目录解析。`local/driver.mjs` 必须导出 `createDriver(options)`，返回环境驱动对象；默认模型后端使用上面的服务配置。

| 阶段 | 驱动成员 | 职责 |
| --- | --- | --- |
| 探索与评估 | `loadBenchmark(task)` | 加载任务对应的基准世界 |
| 探索与评估 | `fingerprint(world)` | 提供可验证的世界内容标识 |
| 探索与评估 | `instanceManifest(world, trials)` | 提供运行实例清单 |
| 探索与评估 | `reset(world, instance)`、`initialState(session)` | 初始化会话并提供可核对的初始状态 |
| 探索与评估 | `step(session, action)` | 执行动作并返回原生环境结果 |
| 可选清理 | `close(session)` | 释放会话资源 |
| Creator 训练 | `designContract`、`buildContract` | 定义设计和构建的输出约束 |
| Creator 训练 | `validateDesign(design, node)`、`materialize(design, proposal, context)` | 校验设计并构建世界 |
| Creator 训练 | `inspect(world, design, buildDigest)`、`creatorAuditPlan(world, design)` | 提供检查信息及可执行的验证计划 |

`reset` 返回的会话需要包含 `observation` 和 `actionSchema`。`step` 的返回值需要布尔值 `done`、`success`、公开 `observation` 和有限且非负的 `cost`；`success: true` 必须同时满足 `done: true`。可附带有限数值的 `score`、`reward`。结果应来自真实环境执行。初始状态、世界指纹、成功判定和 Creator 审核需要互相一致，不能仅返回“审核通过”的布尔值。

接入时请结合 [集成入口](src/integration.mjs)、[探索器](harness/src/explorer.mjs)、[实例固定](harness/src/exploration-plan.mjs)、[Creator 构建](harness/src/creator-coding.mjs) 和 [Creator 审核](harness/src/creator-audits.mjs) 实现完整约定。

## ⚙️ 配置与产物

模型服务预设位于 [config/providers.json](config/providers.json)。支持的配置标识为 `anthropic`、`packy`、`openrouter`、`geili`、`custom`，对应的密钥变量分别为 `ANTHROPIC_API_KEY`、`PACKY_API_KEY`、`OPENROUTER_API_KEY`、`GEILI_API_KEY`、`TRINITY_API_KEY`。

| 环境变量 | 用途 |
| --- | --- |
| `TRINITY_PROVIDER` | 选择服务配置 |
| `TRINITY_API_KEY` | 通用密钥回退；custom 的密钥 |
| `TRINITY_MODEL`、`TRINITY_EFFORT` | 模型和推理强度 |
| `TRINITY_BASE_URL`、`TRINITY_AUTH` | 端点与 `x-api-key` / `bearer` 认证方式；custom 必须配置端点 |
| `TRINITY_API_VERSION` | 服务支持的 API 版本日期 |
| `TRINITY_WEB_SEARCH` | 搜索模式，须与服务能力匹配 |
| `TRINITY_PROVIDERS_FILE` | 指定另一份服务配置表 |
| `TRINITY_PYTHON`、`TRINITY_NODE` | 指定 Python 与 Stage 2 协议验证所用的 Node 可执行文件 |
| `PIPELINE_DATA_DIR`、`PIPELINE_EXPORT_DIR` | Stage 1 的工作目录与导出目录 |
| `PIPELINE_PDFTOTEXT`、`PIPELINE_PDF_PYTHON` | 指定 PDF 文本提取所用的可执行文件 |

Stage 1 当前排除音频任务输入。默认未见任务比例为 `18/46`，按能力方向、来源审核和训练任务保留规则划分，不保证发现固定数量的任务。需要调整已完成任务库的划分时，可在后续阶段开始前执行 `node cli.mjs stage1 split --unseen-fraction 0.4`，再执行 `node cli.mjs stage1 export`。

Harness 默认参数见 [harness/config/defaults.json](harness/config/defaults.json)，模块模板见 [harness/config/templates.json](harness/config/templates.json)。适配器可设置迭代次数、动作预算等支持的选项；详见 [trainingConfig](src/integration.mjs)。

| 阶段 | 主要产物 |
| --- | --- |
| Stage 1 | 任务库、划分及 `stage2-handoff-*.json` |
| 初始探索 | `records/`、`runs.json`、`events.jsonl` |
| Stage 2 | 轨迹摘要、审核记录、`capabilities/capabilities.json`、`train/task-capability-gaps.json` |
| 能力树 | `trees/` 下的 JSON、CSV、SVG 和 Draw.io 文件 |
| Harness 训练 | `tree.json`、`summary.json`、检查点、`routing-candidates.json`、`training-complete.json` |
| 路由 | 路由预测、执行记录及用量统计；预测文件路径由命令输出给出 |

请保留相互关联的运行目录。后续阶段会校验来源记录和训练产物，而不仅是读取最终 JSON。

## 📝 论文与引用

**The Trinity: Capability-Driven Recursive Self-Improvement for Multimodal Agents**

The Trinity Research Team, 2026.

[阅读技术报告](paper/The-Trinity.pdf) · [访问项目主页](https://trinity-rsi.github.io/)

```bibtex
@misc{tang2026trinity,
  title={The Trinity: Capability-Driven Recursive Self-Improvement for Multimodal Agents},
  author={Tang, Weidong and Wang, Ruiheng and Zhang, Jingxuan and Wang, Hexin and Chen, Haoyuan and Zhang, Zhengfeiyang and Ma, Yixing and Jiang, Zichen and Guo, Ziyu and Li, Haodong and Jiao, Zhengbo and Cui, Zhiqing and Yin, Xinxiang and Liang, Shuo and Wan, Zhenglin and Lin, Hongzhan and Zhao, Wangbo and Zhang, Kaipeng and Zhou, Pengfei and Zhang, Odin and You, Yang},
  year={2026},
  eprint={2610.36077},
  archivePrefix={arXiv},
  primaryClass={cs.AI},
  doi={10.48550/arXiv.2610.36077},
  url={https://arxiv.org/abs/2610.36077}
}
```

## 📄 许可证

本项目源代码采用 [MIT 许可证](LICENSE)。外部基准、数据集与模型服务的使用须遵循各自的许可和条款。
