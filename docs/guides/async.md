# Async client

`qkdsec.client.aio.AsyncETSI014Client` is the asyncio-native counterpart to the synchronous `ETSI014Client`. It uses [httpx](https://www.python-httpx.org/) under the hood and has the same method surface — anything you can do with the sync client, you can do with `await`.

## Install

```bash
pip install "qkdsec[async]"
```

The `async` extra adds `httpx>=0.27`. The sync client and async client can coexist; pick whichever fits the surrounding code.

## Usage

### Context-manager style

```python
import asyncio
from qkdsec.client.aio import AsyncETSI014Client


async def main():
    async with AsyncETSI014Client(
        "https://kme.example.com",
        client_cert=("alice.crt", "alice.key"),
    ) as kme:
        status = await kme.status("sae-bob")
        keys = await kme.get_enc_keys("sae-bob", number=1, size=256)
        print(keys[0].key.hex())


asyncio.run(main())
```

The `async with` form is the recommended pattern — it ensures the underlying httpx client is closed cleanly even on exception paths.

### Manual lifecycle

```python
kme = AsyncETSI014Client(...)
try:
    await kme.status("sae-bob")
finally:
    await kme.aclose()
```

### Re-using an httpx client

For advanced configuration (custom transport, mounts, connection pool tuning), build your own `httpx.AsyncClient` and pass it in:

```python
import httpx
from qkdsec.client.aio import AsyncETSI014Client

http = httpx.AsyncClient(
    cert=("alice.crt", "alice.key"),
    verify="ca.crt",
    timeout=httpx.Timeout(10.0, connect=5.0),
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
)
async with AsyncETSI014Client("https://kme.example.com", client=http) as kme:
    await kme.status("sae-bob")
```

When you pass `client=`, `AsyncETSI014Client` does **not** own the lifecycle. Close it yourself.

## Concurrency patterns

### Parallel key fetches

```python
async with AsyncETSI014Client(...) as kme:
    batches = await asyncio.gather(*[
        kme.get_enc_keys("sae-bob", number=10, size=256)
        for _ in range(5)
    ])
    all_keys = [k for batch in batches for k in batch]
```

### Pipelined enc → dec

```python
async with AsyncETSI014Client(...) as alice, \
           AsyncETSI014Client(...) as bob:
    keys = await alice.get_enc_keys("sae-bob", number=1, size=256)
    mirror = await bob.get_dec_keys("sae-bob", key_ids=[keys[0].key_id])
    assert mirror[0].key == keys[0].key
```

### Background key replenishment

```python
async def keep_pool_full(kme, pool, target=20):
    while True:
        if len(pool) < target:
            new = await kme.get_enc_keys("sae-bob", number=target - len(pool))
            pool.extend(new)
        await asyncio.sleep(1.0)
```

## Error handling

The same exception hierarchy applies as in the sync client:

```python
from qkdsec.client import KMEError, KMEHTTPError, KMENotFoundError

try:
    keys = await kme.get_dec_keys("sae-bob", key_ids=["missing"])
except KMENotFoundError:
    ...  # 404: key_ID not in the pending pool (already consumed?)
except KMEHTTPError as e:
    ...  # other 4xx/5xx; e.status_code and e.message available
except KMEError:
    ...  # transport-level issues
```

## Spec coverage

Every parameter on the sync client is available on the async client with identical semantics — see the [spec coverage guide](spec-coverage.md) for multicast and extensions.

```python
keys = await kme.get_enc_keys(
    "sae-bob",
    number=1,
    size=256,
    additional_slave_sae_ids=["sae-charlie", "sae-dave"],
    extension_optional=[{"route_type": "primary"}],
)
```

## When to use which

- **Sync** is fine for scripts, the CLI, and codebases that are not already async. The doctor probe is sync internally for exactly this reason — it has no shared state with the host application.
- **Async** is the right choice when the surrounding code is already async (FastAPI, aiohttp services, asyncio-based background workers) or when you need to fan out many concurrent KME requests.
