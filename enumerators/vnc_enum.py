import asyncio
import json
import argparse
import socket
from datetime import datetime

TIMEOUT = 5
CONCURRENCY = 10
PORTS = [5800, 5801, 5900, 5901]


def tcp_check(host, port):
    try:
        s = socket.create_connection((host, port), timeout=TIMEOUT)
        s.close()
        return True
    except:
        return False


def vnc_enum(host, port):
    result = {
        "target": host,
        "port": port,
        "timestamp": datetime.utcnow().isoformat(),
        "reachable": False,
        "rfb_version": None,
        "auth_methods": [],
        "no_auth": False,
        "vnc_auth_supported": False,
        "error": None
    }

    try:
        if not tcp_check(host, port):
            return result

        result["reachable"] = True

        s = socket.create_connection((host, port), timeout=TIMEOUT)

        # Read RFB version
        banner = s.recv(12)
        if banner.startswith(b"RFB"):
            result["rfb_version"] = banner.decode().strip()

        # Send same version back (required for handshake)
        s.sendall(banner)

        # Read security types
        sec_types = s.recv(1024)

        if sec_types:
            if len(sec_types) > 0:
                num_types = sec_types[0]

                if num_types == 0:
                    result["error"] = "Connection failed (no security types)"
                else:
                    types = list(sec_types[1:1+num_types])
                    result["auth_methods"] = types

                    if 1 in types:
                        result["no_auth"] = True
                    if 2 in types:
                        result["vnc_auth_supported"] = True

        s.close()

    except Exception as e:
        result["error"] = str(e)

    return result


async def async_vnc_enum(host, port, semaphore):
    async with semaphore:
        return await asyncio.to_thread(vnc_enum, host, port)


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = []
    for host in hosts:
        for port in PORTS:
            tasks.append(async_vnc_enum(host, port, semaphore))

    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("VNC enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async VNC Enumerator")
    parser.add_argument("-f", "--file", required=True)
    parser.add_argument("-o", "--output", default="vnc_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
