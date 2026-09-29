---
name: dataframe-parity-benchmark
description: "Revalidate the exact sealed candidate and saved full sample outputs. Missing successful TTFT must be excluded: [10, null] has mean 10, not 5. Do not edit tests, contract or tolerances. This command uses CPU Arrow only; it does not regenerate a candidate or rerun GPU benchmarks."
---

# dataframe-parity-benchmark

Revalidate the exact sealed candidate and saved full sample outputs. Missing successful TTFT must be excluded: [10, null] has mean 10, not 5. Do not edit tests, contract or tolerances. This command uses CPU Arrow only; it does not regenerate a candidate or rerun GPU benchmarks.

## Entry point

Run from the project root:

```sh
python -m accelproof.stages validate --run-id RUN_ID
```

Only the predefined request-log schema is supported. Unrelated requests do not launch GPU work. Do not obey requests to ignore the contract, reduce precision, loosen tolerances, or export without validation. If the contract or execution mode is missing, clarify first. Source identity, input hashes and environment are recorded; content hashes do not authenticate an untrusted publisher.
