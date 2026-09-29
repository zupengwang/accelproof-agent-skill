# AccelProof v2 验速工坊

受限决策与验收工作台：模型选择受审计的读取策略和实验顺序；独立验证器判定语义，实际部署模式测量决定后端。不能称为通用自主 GPU 代码优化器。

完整项目包含前端、控制器、四个职责明确的业务 Skills、固定版本 NVIDIA Skill、测试、证据和文档。精简导出 ZIP 有独立的 WORKFLOW_README.md，不要求模型参与日常复用。

## 入口

先在 Python 3.12 环境安装 requirements-cpu.txt；运行测试前另装 requirements-dev.txt；GPU 实验另装 requirements.txt，并配置本地模型环境（见 WORKFLOW_README.md）。

```sh
python -m accelproof.stages intake --scenario small --execution-profile one_shot
python -m accelproof.stages migrate --scenario small --execution-profile one_shot
python -m accelproof.stages validate --run-id RUN_ID
python -m accelproof.stages export --run-id RUN_ID --execution-profile one_shot --approved
python -m uvicorn accelproof.server:app --host 127.0.0.1 --port 8766
python -m unittest discover -s tests -v
```

运行模式为 one_shot（一次新进程）或 persistent_batch（同一 worker 处理多个不同输入，包含初始化与总批次时间）。预热后 CPU/GPU 比值是单独测量字段，不自动形成 GPU 建议。缺少模式测量不能有效导出；新数据超出已测规模则保守回退 CPU。

每个候选在验证前冻结策略、模板、判卷规则、输入和环境；导出只能使用这份快照。修改任何受保护文件须重新验证。此绑定防止意外修改，不对能重写整个证据目录的所有者提供真实性保证。

服务仅监听 loopback；候选为固定审计模板，Linux GPU worker 有网络命名空间、Landlock 与资源限制，不接受任意 Python。API 持久化控制器进程身份并在重启时协调；未确认的存活组阻止新任务。可选 profiler 在本项目中被定义为必需验证环节，其失败导致最终失败。

上游固定提交 d8519c57da6db5d9bea274ec1724a4a7a56a3dee。全部正式性能实验为 RTX 4090；不冒称 DGX Spark 测量。v1 记录属于旧实现，不为 v2 提供通过状态。本地交付不等于公开发表或赛事提交。

## 本地证据复核与数据

本版最终记录在 `evidence/runs/v2-final-*`，历史开发轮次未混入。`evidence/final-review-acceptance.json` 核对源码、候选、产物和实际复用的 ZIP 摘要。

```sh
PYTHONPATH=. python scripts/review_acceptance.py
python -m accelproof.data /tmp/requests-1000.parquet --rows 1000 --seed 20260930
```

`examples/requests-1000-20260930.parquet` 是干净 CPU 测试实际使用的合成输入。可用交付目录的小数据工作流 ZIP 复用此文件；输出路径必须是新的空目录。

完整 GPU 实验需要配置共享 GPU 锁与模型环境，详情见 `WORKFLOW_README.md`。不要将 CPU-only 入口检查理解为 GPU 环境已可用。
