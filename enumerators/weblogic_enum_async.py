#!/usr/bin/env python3
import argparse
import asyncio
import json
import re
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

DEFAULT_PORTS = [7001, 7002, 8001, 9001, 80, 443]
HTTP_TIMEOUT = 5.0
TCP_TIMEOUT = 3.0
T3_TIMEOUT = 4.0
READ_LIMIT = 131072

# Known historically high-risk version families (flagging only, no exploitation).
VERSION_RISK_RULES = [
    {
        "pattern": re.compile(r"\b10\.3(?:\.\d+)?\b"),
        "families": ["10.3.x"],
        "notable_cves": ["CVE-2017-10271"],
    },
    {
        "pattern": re.compile(r"\b12\.1(?:\.\d+)?\b"),
        "families": ["12.1.x"],
        "notable_cves": ["CVE-2017-10271"],
    },
    {
        "pattern": re.compile(r"\b12\.2\.1\.3\b"),
        "families": ["12.2.1.3"],
        "notable_cves": ["CVE-2020-14882"],
    },
    {
        "pattern": re.compile(r"\b12\.2\.1\.4\b"),
        "families": ["12.2.1.4"],
        "notable_cves": ["CVE-2020-14882", "CVE-2023-21839"],
    },
]


@dataclass(slots=True)
class EndpointCheck:
    path: str
    status_code: int | None
    reachable: bool
    exposed: bool
    location: str | None = None
    content_type: str | None = None
    title_hint: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "status_code": self.status_code,
            "reachable": self.reachable,
            "exposed": self.exposed,
            "location": self.location,
            "content_type": self.content_type,
            "title_hint": self.title_hint,
            "error": self.error,
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_targets(path: str) -> list[str]:
    targets: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            targets.append(raw)
    return targets


def parse_status_code(status_line: str) -> int | None:
    m = re.match(r"^HTTP/\d\.\d\s+(\d{3})", status_line)
    if not m:
        return None
    return int(m.group(1))


def extract_title_hint(body: str) -> str | None:
    m = re.search(r"<title>(.*?)</title>", body, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    title = re.sub(r"\s+", " ", m.group(1)).strip()
    return title[:200] if title else None


def parse_weblogic_version(*values: str | None) -> str | None:
    version_regex = re.compile(r"\b(\d+\.\d+(?:\.\d+){0,2})\b")
    for value in values:
        if not value:
            continue
        if "weblogic" not in value.lower() and "oracle" not in value.lower() and "bea" not in value.lower():
            continue
        m = version_regex.search(value)
        if m:
            return m.group(1)
    return None


def assess_version_risk(version: str | None) -> dict[str, Any]:
    if not version:
        return {
            "potentially_vulnerable": False,
            "matched_families": [],
            "notable_cves": [],
        }

    matched_families: list[str] = []
    notable_cves: list[str] = []
    for rule in VERSION_RISK_RULES:
        if rule["pattern"].search(version):
            matched_families.extend(rule["families"])
            notable_cves.extend(rule["notable_cves"])

    return {
        "potentially_vulnerable": bool(matched_families),
        "matched_families": sorted(set(matched_families)),
        "notable_cves": sorted(set(notable_cves)),
    }


async def tcp_reachable(host: str, port: int, timeout: float) -> tuple[bool, str | None]:
    try:
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True, None
    except Exception as e:
        return False, str(e)


async def http_get_raw(host: str, port: int, path: str, use_tls: bool, timeout: float) -> dict[str, Any]:
    ssl_ctx: ssl.SSLContext | None = None
    if use_tls:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "User-Agent: codex-weblogic-enum/1.0\r\n"
        "Accept: */*\r\n"
        "Connection: close\r\n\r\n"
    ).encode("ascii", errors="ignore")

    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ssl_ctx),
            timeout=timeout,
        )
    except Exception as e:
        return {
            "ok": False,
            "error": f"connect_failed: {e}",
            "status_code": None,
            "headers": {},
            "body": "",
        }

    try:
        writer.write(request)
        await asyncio.wait_for(writer.drain(), timeout=timeout)

        raw = await asyncio.wait_for(reader.read(READ_LIMIT), timeout=timeout)
        text = raw.decode("utf-8", errors="replace")

        head, _, body = text.partition("\r\n\r\n")
        lines = head.split("\r\n") if head else []
        status_line = lines[0] if lines else ""
        headers: dict[str, str] = {}
        for line in lines[1:]:
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()

        return {
            "ok": True,
            "error": None,
            "status_code": parse_status_code(status_line),
            "status_line": status_line,
            "headers": headers,
            "body": body,
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"io_failed: {e}",
            "status_code": None,
            "headers": {},
            "body": "",
        }
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def probe_t3(host: str, port: int, timeout: float) -> dict[str, Any]:
    # Standard non-destructive T3 hello; no payloads, no deserialization traffic.
    probe = b"t3 12.2.1\nAS:255\nHL:19\n\n"
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    except Exception as e:
        return {
            "reachable": False,
            "t3_detected": False,
            "banner": None,
            "error": str(e),
        }

    try:
        writer.write(probe)
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        response = await asyncio.wait_for(reader.read(512), timeout=timeout)
        banner = response.decode("utf-8", errors="replace").strip() if response else ""
        upper = banner.upper()
        is_t3 = any(marker in upper for marker in ["HELO", "T3", "WEBLOGIC"])
        return {
            "reachable": True,
            "t3_detected": is_t3,
            "banner": banner[:300] if banner else None,
            "error": None,
        }
    except Exception as e:
        return {
            "reachable": True,
            "t3_detected": False,
            "banner": None,
            "error": str(e),
        }
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


def endpoint_exposed(path: str, status: int | None, location: str | None) -> bool:
    if status is None:
        return False

    if path == "/console":
        return status in {200, 401, 403, 302}

    if path == "/wls-wsat/CoordinatorPortType":
        return status in {200, 401, 403, 405, 500}

    if path == "/bea_wls_internal":
        return status in {200, 401, 403, 302}

    return False


async def check_endpoint(host: str, port: int, path: str, use_tls: bool) -> EndpointCheck:
    resp = await http_get_raw(host, port, path, use_tls=use_tls, timeout=HTTP_TIMEOUT)
    if not resp["ok"]:
        return EndpointCheck(
            path=path,
            status_code=None,
            reachable=False,
            exposed=False,
            error=resp["error"],
        )

    location = resp["headers"].get("location")
    content_type = resp["headers"].get("content-type")
    title_hint = extract_title_hint(resp["body"])

    return EndpointCheck(
        path=path,
        status_code=resp["status_code"],
        reachable=True,
        exposed=endpoint_exposed(path, resp["status_code"], location),
        location=location,
        content_type=content_type,
        title_hint=title_hint,
        error=None,
    )


def looks_like_weblogic(server_header: str | None, body: str | None) -> bool:
    if server_header and any(x in server_header.lower() for x in ["weblogic", "oracle", "bea"]):
        return True
    if body and any(x in body.lower() for x in ["weblogic", "bea", "oracle fusion middleware"]):
        return True
    return False


async def enumerate_weblogic_port(target: str, port: int) -> dict[str, Any]:
    use_tls = port in {443, 7002}
    scheme = "https" if use_tls else "http"
    base_url = f"{scheme}://{target}:{port}"

    result: dict[str, Any] = {
        "target": target,
        "port": port,
        "service": "weblogic_http",
        "timestamp": now_iso(),
        "reachable": False,
        "protocol": scheme,
        "base_url": base_url,
        "weblogic_detected": False,
        "server_header": None,
        "version": None,
        "admin_console_exposed": False,
        "wls_wsat_exposed": False,
        "bea_wls_internal_exposed": False,
        "t3_probe": {
            "reachable": False,
            "t3_detected": False,
            "banner": None,
            "error": None,
        },
        "version_risk": {
            "potentially_vulnerable": False,
            "matched_families": [],
            "notable_cves": [],
        },
        "http": {
            "root_status_code": None,
            "root_headers": {},
            "root_title_hint": None,
            "endpoints": [],
        },
        "evidence": [],
        "error": None,
    }

    reachable, reach_error = await tcp_reachable(target, port, timeout=TCP_TIMEOUT)
    if not reachable:
        result["error"] = f"tcp_unreachable: {reach_error}"
        return result

    result["reachable"] = True
    result["evidence"].append(
        {
            "kind": "tcp",
            "step": "connect",
            "data": {"reachable": True},
        }
    )

    root = await http_get_raw(target, port, "/", use_tls=use_tls, timeout=HTTP_TIMEOUT)
    if root["ok"]:
        server_header = root["headers"].get("server")
        title_hint = extract_title_hint(root["body"])
        result["server_header"] = server_header
        result["http"]["root_status_code"] = root["status_code"]
        result["http"]["root_headers"] = root["headers"]
        result["http"]["root_title_hint"] = title_hint
        result["weblogic_detected"] = looks_like_weblogic(server_header, root["body"])
        result["version"] = parse_weblogic_version(server_header, root["body"])
        result["version_risk"] = assess_version_risk(result["version"])

        result["evidence"].append(
            {
                "kind": "http",
                "step": "root_request",
                "data": {
                    "status_code": root["status_code"],
                    "server_header": server_header,
                    "title_hint": title_hint,
                },
            }
        )
    else:
        result["evidence"].append(
            {
                "kind": "http",
                "step": "root_request",
                "data": {"error": root["error"]},
            }
        )

    endpoints = [
        "/console",
        "/wls-wsat/CoordinatorPortType",
        "/bea_wls_internal",
    ]

    endpoint_results = await asyncio.gather(
        *(check_endpoint(target, port, path, use_tls=use_tls) for path in endpoints),
        return_exceptions=True,
    )

    parsed_checks: list[EndpointCheck] = []
    for item in endpoint_results:
        if isinstance(item, Exception):
            parsed_checks.append(
                EndpointCheck(
                    path="unknown",
                    status_code=None,
                    reachable=False,
                    exposed=False,
                    error=str(item),
                )
            )
        else:
            parsed_checks.append(item)

    result["http"]["endpoints"] = [c.to_dict() for c in parsed_checks]
    for check in parsed_checks:
        if check.path == "/console" and check.exposed:
            result["admin_console_exposed"] = True
        elif check.path == "/wls-wsat/CoordinatorPortType" and check.exposed:
            result["wls_wsat_exposed"] = True
        elif check.path == "/bea_wls_internal" and check.exposed:
            result["bea_wls_internal_exposed"] = True

    result["evidence"].append(
        {
            "kind": "http",
            "step": "endpoint_checks",
            "data": result["http"]["endpoints"],
        }
    )

    t3_result = await probe_t3(target, port, timeout=T3_TIMEOUT)
    result["t3_probe"] = t3_result
    result["evidence"].append(
        {
            "kind": "t3",
            "step": "t3_handshake_probe",
            "data": t3_result,
        }
    )

    if not result["version"] and result["weblogic_detected"]:
        result["version_risk"] = {
            "potentially_vulnerable": None,
            "matched_families": [],
            "notable_cves": [],
        }

    return result


async def worker(target: str, port: int, sem: asyncio.Semaphore) -> dict[str, Any]:
    async with sem:
        try:
            return await enumerate_weblogic_port(target, port)
        except Exception as e:
            return {
                "target": target,
                "port": port,
                "service": "weblogic_http",
                "timestamp": now_iso(),
                "reachable": False,
                "error": f"unhandled_exception: {e}",
            }


async def run(targets: list[str], ports: list[int], concurrency: int) -> dict[str, Any]:
    sem = asyncio.Semaphore(max(1, concurrency))
    tasks = [worker(target, port, sem) for target in targets for port in ports]
    results = await asyncio.gather(*tasks)

    summary = {
        "total_targets": len(targets),
        "total_checks": len(tasks),
        "reachable": sum(1 for r in results if r.get("reachable")),
        "weblogic_detected": sum(1 for r in results if r.get("weblogic_detected")),
        "admin_console_exposed": sum(1 for r in results if r.get("admin_console_exposed")),
        "wls_wsat_exposed": sum(1 for r in results if r.get("wls_wsat_exposed")),
        "bea_wls_internal_exposed": sum(1 for r in results if r.get("bea_wls_internal_exposed")),
        "t3_detected": sum(1 for r in results if (r.get("t3_probe") or {}).get("t3_detected")),
        "potentially_vulnerable_version": sum(
            1
            for r in results
            if (r.get("version_risk") or {}).get("potentially_vulnerable") is True
        ),
    }

    return {
        "generated_at": now_iso(),
        "service": "weblogic_http",
        "ports": ports,
        "summary": summary,
        "results": results,
    }


def parse_ports(raw: str | None) -> list[int]:
    if not raw:
        return DEFAULT_PORTS[:]
    ports: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        port = int(token)
        if not (1 <= port <= 65535):
            raise ValueError(f"invalid port: {port}")
        ports.append(port)
    return sorted(set(ports))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Async safe WebLogic HTTP/T3 enumeration")
    parser.add_argument("-i", "--input", required=True, help="Input file with one host/IP per line")
    parser.add_argument("-o", "--output", default="weblogic_enum_results.json", help="Output JSON file")
    parser.add_argument(
        "-p",
        "--ports",
        help="Comma-separated ports (default: 7001,7002,8001,9001,80,443)",
    )
    parser.add_argument("-c", "--concurrency", type=int, default=20, help="Concurrent checks")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    targets = parse_targets(args.input)
    if not targets:
        raise SystemExit("No targets found in input file")

    ports = parse_ports(args.ports)

    payload = asyncio.run(run(targets, ports, concurrency=args.concurrency))

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
