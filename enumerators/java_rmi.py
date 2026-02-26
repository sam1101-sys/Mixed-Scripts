import asyncio
import json
import argparse
import socket
from datetime import datetime

TIMEOUT = 5
CONCURRENCY = 10
COMMON_RMI_PORTS = [1099, 1100, 8008, 4444, 33333]


def tcp_check(host, port):
    try:
        s = socket.create_connection((host, port), timeout=TIMEOUT)
        s.close()
        return True
    except:
        return False


def detect_rmi(host, port):
    result = {
        "target": host,
        "port": port,
        "timestamp": datetime.utcnow().isoformat(),
        "reachable": False,
        "jrmi_detected": False,
        "possible_registry": False,
        "jmx_detected": False,
        "ssl_possible": False,
        "error": None
    }

    try:
        if not tcp_check(host, port):
            return result

        result["reachable"] = True

        s = socket.create_connection((host, port), timeout=TIMEOUT)

        # Try to read initial bytes
        try:
            data = s.recv(1024)
            if b"JRMI" in data:
                result["jrmi_detected"] = True
        except:
            pass

        # Send minimal RMI handshake header
        try:
            # JRMI magic + version
            s.sendall(b"\x4a\x52\x4d\x49\x00\x02\x4b")
            resp = s.recv(1024)
            if resp:
                result["possible_registry"] = True

                # JMX detection (very common over RMI)
                if b"javax.management" in resp or b"jmx" in resp.lower():
                    result["jmx_detected"] = True
        except:
            pass

        s.close()

    except Exception as e:
        result["error"] = str(e)

    return result


async def async_rmi_enum(host, port, semaphore):
    async with semaphore:
        return await asyncio.to_thread(detect_rmi, host, port)


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = []
    for host in hosts:
        for port in COMMON_RMI_PORTS:
            tasks.append(async_rmi_enum(host, port, semaphore))

    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("Java RMI enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async Java RMI Enumerator")
    parser.add_argument("-f", "--file", required=True)
    parser.add_argument("-o", "--output", default="rmi_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
