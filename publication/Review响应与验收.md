# AccelProof v2 Review 响应与验收

版本：2026-09-28 / v2.0。保留原选题、原生前端和受限模板，未扩展为任意 Python 执行平台。原 v1 交付包保持不变；以下证据均来自修订后的 v2-final-* 候选。

## 逐项响应

路径均相对本提交包的 project/。

| 项目 | 状态 | 改动与边界 | 证据 |
| --- | --- | --- | --- |
| R01 | 完成 | 验证前冻结候选，控制器独占生成验证记录；导出核对策略、源码、契约、判卷规则及产物。 | tests/test_review.py；evidence/final-review-acceptance.json |
| R02 | 完成 | run 遵从审核后的后端；verify 才显式进行 CPU/GPU 双路复核。无 GPU 工具与 cuDF 的干净 CPU 环境成功运行。 | evidence/clean-cpu/result.json、acceptance.json、reference-parity.json |
| R03 | 完成 | 实际实现 one_shot 与 persistent_batch；批次使用同一 worker PID 处理两份不同种子数据。UI、manifest 与执行一致。 | evidence/runs/v2-final-large/*-measurements.json；evidence/reuse-batch/result.json |
| R04 | 完成 CPU 验收 | 独立工作流 README、可移植 CPU 依赖、HTTPS+哈希 Linux wheel 清单、单独模型安装说明及许可。干净 CPU 目录完成安装、导入、help 和 run。GPU/模型从零安装未复验。 | WORKFLOW_README.md；requirements-*.txt；evidence/clean-cpu/ |
| R05 | 完成 | FINALIZING 收尾后才原子提交终态；profiler 定义为必需环节，失败导致失败终态。延迟和失败均有 SSE 回归。 | tests/test_api_review.py；evidence/review-unit-tests.log |
| R06 | 完成 | 保存 PID、启动时间、命令、进程组及 boot ID。可确认时恢复监管与取消；未知身份阻止调度，已失联任务明确标记。 | accelproof/lifecycle.py；tests/test_review.py |
| R07 | 完成 | activeRun 与查看记录分离；活动任务横幅和取消入口持续保留；事件连接与选择令牌防止旧响应覆盖。 | web/app.js；evidence/frontend-regression.json |
| R08 | 完成 | 按 run_id/attempt 读取冻结策略和模板，修复前后可追踪；检查详情先显示 10 与 5。 | evidence/runs/v2-final-repair/attempts/；media/source/screenshots/ |
| R09 | 完成 | 四个 Skill 分别调用 intake、migrate、validate、export；导出只处理既有 run_id。迁移与修复按阶段加载技能。 | accelproof/stages.py；skills/*/scripts/run.py；evidence/skills-validation.log |
| R10 | 完成有限增强 | 增加 full/projected 实际读取选择、下一项部署模式实验选择，并实跑固定规则基线。仍是受限策略；不宣称模型优于规则。 | evidence/executed-baseline-comparison.json；accelproof/model.py、worker.py |
| R11 | 完成 | 12 个冻结任务，四种模型上下文加规则，共 48 次模型生成与 12 次规则评分；同一验证器，保留负向结果。 | specs/agent-evals-v2.json；evidence/agent-eval/ |
| R12 | 完成 | 每次在全新临时目录解包，核对精确成员集合、全部哈希及候选绑定；拒绝额外代码、路径越界、符号链接和特殊成员。 | accelproof/proof.py；tests/test_review.py |

## 实测结果

- 42 项回归测试通过，4 个业务 Skill 元数据校验通过。
- 最终五个运行的 92 个受保护文件均与本包源码一致；候选、验证记录和已验证产物的哈希逐一核对。故障运行保持 FAILED，未进入测速。
- 500 万行暖态同构 CPU/GPU 比值 13.2636×；原始 pandas/最终 GPU 整体比值 37.7842×，不能把全部收益归给 GPU。
- 一次新进程：CPU 1.8699s，GPU 18.8311s，建议 CPU。各后端一次观测，未清文件缓存。
- 同进程两份不同输入：CPU 3.0247s，GPU 18.9789s，建议 CPU。各后端一次观测，未清文件缓存。
- 新种子 CPU 复用：selected_backend=cpu、model_called=false、gpu_worker_called=false；GPU 查询失败哨兵未被调用，与原始 pandas 独立全表比较 PASS。
- 500 万行第二份数据显式 CPU/GPU verify 一致性通过；常驻批次日常复用使用 CPU。最终工作流 ZIP 摘要与复用记录完全对应。

| 策略评测条件 | 通过 | 错误采用 | 输入/输出 tokens | 规划总秒数 | 工具调用 |
| --- | --- | --- | --- | --- | --- |
| 无 Skills | 10/12 | 0 | 2101/423 | 17.38483 | 0 |
| 仅官方 | 7/12 | 1 | 29845/425 | 19.27381 | 0 |
| 仅业务 | 12/12 | 0 | 14545/430 | 17.65727 | 0 |
| 官方+业务 | 12/12 | 0 | 42289/426 | 20.83078 | 0 |
| 固定规则 | 11/12 | 0 | 0/0 | 0.00009 | 0 |

上表是策略题评分，工具调用为零，不是 GPU 端到端成功率。另有真实执行基线：

| 运行 | 完成秒数 | 模型请求 | 隔离 worker 次数 | 结果 |
| --- | --- | --- | --- | --- |
| v2-final-small | 108.466 | 1 | 13 | PASS |
| v2-final-rule | 94.873 | 0 | 13 | PASS |

每组仅一次，worker 次数按保存的 sandbox.json 计数，不是模型 function calling。固定规则在该流程更快；模型的必要性和泛化收益尚未得到充分证明。

## 材料与展示

报告增加架构、错误值、真实策略修复、不同运行口径、后端落实和消融；征文围绕填零错误、暖态指标与部署差异、验证后文件漂移三个工程取舍。视频五段使用真实交互录屏，其中 CPU 段实际启动干净环境；长等待不伪装为现场秒级完成，旁白明确为合成。离线预览可切换历史、attempt、部署模式及检查详情，禁止启动和重新导出。

## 尚未完成的外部动作

本包只作本地交付，未创建公开仓库、未发布网站或视频、未填写赛事表单。原提交表要求的三个可访问网址仍待后续授权发布，不能把本地文件路径当作提交网址。GPU/模型环境使用既有 4090 环境完成实验；没有将 CPU 干净环境测试冒充 GPU 从零安装验证。RTX 4090 实测不等于 DGX Spark 实测，是否满足赛事硬件要求需依据完整官方规则确认。
