import asyncio
import json
import argparse
import socket
from datetime import datetime

TIMEOUT = 5
CONCURRENCY = 10
COMMON_JDWP_PORTS = [5005, 8000, 8787]

JDWP_HANDSHAKE = b"JDWP-Handshake"


def tcp_check(host, port):
    try:
        s = socket.create_connection((host, port), timeout=TIMEOUT)
        s.close()
        return True
    except:
        return False


def jdwp_enum(host, port):
    result = {
        "target": host,
        "port": port,
        "timestamp": datetime.utcnow().isoformat(),
        "reachable": False,
        "jdwp_exposed": False,
        "vm_version_response": None,
        "error": None
    }

    try:
        if not tcp_check(host, port):
            return result

        result["reachable"] = True

        s = socket.create_connection((host, port), timeout=TIMEOUT)

        # Send handshake
        s.sendall(JDWP_HANDSHAKE)

        response = s.recv(1024)
        if response == JDWP_HANDSHAKE:
            result["jdwp_exposed"] = True

            # Minimal JDWP version request packet
            # JDWP packet format: length(4) id(4) flags(1) cmdset(1) cmd(1)
            # Version command: cmdset=1, cmd=1
            packet = (
                b"\x00\x00\x00\x0b"  # length 11
                b"\x00\x00\x00\x01"  # id
                b"\x00"              # flags
                b"\x01"              # cmdset (VirtualMachine)
                b"\x01"              # cmd (Version)
            )

            s.sendall(packet)
            vm_resp = s.recv(1024)
            result["vm_version_response"] = vm_resp.hex()

        s.close()

    except Exception as e:
        result["error"] = str(e)

    return result


async def async_jdwp_enum(host, port, semaphore):
    async with semaphore:
        return await asyncio.to_thread(jdwp_enum, host, port)


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = []
    for host in hosts:
        for port in COMMON_JDWP_PORTS:
            tasks.append(async_jdwp_enum(host, port, semaphore))

    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("JDWP enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async JDWP Enumerator")
    parser.add_argument("-f", "--file", required=True)
    parser.add_argument("-o", "--output", default="jdwp_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
