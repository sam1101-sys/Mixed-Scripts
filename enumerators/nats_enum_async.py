#!/usr/bin/env python3
import argparse
import asyncio
import json
from datetime import datetime, timezone
from typing import Any

DEFAULT_PORTS = [4222]
TCP_TIMEOUT = 3.0
NATS_TIMEOUT = 4.0


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


async def nats_probe(host: str, port: int, timeout: float) -> dict[str, Any]:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    except Exception as e:
        return {"nats_detected": False, "info": None, "pong_received": False, "error": str(e)}

    try:
        line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        text = line.decode("utf-8", errors="replace").strip()
        info = None
        detected = False
        if text.startswith("INFO "):
            detected = True
            try:
                info = json.loads(text[len("INFO "):])
            except Exception:
                info = {"raw": text[len("INFO "):][:1000]}

        writer.write(b"PING\r\n")
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        pong = await asyncio.wait_for(reader.readline(), timeout=timeout)
        pong_text = pong.decode("utf-8", errors="replace").strip().upper()

        return {
            "nats_detected": detected or pong_text.startswith("PONG"),
            "info": info,
            "initial_line": text[:1000],
            "pong_received": pong_text.startswith("PONG"),
            "error": None,
        }
    except Exception as e:
        return {"nats_detected": False, "info": None, "pong_received": False, "error": str(e)}
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
        "service": "nats",
        "timestamp": now_iso(),
        "transport": "tcp",
        "reachable": False,
        "nats_detected": False,
        "version": None,
        "server_name": None,
        "cluster": None,
        "features": {},
        "pong_received": False,
        "error": None,
    }

    reachable, err = await tcp_check(host, port, TCP_TIMEOUT)
    if not reachable:
        result["error"] = f"tcp_unreachable: {err}"
        return result
    result["reachable"] = True

    probe = await nats_probe(host, port, NATS_TIMEOUT)
    result["nats_detected"] = probe.get("nats_detected", False)
    result["pong_received"] = probe.get("pong_received", False)

    info = probe.get("info")
    if isinstance(info, dict):
        result["version"] = info.get("version")
        result["server_name"] = info.get("server_name")
        result["cluster"] = info.get("cluster")
        result["features"] = {
            "headers": info.get("headers"),
            "jetstream": info.get("jetstream"),
            "tls_required": info.get("tls_required"),
            "auth_required": info.get("auth_required"),
            "max_payload": info.get("max_payload"),
        }

    if probe.get("error"):
        result["error"] = probe["error"]

    return result


async def worker(host: str, port: int, sem: asyncio.Semaphore) -> dict[str, Any]:
    async with sem:
        try:
            return await enumerate_target(host, port)
        except Exception as e:
            return {"target": host, "port": port, "service": "nats", "timestamp": now_iso(), "reachable": False, "error": f"unhandled_exception: {e}"}


async def run(targets: list[str], ports: list[int], concurrency: int) -> dict[str, Any]:
    sem = asyncio.Semaphore(max(1, concurrency))
    tasks = [worker(t, p, sem) for t in targets for p in ports]
    results = await asyncio.gather(*tasks)
    summary = {
        "total_targets": len(targets),
        "total_checks": len(tasks),
        "reachable": sum(1 for r in results if r.get("reachable")),
        "nats_detected": sum(1 for r in results if r.get("nats_detected")),
        "pong_received": sum(1 for r in results if r.get("pong_received")),
    }
    return {"generated_at": now_iso(), "service": "nats", "ports": ports, "summary": summary, "results": results}


def parse_ports(raw: str | None) -> list[int]:
    if not raw:
        return DEFAULT_PORTS[:]
    ports = sorted({int(x.strip()) for x in raw.split(",") if x.strip()})
    for p in ports:
        if p < 1 or p > 65535:
            raise ValueError(f"invalid port: {p}")
    return ports


def main() -> None:
    parser = argparse.ArgumentParser(description="Async safe NATS enumerator")
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", default="nats_enum_results.json")
    parser.add_argument("-p", "--ports", help="Comma-separated ports (default: 4222)")
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
