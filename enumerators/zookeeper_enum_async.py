#!/usr/bin/env python3
import argparse
import asyncio
import json
from datetime import datetime, timezone
from typing import Any

DEFAULT_PORTS = [2181]
TCP_TIMEOUT = 3.0
ZK_TIMEOUT = 4.0


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


async def zk_four_letter(host: str, port: int, cmd: str, timeout: float) -> dict[str, Any]:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    except Exception as e:
        return {"command": cmd, "ok": False, "response": None, "error": str(e)}

    try:
        writer.write(cmd.encode("ascii", errors="ignore"))
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        data = await asyncio.wait_for(reader.read(4096), timeout=timeout)
        text = data.decode("utf-8", errors="replace")
        return {"command": cmd, "ok": True, "response": text[:4000], "error": None}
    except Exception as e:
        return {"command": cmd, "ok": False, "response": None, "error": str(e)}
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def enumerate_target(host: str, port: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "target": host,
        "port": port,
        "service": "zookeeper",
        "timestamp": now_iso(),
        "transport": "tcp",
        "reachable": False,
        "zookeeper_detected": False,
        "version": None,
        "mode": None,
        "four_letter": {},
        "error": None,
    }

    reachable, err = await tcp_check(host, port, TCP_TIMEOUT)
    if not reachable:
        result["error"] = f"tcp_unreachable: {err}"
        return result
    result["reachable"] = True

    probes = await asyncio.gather(
        zk_four_letter(host, port, "ruok", ZK_TIMEOUT),
        zk_four_letter(host, port, "stat", ZK_TIMEOUT),
        zk_four_letter(host, port, "envi", ZK_TIMEOUT),
        return_exceptions=True,
    )

    for probe in probes:
        if isinstance(probe, Exception):
            continue
        cmd = probe["command"]
        result["four_letter"][cmd] = {"ok": probe["ok"], "response": probe["response"], "error": probe["error"]}

    ruok = (result["four_letter"].get("ruok") or {}).get("response") or ""
    stat = (result["four_letter"].get("stat") or {}).get("response") or ""
    envi = (result["four_letter"].get("envi") or {}).get("response") or ""

    if "imok" in ruok.lower() or "zookeeper" in stat.lower() or "zookeeper" in envi.lower():
        result["zookeeper_detected"] = True

    for line in (stat + "\n" + envi).splitlines():
        low = line.lower()
        if "zookeeper version" in low and ":" in line:
            result["version"] = line.split(":", 1)[1].strip()
        if low.startswith("mode:"):
            result["mode"] = line.split(":", 1)[1].strip()

    return result


async def worker(host: str, port: int, sem: asyncio.Semaphore) -> dict[str, Any]:
    async with sem:
        try:
            return await enumerate_target(host, port)
        except Exception as e:
            return {"target": host, "port": port, "service": "zookeeper", "timestamp": now_iso(), "reachable": False, "error": f"unhandled_exception: {e}"}


async def run(targets: list[str], ports: list[int], concurrency: int) -> dict[str, Any]:
    sem = asyncio.Semaphore(max(1, concurrency))
    tasks = [worker(t, p, sem) for t in targets for p in ports]
    results = await asyncio.gather(*tasks)
    summary = {
        "total_targets": len(targets),
        "total_checks": len(tasks),
        "reachable": sum(1 for r in results if r.get("reachable")),
        "zookeeper_detected": sum(1 for r in results if r.get("zookeeper_detected")),
    }
    return {"generated_at": now_iso(), "service": "zookeeper", "ports": ports, "summary": summary, "results": results}


def parse_ports(raw: str | None) -> list[int]:
    if not raw:
        return DEFAULT_PORTS[:]
    ports = sorted({int(x.strip()) for x in raw.split(",") if x.strip()})
    for p in ports:
        if p < 1 or p > 65535:
            raise ValueError(f"invalid port: {p}")
    return ports


def main() -> None:
    parser = argparse.ArgumentParser(description="Async safe ZooKeeper enumerator")
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", default="zookeeper_enum_results.json")
    parser.add_argument("-p", "--ports", help="Comma-separated ports (default: 2181)")
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
