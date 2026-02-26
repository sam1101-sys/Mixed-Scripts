import asyncio
import socket
import argparse
import json
from datetime import datetime

TIMEOUT = 5
CONCURRENCY = 20

TELNET_IAC = b"\xff"  # Telnet "Interpret as Command" prefix

async def grab_banner(host):
    """Connect and read initial banner (if any)."""
    try:
        reader, writer = await asyncio.open_connection(host, 23)
        try:
            banner = await asyncio.wait_for(reader.read(1024), timeout=TIMEOUT)
        finally:
            writer.close()
            await writer.wait_closed()
        return banner.decode(errors="ignore").strip()
    except Exception:
        return None

async def capture_negotiate(host):
    """
    Connect and read negotiation bytes until close or timeout.
    Optionally parse IAC (Interpret As Command) options.
    """
    try:
        reader, writer = await asyncio.open_connection(host, 23)
        try:
            data = await asyncio.wait_for(reader.read(1024), timeout=TIMEOUT)
        finally:
            writer.close()
            await writer.wait_closed()

        # Identify IAC sequences
        options = []
        i = 0
        while i < len(data):
            if data[i:i+1] == TELNET_IAC:
                # Telnet command + option byte if present
                if i + 2 < len(data):
                    cmd = data[i]
                    opt = data[i+1]
                    options.append(f"{cmd:02x}:{opt:02x}")
                    i += 2
            i += 1
        return {"raw": data.hex(), "options": options}
    except Exception:
        return None

async def scan_telnet(host, semaphore):
    async with semaphore:
        result = {
            "target": host,
            "port": 23,
            "timestamp": datetime.utcnow().isoformat(),
            "banner": None,
            "negotiate": None,
            "ntlm_info": None,
            "open": False,
            "error": None,
        }

        try:
            # Check banner and negotiate
            result["banner"] = await grab_banner(host)
            result["negotiate"] = await capture_negotiate(host)
            if result["banner"] or result["negotiate"]:
                result["open"] = True

            # Optional: Extract NTLM info by looking for NetBIOS/NTLM negotiation patterns
            # (very basic detection without full MSDT)
            if result["negotiate"]:
                raw_hex = result["negotiate"]["raw"]
                if "4e544c4d535350" in raw_hex.upper():  # ASCII 'NTLMSSP'
                    result["ntlm_info"] = "NTLM negotiation detected"
        except Exception as e:
            result["error"] = str(e)
        return result

async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)
    with open(input_file, "r") as f:
        targets = [line.strip() for line in f if line.strip()]

    tasks = [scan_telnet(t, semaphore) for t in targets]
    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Completed Telnet enumeration. Results in {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async Telnet (port 23) Enumerator")
    parser.add_argument("-f", "--file", required=True, help="File with targets")
    parser.add_argument("-o", "--output", default="telnet_results.json", help="Output JSON file")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
