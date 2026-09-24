# PoW CUDA Mint Template

A credential-free starting point for EVM proof-of-work mints. It separates GPU hashing from live chain state, CPU verification, simulation, local signing, and transaction broadcast.

**Status:** template only. It deliberately cannot mine or submit until the target protocol is reverse-engineered and the TODO functions are implemented.

## What this template covers

```text
contract/frontend source
        │
        ├─ exact byte layout + target + nonce field
        │
GPU worker ── verified candidate ──> CPU recomputation
                                           │
                                    eth_call simulation
                                           │
                               local signer + broadcast
                                           │
                                  receipt/event verification
```

- Persistent CUDA worker protocol used by [`asbryx/universal-cuda-miner`](https://github.com/asbryx/universal-cuda-miner).
- SHA-256 or Ethereum Keccak-256 layouts.
- Strict PoW target rule: `digest < target`.
- CPU re-verification of every GPU candidate.
- `eth_call` simulation before signing.
- Local transaction signing and raw transaction broadcast.

## Files

```text
miner.py                 Coordinator template. Private-key placeholder: line 19.
requirements.txt         Python runtime dependencies.
tests/test_template.py   Credential-free and required-gate checks.
.gitignore               Blocks common local secrets and build outputs.
```

## Private key configuration

`miner.py` line **19** contains an empty placeholder:

```python
PRIVATE_KEY = ""
```

For a standalone burner deployment, replace only the empty string with its private key. The template intentionally ships with no key, RPC URL, contract address, wallet, transaction data, or chain-specific state.

Do not commit after adding a key. `.gitignore` cannot protect a secret written into an already tracked `miner.py`.

## Setup

Requirements:

- Linux host with NVIDIA GPU.
- NVIDIA driver compatible with the selected CUDA toolkit.
- CUDA development image/toolkit with `nvcc`.
- Python 3.10+.

Recommended Vast.ai image:

```text
nvidia/cuda:12.4.1-devel-ubuntu22.04
```

Install Python dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt pytest
pytest -q
```

Clone and build the CUDA worker:

```bash
git clone https://github.com/asbryx/universal-cuda-miner
cd universal-cuda-miner
nvcc -O3 -std=c++17 -arch=sm_89 cuda/universal_cuda_miner.cu -o ../universal_cuda_miner
python scripts/cuda_preflight.py --worker ../universal_cuda_miner
```

For RTX 4090, `sm_89` is the correct architecture flag. Do not call a GPU ready based on `nvidia-smi` alone: `cuda_preflight.py` and `--self-test` must pass.

## Integration checklist

A new PoW protocol must pass every step before any live broadcast.

1. Extract the exact hash specification from verified contract source or the official client.
2. Identify the packed preimage: every fixed field, width, ordering, padding, nonce offset, and endianness.
3. Identify the exact hash primitive. Ethereum uses Keccak-256, **not** NIST `sha3_256`.
4. Identify target semantics. This template assumes strict `digest < target`; verify if the target is per-user or global.
5. Create at least three CPU golden vectors: nonce `0`, nonce `1`, and a nonce near `2^32`.
6. Implement `refresh_job()` to read every live field that invalidates work: seed, previous work, target, anchor, count, price, supply, or epoch.
7. Implement `verify_solution()` using the exact packed bytes. Compare its digest to an on-chain view such as `digestOf()` when available.
8. Implement `mint_calldata()` only after validating the ABI selector, parameters, payable value, and price cap.
9. Generate `GPU_JOB` from the same adapter/template used by CPU verification. Never hand-copy offsets.
10. Run CUDA self-test, then compare GPU hashes against all golden vectors.
11. On a valid candidate: re-read live state, CPU verify, `eth_call`, sign, broadcast, wait receipt, decode mint event.
12. Stop or refresh immediately when another miner changes a global challenge/anchor.

## CUDA worker protocol

`universal_cuda_miner` accepts one job per stdin line:

```text
job ID PROTOCOL ALGORITHM NONCE_OFFSET NONCE_WIDTH TEMPLATE_HEX TARGET_HEX START_HEX COUNT STEP
```

- `TEMPLATE_HEX`: complete packed public message; nonce bytes zeroed.
- `NONCE_OFFSET` / `NONCE_WIDTH`: byte positions, not 32-bit word indexes.
- `START_HEX`, `COUNT`, `STEP`: split work across workers without overlap.
- `ALGORITHM`: `sha256` or Ethereum `keccak256`.
- A reported solution still requires independent CPU verification.

Supported reference layouts in the upstream worker:

| Layout | Hash | Message |
|---|---|---|
| `hashbroker84` | SHA-256 | address[20] + zero[24] + nonce[8] + challenge[32] |
| `hashcats116` | Keccak-256 | address[20] + nonce[32] + prev[32] + anchor[32] |
| `minerpotatos116` | Keccak-256 | address[20] + prevWork[32] + anchor[32] + nonce[32] |
| `prspct84` | Keccak-256 | seed[32] + address[20] + nonce[32] |

Custom protocols need a new layout and golden-vector tests. Do not force them into a similar layout.

## Coordinator behavior

`miner.py` intentionally has four integration boundaries:

- `refresh_job(rpc, address)`: read chain state and return public job fields.
- `verify_solution(job, nonce)`: build the exact preimage and check strict target.
- `mint_calldata(job, nonce)`: ABI-encode the real mint call and native value.
- `simulate_mint(...)`: preflight with `eth_call`; only then call `broadcast_mint(...)`.

The default hashing body is intentionally wrong for real protocols. It is a placeholder that fails fast until replaced with protocol-specific logic.

## Operations

- One persistent CUDA process per GPU.
- Give each worker a disjoint nonce range: `start + i * step`.
- Poll/re-read state at short intervals for FCFS/global-race mints.
- Keep a best candidate locally while polling, but discard it when fields affecting the hash change.
- Never trust an unusually high hashrate. A result outside a plausible hardware range usually indicates skipped work or a broken kernel.
- Do not put a production wallet on a rental GPU. Use only an explicitly funded burner.

## Economic gate

Before renting a GPU, calculate:

```text
expected work = 2^difficulty_bits
share = your_hashrate / (network_hashrate + your_hashrate)
expected time = average_mint_interval / share
cost per NFT = rental/hour × expected hours + gas + mint price
```

Set hard caps for price, gas, supply, difficulty, runtime, and burner balance. Stop when any cap is crossed.

## Verification commands

```bash
pytest -q
python -m py_compile miner.py
```

## Security model

The upstream CUDA worker receives only public job data. This repository is a template, not a production miner. It has no credentials by default, and all chain-specific transaction construction remains TODO until verified against the target contract.

Never assume a frontend's displayed price, target, selector, or “free mint” claim is authoritative. Verify source and live chain state first.
