#!/usr/bin/env python3
import argparse
import asyncio
import json
from datetime import datetime, timezone
from typing import Any

DEFAULT_PORTS = [11211]
TCP_TIMEOUT = 3.0
MEM_TIMEOUT = 4.0
READ_LIMIT = 262144


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_targets(path: str) -> list[str]:
    out: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if t and not t.startswith("#"):
                out.append(t)
    return out


async def tcp_check(host: str, port: int, timeout: float) -> tuple[bool, str | None]:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True, None
    except Exception as e:
        return False, str(e)


def parse_stat_lines(text: str, prefix: str = "STAT ") -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith(prefix):
            parts = line.split()
            if len(parts) >= 3:
                out[parts[1]] = " ".join(parts[2:])
    return out


async def memcached_query(host: str, port: int, timeout: float) -> dict[str, Any]:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    except Exception as e:
        return {"ok": False, "error": str(e), "raw": ""}

    try:
        cmd = b"version\r\nstats\r\nstats slabs\r\nquit\r\n"
        writer.write(cmd)
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        data = await asyncio.wait_for(reader.read(READ_LIMIT), timeout=timeout)
        text = data.decode("utf-8", errors="replace")
        return {"ok": True, "error": None, "raw": text}
    except Exception as e:
        return {"ok": False, "error": str(e), "raw": ""}
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def enumerate_target(host: str, port: int) -> dict[str, Any]:
    result = {
        "target": host,
        "port": port,
        "service": "memcached",
        "timestamp": now_iso(),
        "transport": "tcp",
        "reachable": False,
        "memcached_detected": False,
        "version": None,
        "stats": {},
        "slabs": {},
        "error": None,
    }

    reachable, err = await tcp_check(host, port, TCP_TIMEOUT)
    if not reachable:
        result["error"] = f"tcp_unreachable: {err}"
        return result
    result["reachable"] = True

    resp = await memcached_query(host, port, MEM_TIMEOUT)
    if not resp["ok"]:
        result["error"] = f"query_failed: {resp['error']}"
        return result

    raw = resp["raw"]
    if "VERSION " in raw or "STAT " in raw:
        result["memcached_detected"] = True

    for line in raw.splitlines():
        if line.startswith("VERSION "):
            result["version"] = line.split(" ", 1)[1].strip()
            break

    result["stats"] = parse_stat_lines(raw, "STAT ")

    slabs: dict[str, dict[str, str]] = {}
    for key, value in result["stats"].items():
        if ":" in key:
            slab_id, slab_key = key.split(":", 1)
            if slab_id.isdigit():
                slabs.setdefault(slab_id, {})[slab_key] = value
    result["slabs"] = slabs

    return result


async def worker(host: str, port: int, sem: asyncio.Semaphore) -> dict[str, Any]:
    async with sem:
        try:
            return await enumerate_target(host, port)
        except Exception as e:
            return {"target": host, "port": port, "service": "memcached", "timestamp": now_iso(), "reachable": False, "error": f"unhandled_exception: {e}"}


async def run(targets: list[str], ports: list[int], concurrency: int) -> dict[str, Any]:
    sem = asyncio.Semaphore(max(1, concurrency))
    tasks = [worker(t, p, sem) for t in targets for p in ports]
    results = await asyncio.gather(*tasks)
    summary = {
        "total_targets": len(targets),
        "total_checks": len(tasks),
        "reachable": sum(1 for r in results if r.get("reachable")),
        "memcached_detected": sum(1 for r in results if r.get("memcached_detected")),
    }
    return {"generated_at": now_iso(), "service": "memcached", "ports": ports, "summary": summary, "results": results}


def parse_ports(raw: str | None) -> list[int]:
    if not raw:
        return DEFAULT_PORTS[:]
    ports = sorted({int(x.strip()) for x in raw.split(",") if x.strip()})
    for p in ports:
        if p < 1 or p > 65535:
            raise ValueError(f"invalid port: {p}")
    return ports


def main() -> None:
    parser = argparse.ArgumentParser(description="Async safe Memcached enumerator")
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", default="memcached_enum_results.json")
    parser.add_argument("-p", "--ports", help="Comma-separated ports (default: 11211)")
    parser.add_argument("-c", "--concurrency", type=int, default=20)
    args = parser.parse_args()

    targets = parse_targets(args.input)
    if not targets:
        raise SystemExit("No targets found in input file")

    payload = asyncio.run(run(targets, parse_ports(args.ports), args.concurrency))
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
