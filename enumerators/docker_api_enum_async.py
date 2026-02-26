#!/usr/bin/env python3
import argparse
import asyncio
import json
import ssl
from datetime import datetime, timezone
from typing import Any

DEFAULT_PORTS = [2375, 2376]
TCP_TIMEOUT = 3.0
HTTP_TIMEOUT = 5.0
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


def parse_http(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace")
    head, _, body = text.partition("\r\n\r\n")
    lines = head.split("\r\n") if head else []
    status_code = None
    if lines and len(lines[0].split()) >= 2 and lines[0].split()[1].isdigit():
        status_code = int(lines[0].split()[1])
    headers: dict[str, str] = {}
    for ln in lines[1:]:
        if ":" not in ln:
            continue
        k, v = ln.split(":", 1)
        headers[k.strip().lower()] = v.strip()
    return {"status_code": status_code, "headers": headers, "body": body}


async def http_get(host: str, port: int, path: str, use_tls: bool, timeout: float) -> dict[str, Any]:
    ssl_ctx = None
    if use_tls:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "User-Agent: codex-docker-api-enum/1.0\r\n"
        "Accept: application/json,*/*\r\n"
        "Connection: close\r\n\r\n"
    ).encode("ascii", errors="ignore")

    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port, ssl=ssl_ctx), timeout=timeout)
    except Exception as e:
        return {"ok": False, "error": f"connect_failed: {e}", "status_code": None, "headers": {}, "body": ""}

    try:
        writer.write(request)
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        raw = await asyncio.wait_for(reader.read(READ_LIMIT), timeout=timeout)
        parsed = parse_http(raw)
        return {"ok": True, "error": None, **parsed}
    except Exception as e:
        return {"ok": False, "error": f"io_failed: {e}", "status_code": None, "headers": {}, "body": ""}
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


def json_or_text(body: str) -> Any:
    try:
        return json.loads(body)
    except Exception:
        return body[:2000]


async def enumerate_target(host: str, port: int) -> dict[str, Any]:
    use_tls = port == 2376
    base = ("https" if use_tls else "http") + f"://{host}:{port}"

    result = {
        "target": host,
        "port": port,
        "service": "docker_api",
        "timestamp": now_iso(),
        "transport": "tcp",
        "protocol": "https" if use_tls else "http",
        "base_url": base,
        "reachable": False,
        "api_accessible": False,
        "version": None,
        "docker_info": None,
        "containers": [],
        "endpoints": {},
        "evidence": [],
        "error": None,
    }

    reachable, err = await tcp_check(host, port, TCP_TIMEOUT)
    if not reachable:
        result["error"] = f"tcp_unreachable: {err}"
        return result
    result["reachable"] = True

    paths = ["/_ping", "/version", "/info", "/containers/json?all=1"]
    for path in paths:
        resp = await http_get(host, port, path, use_tls, HTTP_TIMEOUT)
        result["endpoints"][path] = {
            "ok": resp["ok"],
            "status_code": resp.get("status_code"),
            "error": resp.get("error"),
        }
        if not resp["ok"]:
            continue

        body_data = json_or_text(resp["body"])
        if path == "/_ping":
            result["api_accessible"] = resp["status_code"] == 200 and str(resp["body"]).strip().upper().startswith("OK")
            result["evidence"].append({"kind": "http", "step": "ping", "data": {"status_code": resp["status_code"], "body": str(resp["body"]).strip()[:200]}})
        elif path == "/version" and isinstance(body_data, dict):
            result["version"] = {
                "version": body_data.get("Version"),
                "api_version": body_data.get("ApiVersion"),
                "min_api_version": body_data.get("MinAPIVersion"),
                "git_commit": body_data.get("GitCommit"),
                "go_version": body_data.get("GoVersion"),
                "os": body_data.get("Os"),
                "arch": body_data.get("Arch"),
            }
            result["api_accessible"] = True
        elif path == "/info" and isinstance(body_data, dict):
            result["docker_info"] = {
                "name": body_data.get("Name"),
                "server_version": body_data.get("ServerVersion"),
                "operating_system": body_data.get("OperatingSystem"),
                "kernel_version": body_data.get("KernelVersion"),
                "cgroup_driver": body_data.get("CgroupDriver"),
                "containers": body_data.get("Containers"),
                "images": body_data.get("Images"),
                "swarm": body_data.get("Swarm"),
            }
        elif path == "/containers/json?all=1" and isinstance(body_data, list):
            result["containers"] = [
                {
                    "id": c.get("Id"),
                    "image": c.get("Image"),
                    "names": c.get("Names"),
                    "state": c.get("State"),
                    "status": c.get("Status"),
                }
                for c in body_data[:100]
                if isinstance(c, dict)
            ]

    return result


async def worker(host: str, port: int, sem: asyncio.Semaphore) -> dict[str, Any]:
    async with sem:
        try:
            return await enumerate_target(host, port)
        except Exception as e:
            return {"target": host, "port": port, "service": "docker_api", "timestamp": now_iso(), "reachable": False, "error": f"unhandled_exception: {e}"}


async def run(targets: list[str], ports: list[int], concurrency: int) -> dict[str, Any]:
    sem = asyncio.Semaphore(max(1, concurrency))
    tasks = [worker(t, p, sem) for t in targets for p in ports]
    results = await asyncio.gather(*tasks)
    summary = {
        "total_targets": len(targets),
        "total_checks": len(tasks),
        "reachable": sum(1 for r in results if r.get("reachable")),
        "api_accessible": sum(1 for r in results if r.get("api_accessible")),
        "containers_listed": sum(1 for r in results if r.get("containers")),
    }
    return {"generated_at": now_iso(), "service": "docker_api", "ports": ports, "summary": summary, "results": results}


def parse_ports(raw: str | None) -> list[int]:
    if not raw:
        return DEFAULT_PORTS[:]
    ports = sorted({int(x.strip()) for x in raw.split(",") if x.strip()})
    for p in ports:
        if p < 1 or p > 65535:
            raise ValueError(f"invalid port: {p}")
    return ports


def main() -> None:
    parser = argparse.ArgumentParser(description="Async safe Docker API enumerator")
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", default="docker_api_enum_results.json")
    parser.add_argument("-p", "--ports", help="Comma-separated ports (default: 2375,2376)")
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
