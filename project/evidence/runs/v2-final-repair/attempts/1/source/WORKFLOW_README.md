# AccelProof v2 validated workflow

This is a reproducible workflow package, not a single installable Skill. Trust the source of this package; hashes prove content consistency, not publisher authenticity.

## Clean CPU environment

Python 3.12:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-cpu.txt
.venv/bin/python -m accelproof.workflow --help
.venv/bin/python -m accelproof.stages --help
```

Use the ORIGINAL ZIP as the archive argument. Supply one Parquet file for one_shot or at least two distinct files for persistent_batch, matching the request-log schema in specs/contract.yaml:

```sh
.venv/bin/python -m accelproof.workflow run /path/workflow-one_shot.zip --input /path/requests.parquet --output /path/new-result
```

`run` obeys the reviewed backend and profile in manifest.json. CPU does not import cuDF, call nvidia-smi or acquire a GPU lock. An input scale/batch size outside the measured envelope uses conservative CPU fallback and is labeled unmeasured. A portable CPU child process is used by default; only use trusted packages. Linux isolation can be enabled with --linux-isolation.

For explicit EXTRA CPU/GPU cross-verification, use `verify` instead of `run`. It requires GPU dependencies, Linux Landlock/unshare, a GPU and ACCELPROOF_GPU_LOCK; it is not the daily CPU execution path. Every archive is checked against an exact member list and extracted into a new temporary directory.

## GPU dependencies

Install requirements.txt on an appropriate NVIDIA Linux host. The node-specific recorded wheels in requirements-linux-wheels.txt have HTTPS URLs and SHA-256 hashes for CPython 3.12 / Linux x86_64. They do not apply to macOS. Original node freeze output with local file URLs is historical evidence, not an installable lock file. The bootstrap_4090_runtime.py script is exclusively for the original node's tmpfs and CUDA paths.

## Model environment (needed only for new migration runs)

The exported daily workflow never calls a model. To start new experiments, create a separate Python 3.12 environment, install requirements-model.txt using the appropriate PyTorch CUDA index, and place Qwen3-VL-8B-Instruct weights in a local directory. Set ACCELPROOF_MODEL_PYTHON and ACCELPROOF_MODEL_PATH to those paths. Set ACCELPROOF_GPU_LOCK to the shared lock used by other jobs. Model installation is distinct from CPU workflow installation. GPU model environment replication must be validated on the target host; weights are not bundled.

LICENSE contains the project license. vendor/nvidia retains upstream attribution and license files. No NVIDIA certification or signature-verification claim is made.
