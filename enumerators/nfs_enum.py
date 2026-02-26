import asyncio
import json
import argparse
import socket
import subprocess
from datetime import datetime

TIMEOUT = 5
CONCURRENCY = 10


def tcp_check(host, port=2049):
    try:
        s = socket.create_connection((host, port), timeout=TIMEOUT)
        s.close()
        return True
    except:
        return False


def run_showmount(host):
    try:
        result = subprocess.run(
            ["showmount", "-e", host],
            capture_output=True,
            text=True,
            timeout=TIMEOUT
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except:
        return None


def parse_exports(output):
    exports = []
    if not output:
        return exports

    lines = output.splitlines()
    for line in lines:
        if "/" in line:
            parts = line.split()
            exports.append({
                "export": parts[0],
                "allowed_hosts": parts[1:] if len(parts) > 1 else []
            })
    return exports


async def enumerate_nfs(host, semaphore):
    async with semaphore:
        result = {
            "target": host,
            "port": 2049,
            "timestamp": datetime.utcnow().isoformat(),
            "reachable": False,
            "exports_found": False,
            "exports": [],
            "error": None
        }

        try:
            if not tcp_check(host):
                return result

            result["reachable"] = True

            exports_output = await asyncio.to_thread(run_showmount, host)

            if exports_output:
                result["exports_found"] = True
                result["exports"] = parse_exports(exports_output)

        except Exception as e:
            result["error"] = str(e)

        return result


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = [enumerate_nfs(h, semaphore) for h in hosts]
    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("NFS enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async NFS Enumerator")
    parser.add_argument("-f", "--file", required=True, help="Input file with hosts")
    parser.add_argument("-o", "--output", default="nfs_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
