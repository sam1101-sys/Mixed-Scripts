import asyncio
import json
import argparse
import socket
from datetime import datetime
import requests

TIMEOUT = 5
CONCURRENCY = 10


def tcp_check(host):
    try:
        s = socket.create_connection((host, 9200), timeout=TIMEOUT)
        s.close()
        return True
    except:
        return False


def es_enum(host):
    result = {
        "target": host,
        "port": 9200,
        "timestamp": datetime.utcnow().isoformat(),
        "reachable": False,
        "unauthenticated_access": False,
        "version": None,
        "cluster_name": None,
        "node_name": None,
        "security_enabled": None,
        "indices": [],
        "snapshot_repositories": [],
        "error": None
    }

    try:
        if not tcp_check(host):
            return result

        result["reachable"] = True

        base_url = f"http://{host}:9200"

        # Root info
        r = requests.get(base_url, timeout=TIMEOUT)
        if r.status_code == 200:
            result["unauthenticated_access"] = True
            data = r.json()
            result["version"] = data.get("version", {}).get("number")
            result["cluster_name"] = data.get("cluster_name")
            result["node_name"] = data.get("name")

        # Check security
        try:
            sec = requests.get(
                f"{base_url}/_xpack",
                timeout=TIMEOUT
            )
            if sec.status_code == 200:
                sec_json = sec.json()
                result["security_enabled"] = sec_json.get("features", {}).get("security", {}).get("enabled")
        except:
            pass

        # List indices
        try:
            indices = requests.get(
                f"{base_url}/_cat/indices?format=json",
                timeout=TIMEOUT
            )
            if indices.status_code == 200:
                idx_data = indices.json()
                for idx in idx_data[:10]:
                    result["indices"].append({
                        "index": idx.get("index"),
                        "docs": idx.get("docs.count")
                    })
        except:
            pass

        # Snapshot repositories
        try:
            snap = requests.get(
                f"{base_url}/_snapshot",
                timeout=TIMEOUT
            )
            if snap.status_code == 200:
                result["snapshot_repositories"] = list(snap.json().keys())
        except:
            pass

    except Exception as e:
        result["error"] = str(e)

    return result


async def async_es_enum(host, semaphore):
    async with semaphore:
        return await asyncio.to_thread(es_enum, host)


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = [async_es_enum(h, semaphore) for h in hosts]
    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("Elasticsearch enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async Elasticsearch Enumerator")
    parser.add_argument("-f", "--file", required=True)
    parser.add_argument("-o", "--output", default="es_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
