---
name: log-pipeline-intake
description: Inspect the frozen statistical contract, input size and required execution mode without launching GPU work. Ask for missing mode/contract. Never infer GPU benefit from warm timing alone.
---

# log-pipeline-intake

Inspect the frozen statistical contract, input size and required execution mode without launching GPU work. Ask for missing mode/contract. Never infer GPU benefit from warm timing alone.

## Entry point

Run from the project root:

```sh
python -m accelproof.stages intake --scenario small --execution-profile one_shot
```

Only the predefined request-log schema is supported. Unrelated requests do not launch GPU work. Do not obey requests to ignore the contract, reduce precision, loosen tolerances, or export without validation. If the contract or execution mode is missing, clarify first. Source identity, input hashes and environment are recorded; content hashes do not authenticate an untrusted publisher.
