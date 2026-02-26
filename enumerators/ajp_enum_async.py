#!/usr/bin/env python3
import argparse
import asyncio
import json
from datetime import datetime, timezone
from typing import Any

DEFAULT_PORTS = [8009]
TCP_TIMEOUT = 3.0
AJP_TIMEOUT = 4.0


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_targets(path: str) -> list[str]:
    targets: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if t and not t.startswith("#"):
                targets.append(t)
    return targets


async def tcp_check(host: str, port: int, timeout: float) -> tuple[bool, str | None]:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True, None
    except Exception as e:
        return False, str(e)


async def ajp_cping_probe(host: str, port: int, timeout: float) -> dict[str, Any]:
    # AJP13 CPING: magic 0x1234, packet length 1, payload 0x0A.
    cping = b"\x12\x34\x00\x01\x0A"
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    except Exception as e:
        return {
            "ajp13_detected": False,
            "cpong_received": False,
            "raw_response_hex": None,
            "error": str(e),
        }

    try:
        writer.write(cping)
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        response = await asyncio.wait_for(reader.read(64), timeout=timeout)
        raw_hex = response.hex() if response else None
        cpong = len(response) >= 5 and response[:5] == b"\x41\x42\x00\x01\x09"
        ajp13 = cpong or (len(response) >= 2 and response[:2] in (b"\x12\x34", b"AB"))
        return {
            "ajp13_detected": ajp13,
            "cpong_received": cpong,
            "raw_response_hex": raw_hex,
            "error": None,
        }
    except Exception as e:
        return {
            "ajp13_detected": False,
            "cpong_received": False,
            "raw_response_hex": None,
            "error": str(e),
        }
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
        "service": "ajp",
        "timestamp": now_iso(),
        "transport": "tcp",
        "reachable": False,
        "ajp13_detected": False,
        "cpong_received": False,
        "supported_methods": [],
        "method_probe_note": "AJP method enumeration requires mapped app context; safe unauth probe does not force backend requests.",
        "evidence": [],
        "error": None,
    }

    reachable, err = await tcp_check(host, port, TCP_TIMEOUT)
    if not reachable:
        result["error"] = f"tcp_unreachable: {err}"
        return result

    result["reachable"] = True
    result["evidence"].append({"kind": "tcp", "step": "connect", "data": {"reachable": True}})

    probe = await ajp_cping_probe(host, port, AJP_TIMEOUT)
    result["ajp13_detected"] = probe["ajp13_detected"]
    result["cpong_received"] = probe["cpong_received"]
    result["evidence"].append({"kind": "ajp", "step": "cping_cpong", "data": probe})

    return result


async def worker(host: str, port: int, sem: asyncio.Semaphore) -> dict[str, Any]:
    async with sem:
        try:
            return await enumerate_target(host, port)
        except Exception as e:
            return {
                "target": host,
                "port": port,
                "service": "ajp",
                "timestamp": now_iso(),
                "reachable": False,
                "error": f"unhandled_exception: {e}",
            }


async def run(targets: list[str], ports: list[int], concurrency: int) -> dict[str, Any]:
    sem = asyncio.Semaphore(max(1, concurrency))
    tasks = [worker(t, p, sem) for t in targets for p in ports]
    results = await asyncio.gather(*tasks)

    summary = {
        "total_targets": len(targets),
        "total_checks": len(tasks),
        "reachable": sum(1 for r in results if r.get("reachable")),
        "ajp13_detected": sum(1 for r in results if r.get("ajp13_detected")),
        "cpong_received": sum(1 for r in results if r.get("cpong_received")),
    }

    return {
        "generated_at": now_iso(),
        "service": "ajp",
        "ports": ports,
        "summary": summary,
        "results": results,
    }


def parse_ports(raw: str | None) -> list[int]:
    if not raw:
        return DEFAULT_PORTS[:]
    ports = sorted({int(p.strip()) for p in raw.split(",") if p.strip()})
    for p in ports:
        if p < 1 or p > 65535:
            raise ValueError(f"invalid port: {p}")
    return ports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Async safe AJP enumerator")
    parser.add_argument("-i", "--input", required=True, help="Input hosts file (one host/IP per line)")
    parser.add_argument("-o", "--output", default="ajp_enum_results.json", help="Output JSON")
    parser.add_argument("-p", "--ports", help="Comma-separated ports (default: 8009)")
    parser.add_argument("-c", "--concurrency", type=int, default=20, help="Concurrent checks")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    targets = parse_targets(args.input)
    if not targets:
        raise SystemExit("No targets found in input file")
    ports = parse_ports(args.ports)

    payload = asyncio.run(run(targets, ports, args.concurrency))
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
