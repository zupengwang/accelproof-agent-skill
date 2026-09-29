# AccelProof 验速工坊

受限决策与验收工作台：先证明算对，再测实际部署成本，最后导出与已验证候选绑定的工作流。

## 在线材料

| 内容 | 访问入口 |
| --- | --- |
| 项目及报告 | [https://zupengwang.github.io/accelproof-agent-skill/](https://zupengwang.github.io/accelproof-agent-skill/) · [完整报告](https://zupengwang.github.io/accelproof-agent-skill/report/) |
| Demo 视频 | [https://zupengwang.github.io/accelproof-agent-skill/demo/](https://zupengwang.github.io/accelproof-agent-skill/demo/)（3 分 14 秒，中文 AI 配音与字幕） |
| 参赛征文 | [https://zupengwang.github.io/accelproof-agent-skill/essay/](https://zupengwang.github.io/accelproof-agent-skill/essay/) |
| 完整提交包 | [v2.1 Release](https://github.com/zupengwang/accelproof-agent-skill/releases/tag/v2.1) |
| 交互预览 | [冻结数据的离线预览](https://zupengwang.github.io/accelproof-agent-skill/preview/) |

## 本次实验告诉我们什么

- RTX 4090、500 万行合成日志：预热后同构 CPU/GPU 比值 **13.264×**。
- 一次新进程：CPU **1.870 s**，GPU **18.831 s**；实测建议 **CPU**。
- 同进程处理两个不同输入：CPU **3.025 s**，GPU **18.979 s**；实测建议 **CPU**。
- 主动注入的空值错误候选 **14/18**，修复后 **18/18**；失败证据保留。
- 12 个冻结规划任务里，业务 Skills 与组合条件为 **12/12**，固定规则为 **11/12**。这不是 GPU 端到端成功率，也不能证明模型普遍优于规则。

暖态预热 1 次后测 3 次，部署模式各观测 1 次；未清除文件缓存。全部硬件实验为 RTX 4090，未宣称 DGX Spark 实测。

## 源码与复用

[project/README.md](project/README.md) 是项目入口；[project/WORKFLOW_README.md](project/WORKFLOW_README.md) 说明 CPU 复用、GPU 与模型依赖。源码、四个业务 Skills、测试与主要证据都在 `project/`。

在 Python 3.12 环境下：

```sh
cd project
python3 -m venv .venv
.venv/bin/pip install -r requirements-cpu.txt
.venv/bin/python -m accelproof.workflow --help
.venv/bin/python -m accelproof.stages --help
```

日常工作流 `run` 遵从已审核的后端建议；CPU 分支不依赖 cuDF 或模型。完整 GPU/模型环境需按文档在适合的 Linux NVIDIA 主机独立准备。

## 原件与发布范围

v2.1 只调整视频配音、字幕与节奏，报告和实验结果沿用已核验 v2。完整提交包采用 ASCII 文件名发布，字节与本地原包一致：

```text
d3179928a51bd5e60c5e5982f805f01a3946bea4efb38f7635b0e38129e5c80c  AccelProof-v2.1-submission.zip
```

Git 仓库不重复存储 CUDA 编译缓存、中间音视频和 PDF 排版核验图，完整原件均在 Release ZIP 中。保留的项目文件按字节复制，范围记录在 [publication/provenance.json](publication/provenance.json)。复核完整交付清单时应下载、解压 Release 包，而不是对精简仓库运行完整包校验脚本。

原件与历史证据中的“尚未公开”“本地材料”是生成时状态。此仓库于 2026-09-29 发布；**公开材料不等于已向赛事投稿或取得接收回执**。

开发与材料制作使用 Codex 辅助，视频使用 AI 合成语音。固定 NVIDIA Skill 提交为 `d8519c57da6db5d9bea274ec1724a4a7a56a3dee`，上游许可和签名文件原样保留；未宣称密码学签名验证或 NVIDIA 官方认证。项目许可见 [LICENSE](LICENSE)，上游归属见 [project/vendor/nvidia](project/vendor/nvidia)。
