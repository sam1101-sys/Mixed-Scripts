#!/usr/bin/env python3
import argparse
import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any

DEFAULT_PORTS = [1414]
TCP_TIMEOUT = 3.0
MQ_TIMEOUT = 4.0


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


def extract_version(text: str) -> str | None:
    # Best-effort extraction from listener errors/banners.
    m = re.search(r"\b(\d+\.\d+(?:\.\d+){0,2})\b", text)
    return m.group(1) if m else None


async def ibmmq_probe(host: str, port: int, timeout: float) -> dict[str, Any]:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    except Exception as e:
        return {"mq_detected": False, "banner": None, "version": None, "error": str(e)}

    banners: list[str] = []
    try:
        # Passive read in case listener sends immediate text.
        try:
            raw = await asyncio.wait_for(reader.read(256), timeout=1.0)
            if raw:
                banners.append(raw.decode("utf-8", errors="replace"))
        except Exception:
            pass

        # Send benign invalid preamble to elicit protocol error (read-only probe).
        writer.write(b"AMQPROBE\r\n")
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        try:
            raw2 = await asyncio.wait_for(reader.read(512), timeout=2.0)
            if raw2:
                banners.append(raw2.decode("utf-8", errors="replace"))
        except Exception:
            pass

        text = "\n".join(banners).strip()
        upper = text.upper()
        mq_detected = any(marker in upper for marker in ["AMQ", "WEBSPHERE MQ", "IBM MQ", "MQ"])

        return {
            "mq_detected": mq_detected,
            "banner": text[:2000] if text else None,
            "version": extract_version(text) if text else None,
            "error": None,
        }
    except Exception as e:
        return {"mq_detected": False, "banner": None, "version": None, "error": str(e)}
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
        "service": "ibm_mq",
        "timestamp": now_iso(),
        "transport": "tcp",
        "reachable": False,
        "mq_listener_detected": False,
        "version": None,
        "banner": None,
        "error": None,
        "evidence": [],
    }

    reachable, err = await tcp_check(host, port, TCP_TIMEOUT)
    if not reachable:
        result["error"] = f"tcp_unreachable: {err}"
        return result

    result["reachable"] = True
    result["mq_listener_detected"] = True
    result["evidence"].append({"kind": "tcp", "step": "connect", "data": {"reachable": True}})

    probe = await ibmmq_probe(host, port, MQ_TIMEOUT)
    result["banner"] = probe.get("banner")
    result["version"] = probe.get("version")
    if probe.get("mq_detected"):
        result["mq_listener_detected"] = True
    if probe.get("error"):
        result["error"] = probe["error"]

    result["evidence"].append({"kind": "ibm_mq", "step": "safe_probe", "data": probe})
    return result


async def worker(host: str, port: int, sem: asyncio.Semaphore) -> dict[str, Any]:
    async with sem:
        try:
            return await enumerate_target(host, port)
        except Exception as e:
            return {"target": host, "port": port, "service": "ibm_mq", "timestamp": now_iso(), "reachable": False, "error": f"unhandled_exception: {e}"}


async def run(targets: list[str], ports: list[int], concurrency: int) -> dict[str, Any]:
    sem = asyncio.Semaphore(max(1, concurrency))
    tasks = [worker(t, p, sem) for t in targets for p in ports]
    results = await asyncio.gather(*tasks)
    summary = {
        "total_targets": len(targets),
        "total_checks": len(tasks),
        "reachable": sum(1 for r in results if r.get("reachable")),
        "mq_listener_detected": sum(1 for r in results if r.get("mq_listener_detected")),
        "version_exposed": sum(1 for r in results if r.get("version")),
    }
    return {"generated_at": now_iso(), "service": "ibm_mq", "ports": ports, "summary": summary, "results": results}


def parse_ports(raw: str | None) -> list[int]:
    if not raw:
        return DEFAULT_PORTS[:]
    ports = sorted({int(x.strip()) for x in raw.split(",") if x.strip()})
    for p in ports:
        if p < 1 or p > 65535:
            raise ValueError(f"invalid port: {p}")
    return ports


def main() -> None:
    parser = argparse.ArgumentParser(description="Async safe IBM MQ enumerator")
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", default="ibmmq_enum_results.json")
    parser.add_argument("-p", "--ports", help="Comma-separated ports (default: 1414)")
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
