#!/usr/bin/env python3
import argparse
import asyncio
import json
from datetime import datetime, timezone

DEFAULT_PORTS = [5672]
TCP_TIMEOUT = 3.0
AMQP_TIMEOUT = 4.0


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_targets(path: str) -> list[str]:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if t and not t.startswith("#"):
                out.append(t)
    return out


async def tcp_check(host: str, port: int, timeout: float):
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True, None
    except Exception as e:
        return False, str(e)


async def amqp_probe(host: str, port: int, timeout: float):
    # AMQP 0-9-1 protocol header.
    hdr = b"AMQP\x00\x00\x09\x01"
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    except Exception as e:
        return {"amqp_detected": False, "protocol_header_accepted": False, "response_hex": None, "error": str(e)}

    try:
        writer.write(hdr)
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        data = await asyncio.wait_for(reader.read(64), timeout=timeout)
        response_hex = data.hex() if data else None
        detected = bool(data)
        return {
            "amqp_detected": detected,
            "protocol_header_accepted": detected,
            "response_hex": response_hex,
            "error": None,
        }
    except Exception as e:
        return {"amqp_detected": False, "protocol_header_accepted": False, "response_hex": None, "error": str(e)}
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def enumerate_target(host: str, port: int):
    result = {
        "target": host,
        "port": port,
        "service": "amqp",
        "timestamp": now_iso(),
        "transport": "tcp",
        "reachable": False,
        "amqp_detected": False,
        "protocol_header_accepted": False,
        "response_hex": None,
        "error": None,
    }
    reachable, err = await tcp_check(host, port, TCP_TIMEOUT)
    if not reachable:
        result["error"] = f"tcp_unreachable: {err}"
        return result

    result["reachable"] = True
    probe = await amqp_probe(host, port, AMQP_TIMEOUT)
    result.update(probe)
    return result


async def worker(host: str, port: int, sem: asyncio.Semaphore):
    async with sem:
        try:
            return await enumerate_target(host, port)
        except Exception as e:
            return {"target": host, "port": port, "service": "amqp", "timestamp": now_iso(), "reachable": False, "error": f"unhandled_exception: {e}"}


async def run(targets: list[str], ports: list[int], concurrency: int):
    sem = asyncio.Semaphore(max(1, concurrency))
    tasks = [worker(t, p, sem) for t in targets for p in ports]
    results = await asyncio.gather(*tasks)
    summary = {
        "total_targets": len(targets),
        "total_checks": len(tasks),
        "reachable": sum(1 for r in results if r.get("reachable")),
        "amqp_detected": sum(1 for r in results if r.get("amqp_detected")),
    }
    return {"generated_at": now_iso(), "service": "amqp", "ports": ports, "summary": summary, "results": results}


def parse_ports(raw: str | None):
    if not raw:
        return DEFAULT_PORTS[:]
    ports = sorted({int(x.strip()) for x in raw.split(",") if x.strip()})
    for p in ports:
        if p < 1 or p > 65535:
            raise ValueError(f"invalid port: {p}")
    return ports


def main():
    parser = argparse.ArgumentParser(description="Async safe AMQP enumerator")
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", default="amqp_enum_results.json")
    parser.add_argument("-p", "--ports", help="Comma-separated ports (default: 5672)")
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
