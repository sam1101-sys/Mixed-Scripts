import asyncio
import ssl
import json
import argparse
from datetime import datetime

TIMEOUT = 5
GLOBAL_TIMEOUT = 15
CONCURRENCY = 10

SMTP_PORTS = [25, 465, 587]


async def smtp_session(host, port):
    result = {
        "target": host,
        "port": port,
        "open": False,
        "banner": None,
        "ehlo": [],
        "starttls": False,
        "auth": [],
        "vrfy": False,
        "expn": False,
        "open_relay": False,
        "error": None
    }

    try:
        # Handle implicit SSL (465)
        if port == 465:
            context = ssl.create_default_context()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=context),
                timeout=TIMEOUT
            )
        else:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=TIMEOUT
            )

        result["open"] = True

        # Read banner
        banner = await asyncio.wait_for(reader.readline(), timeout=TIMEOUT)
        result["banner"] = banner.decode(errors="ignore").strip()

        # Send EHLO
        writer.write(b"EHLO test.local\r\n")
        await writer.drain()

        # Read multi-line response safely
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=TIMEOUT)
            if not line:
                break

            decoded = line.decode(errors="ignore").strip()
            result["ehlo"].append(decoded)

            # Stop if line starts with 250 <space>
            if decoded.startswith("250 "):
                break

        # Parse capabilities
        for line in result["ehlo"]:
            upper = line.upper()
            if "STARTTLS" in upper:
                result["starttls"] = True
            if "AUTH" in upper:
                parts = upper.split()
                if "AUTH" in parts:
                    idx = parts.index("AUTH")
                    result["auth"] = parts[idx + 1:]

        # VRFY
        writer.write(b"VRFY postmaster\r\n")
        await writer.drain()
        vrfy_resp = await asyncio.wait_for(reader.readline(), timeout=TIMEOUT)
        if vrfy_resp and not vrfy_resp.decode().startswith("550"):
            result["vrfy"] = True

        # EXPN
        writer.write(b"EXPN postmaster\r\n")
        await writer.drain()
        expn_resp = await asyncio.wait_for(reader.readline(), timeout=TIMEOUT)
        if expn_resp and not expn_resp.decode().startswith("550"):
            result["expn"] = True

        # Safe open relay check
        writer.write(b"MAIL FROM:<test@test.com>\r\n")
        await writer.drain()
        await asyncio.wait_for(reader.readline(), timeout=TIMEOUT)

        writer.write(b"RCPT TO:<test@test.com>\r\n")
        await writer.drain()
        rcpt_resp = await asyncio.wait_for(reader.readline(), timeout=TIMEOUT)

        if rcpt_resp and not rcpt_resp.decode().startswith("550"):
            result["open_relay"] = True

        # QUIT cleanly
        writer.write(b"QUIT\r\n")
        await writer.drain()

        writer.close()
        await writer.wait_closed()

    except Exception as e:
        result["error"] = str(e)

    return result


async def bounded_smtp(host, port, semaphore):
    async with semaphore:
        try:
            return await asyncio.wait_for(
                smtp_session(host, port),
                timeout=GLOBAL_TIMEOUT
            )
        except asyncio.TimeoutError:
            return {
                "target": host,
                "port": port,
                "error": "GLOBAL TIMEOUT"
            }


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = []
    for host in hosts:
        for port in SMTP_PORTS:
            tasks.append(bounded_smtp(host, port, semaphore))

    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("Scan complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", required=True)
    parser.add_argument("-o", "--output", default="smtp_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
