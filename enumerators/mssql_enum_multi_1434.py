import asyncio
import json
import argparse
from datetime import datetime

TIMEOUT = 4
CONCURRENCY = 20
UDP_PORT = 1434

DISCOVERY_PACKET = b"\x02"


def parse_browser_response(data):
    """
    Parses SQL Browser response into structured dict.
    """
    try:
        decoded = data.decode(errors="ignore")
        parts = decoded.split(";")

        parsed = {}
        for i in range(0, len(parts) - 1, 2):
            key = parts[i].strip()
            value = parts[i + 1].strip()
            if key:
                parsed[key] = value

        return parsed
    except Exception:
        return {"raw": data.hex()}


async def query_sql_browser(host):
    result = {
        "target": host,
        "port": UDP_PORT,
        "timestamp": datetime.utcnow().isoformat(),
        "responsive": False,
        "instances": [],
        "error": None
    }

    try:
        loop = asyncio.get_running_loop()

        transport, protocol = await loop.create_datagram_endpoint(
            lambda: asyncio.DatagramProtocol(),
            remote_addr=(host, UDP_PORT)
        )

        transport.sendto(DISCOVERY_PACKET)

        try:
            data, _ = await asyncio.wait_for(
                loop.sock_recv(transport.get_extra_info("socket"), 4096),
                timeout=TIMEOUT
            )
        except:
            # Fallback for compatibility
            transport.close()
            return result

        result["responsive"] = True

        parsed = parse_browser_response(data)

        if parsed:
            result["instances"].append(parsed)

        transport.close()

    except Exception as e:
        result["error"] = str(e)

    return result


async def bounded_query(host, semaphore):
    async with semaphore:
        try:
            return await asyncio.wait_for(
                query_sql_browser(host),
                timeout=TIMEOUT + 2
            )
        except asyncio.TimeoutError:
            return {
                "target": host,
                "port": UDP_PORT,
                "responsive": False,
                "error": "Timeout"
            }


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = [bounded_query(host, semaphore) for host in hosts]
    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("SQL Browser enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MSSQL Browser UDP 1434 Enumerator")
    parser.add_argument("-f", "--file", required=True, help="Input file with hosts")
    parser.add_argument("-o", "--output", default="mssql_browser_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
