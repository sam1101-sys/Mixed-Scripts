#!/usr/bin/env python3
import argparse
import asyncio
import json
import random
import string
from datetime import datetime, timezone
from typing import Any

DEFAULT_PORTS = [1883]
TCP_TIMEOUT = 3.0
MQTT_TIMEOUT = 4.0


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


def encode_remaining_length(value: int) -> bytes:
    out = bytearray()
    while True:
        digit = value % 128
        value //= 128
        if value > 0:
            digit |= 0x80
        out.append(digit)
        if value == 0:
            break
    return bytes(out)


def build_connect_packet(protocol_level: int) -> bytes:
    client_id = "codex-" + "".join(random.choice(string.ascii_lowercase) for _ in range(8))
    proto_name = b"\x00\x04MQTT"
    connect_flags = b"\x02"  # clean session/start
    keepalive = b"\x00\x1e"

    variable_header = proto_name + bytes([protocol_level]) + connect_flags + keepalive

    client_id_bytes = client_id.encode("utf-8")
    payload = len(client_id_bytes).to_bytes(2, "big") + client_id_bytes

    remaining = encode_remaining_length(len(variable_header) + len(payload))
    return b"\x10" + remaining + variable_header + payload


async def tcp_check(host: str, port: int, timeout: float) -> tuple[bool, str | None]:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True, None
    except Exception as e:
        return False, str(e)


async def mqtt_probe_version(host: str, port: int, protocol_level: int, timeout: float) -> dict[str, Any]:
    packet = build_connect_packet(protocol_level)
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    except Exception as e:
        return {"protocol_level": protocol_level, "accepted": False, "connack": None, "error": str(e)}

    try:
        writer.write(packet)
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        response = await asyncio.wait_for(reader.read(8), timeout=timeout)

        if len(response) < 4 or response[0] != 0x20:
            return {"protocol_level": protocol_level, "accepted": False, "connack": response.hex(), "error": "unexpected_response"}

        if protocol_level == 5:
            reason_code = response[3]
            accepted = reason_code == 0x00
            return {
                "protocol_level": protocol_level,
                "accepted": accepted,
                "connack": response.hex(),
                "session_present": bool(response[2] & 0x01),
                "reason_code": reason_code,
                "error": None,
            }

        return_code = response[3]
        accepted = return_code == 0x00
        return {
            "protocol_level": protocol_level,
            "accepted": accepted,
            "connack": response.hex(),
            "session_present": bool(response[2] & 0x01),
            "return_code": return_code,
            "error": None,
        }
    except Exception as e:
        return {"protocol_level": protocol_level, "accepted": False, "connack": None, "error": str(e)}
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
        "service": "mqtt",
        "timestamp": now_iso(),
        "transport": "tcp",
        "reachable": False,
        "mqtt_detected": False,
        "supported_protocol_levels": [],
        "features": {
            "session_present_supported": False,
            "auth_required_or_rejected": False,
        },
        "probes": [],
        "error": None,
    }

    reachable, err = await tcp_check(host, port, TCP_TIMEOUT)
    if not reachable:
        result["error"] = f"tcp_unreachable: {err}"
        return result
    result["reachable"] = True

    probes = await asyncio.gather(
        mqtt_probe_version(host, port, 4, MQTT_TIMEOUT),   # MQTT 3.1.1
        mqtt_probe_version(host, port, 5, MQTT_TIMEOUT),   # MQTT 5
    )
    result["probes"] = probes

    supported = []
    for p in probes:
        if p.get("accepted"):
            supported.append(p["protocol_level"])
        if p.get("session_present"):
            result["features"]["session_present_supported"] = True

        # 0x05 for v3 and many non-zero v5 reason codes can imply auth/ACL restrictions.
        if (p.get("return_code") == 0x05) or (p.get("reason_code") not in (None, 0x00)):
            result["features"]["auth_required_or_rejected"] = True

    result["supported_protocol_levels"] = supported
    result["mqtt_detected"] = any(p.get("connack") for p in probes)

    return result


async def worker(host: str, port: int, sem: asyncio.Semaphore) -> dict[str, Any]:
    async with sem:
        try:
            return await enumerate_target(host, port)
        except Exception as e:
            return {"target": host, "port": port, "service": "mqtt", "timestamp": now_iso(), "reachable": False, "error": f"unhandled_exception: {e}"}


async def run(targets: list[str], ports: list[int], concurrency: int) -> dict[str, Any]:
    sem = asyncio.Semaphore(max(1, concurrency))
    tasks = [worker(t, p, sem) for t in targets for p in ports]
    results = await asyncio.gather(*tasks)
    summary = {
        "total_targets": len(targets),
        "total_checks": len(tasks),
        "reachable": sum(1 for r in results if r.get("reachable")),
        "mqtt_detected": sum(1 for r in results if r.get("mqtt_detected")),
        "mqtt_v5_supported": sum(1 for r in results if 5 in r.get("supported_protocol_levels", [])),
    }
    return {"generated_at": now_iso(), "service": "mqtt", "ports": ports, "summary": summary, "results": results}


def parse_ports(raw: str | None) -> list[int]:
    if not raw:
        return DEFAULT_PORTS[:]
    ports = sorted({int(x.strip()) for x in raw.split(",") if x.strip()})
    for p in ports:
        if p < 1 or p > 65535:
            raise ValueError(f"invalid port: {p}")
    return ports


def main() -> None:
    parser = argparse.ArgumentParser(description="Async safe MQTT enumerator")
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", default="mqtt_enum_results.json")
    parser.add_argument("-p", "--ports", help="Comma-separated ports (default: 1883)")
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
