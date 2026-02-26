#!/usr/bin/env python3
import argparse
import asyncio
import json
import ssl
from datetime import datetime, timezone
from typing import Any

DEFAULT_PORTS = [5000]
TCP_TIMEOUT = 3.0
HTTP_TIMEOUT = 5.0
READ_LIMIT = 262144
MAX_REPOS = 100


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_targets(path: str) -> list[str]:
    items: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if t and not t.startswith("#"):
                items.append(t)
    return items


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

    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "User-Agent: codex-docker-registry-enum/1.0\r\n"
        "Accept: application/json,*/*\r\n"
        "Connection: close\r\n\r\n"
    ).encode("ascii", errors="ignore")

    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port, ssl=ssl_ctx), timeout=timeout)
    except Exception as e:
        return {"ok": False, "error": f"connect_failed: {e}", "status_code": None, "headers": {}, "body": ""}

    try:
        writer.write(req)
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


def parse_json(body: str) -> Any:
    try:
        return json.loads(body)
    except Exception:
        return None


async def enumerate_target(host: str, port: int, tls_mode: bool | None = None) -> dict[str, Any]:
    use_tls = (port == 443) if tls_mode is None else tls_mode

    result = {
        "target": host,
        "port": port,
        "service": "docker_registry",
        "timestamp": now_iso(),
        "transport": "tcp",
        "protocol": "https" if use_tls else "http",
        "reachable": False,
        "registry_api_available": False,
        "distribution_api_version": None,
        "auth_challenge": None,
        "catalog": [],
        "tags": {},
        "endpoints": {},
        "evidence": [],
        "error": None,
    }

    reachable, err = await tcp_check(host, port, TCP_TIMEOUT)
    if not reachable:
        result["error"] = f"tcp_unreachable: {err}"
        return result
    result["reachable"] = True

    v2 = await http_get(host, port, "/v2/", use_tls, HTTP_TIMEOUT)
    result["endpoints"]["/v2/"] = {"ok": v2["ok"], "status_code": v2.get("status_code"), "error": v2.get("error")}
    if v2["ok"]:
        hdr = v2["headers"]
        result["distribution_api_version"] = hdr.get("docker-distribution-api-version")
        result["auth_challenge"] = hdr.get("www-authenticate")
        result["registry_api_available"] = v2["status_code"] in (200, 401)

    catalog = await http_get(host, port, f"/v2/_catalog?n={MAX_REPOS}", use_tls, HTTP_TIMEOUT)
    result["endpoints"]["/v2/_catalog"] = {"ok": catalog["ok"], "status_code": catalog.get("status_code"), "error": catalog.get("error")}
    if catalog["ok"] and catalog.get("status_code") == 200:
        data = parse_json(catalog["body"])
        if isinstance(data, dict) and isinstance(data.get("repositories"), list):
            result["catalog"] = [str(x) for x in data["repositories"][:MAX_REPOS]]

    for repo in result["catalog"][:30]:
        path = f"/v2/{repo}/tags/list"
        tags_resp = await http_get(host, port, path, use_tls, HTTP_TIMEOUT)
        result["endpoints"][path] = {
            "ok": tags_resp["ok"],
            "status_code": tags_resp.get("status_code"),
            "error": tags_resp.get("error"),
        }
        if tags_resp["ok"] and tags_resp.get("status_code") == 200:
            data = parse_json(tags_resp["body"])
            if isinstance(data, dict):
                tags = data.get("tags")
                if isinstance(tags, list):
                    result["tags"][repo] = [str(t) for t in tags[:100]]

    result["evidence"].append({
        "kind": "http",
        "step": "registry_checks",
        "data": {
            "registry_api_available": result["registry_api_available"],
            "distribution_api_version": result["distribution_api_version"],
            "catalog_count": len(result["catalog"]),
            "tag_repo_count": len(result["tags"]),
        },
    })

    return result


async def worker(host: str, port: int, sem: asyncio.Semaphore) -> dict[str, Any]:
    async with sem:
        try:
            # try HTTP first for :5000, then TLS fallback if HTTP parse fails repeatedly
            plain = await enumerate_target(host, port, tls_mode=False)
            if plain.get("registry_api_available") or plain.get("catalog"):
                return plain
            if plain.get("endpoints", {}).get("/v2/", {}).get("ok"):
                return plain
            tls_try = await enumerate_target(host, port, tls_mode=True)
            if tls_try.get("registry_api_available") or tls_try.get("catalog"):
                return tls_try
            return plain
        except Exception as e:
            return {"target": host, "port": port, "service": "docker_registry", "timestamp": now_iso(), "reachable": False, "error": f"unhandled_exception: {e}"}


async def run(targets: list[str], ports: list[int], concurrency: int) -> dict[str, Any]:
    sem = asyncio.Semaphore(max(1, concurrency))
    tasks = [worker(t, p, sem) for t in targets for p in ports]
    results = await asyncio.gather(*tasks)
    summary = {
        "total_targets": len(targets),
        "total_checks": len(tasks),
        "reachable": sum(1 for r in results if r.get("reachable")),
        "registry_api_available": sum(1 for r in results if r.get("registry_api_available")),
        "catalog_exposed": sum(1 for r in results if r.get("catalog")),
    }
    return {"generated_at": now_iso(), "service": "docker_registry", "ports": ports, "summary": summary, "results": results}


def parse_ports(raw: str | None) -> list[int]:
    if not raw:
        return DEFAULT_PORTS[:]
    ports = sorted({int(x.strip()) for x in raw.split(",") if x.strip()})
    for p in ports:
        if p < 1 or p > 65535:
            raise ValueError(f"invalid port: {p}")
    return ports


def main() -> None:
    parser = argparse.ArgumentParser(description="Async safe Docker Registry enumerator")
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", default="docker_registry_enum_results.json")
    parser.add_argument("-p", "--ports", help="Comma-separated ports (default: 5000)")
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
