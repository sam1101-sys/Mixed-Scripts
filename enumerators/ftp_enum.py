import asyncio
import ftplib
import socket
import json
import argparse
from datetime import datetime
from io import BytesIO

DEFAULT_CREDS = [
    ("ftp", "ftp"),
    ("admin", "admin"),
    ("test", "test"),
    ("user", "password"),
]

TIMEOUT = 5
CONCURRENCY = 20


async def grab_banner(host):
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, 21),
            timeout=TIMEOUT
        )
        banner = await asyncio.wait_for(reader.read(1024), timeout=TIMEOUT)
        writer.close()
        await writer.wait_closed()
        return banner.decode(errors="ignore").strip()
    except Exception:
        return None


def test_login_sync(host, username, password):
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, 21, timeout=TIMEOUT)
        ftp.login(username, password)
        ftp.quit()
        return True
    except Exception:
        return False


def writable_directory_test_sync(host):
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, 21, timeout=TIMEOUT)
        ftp.login("anonymous", "anonymous@test.com")

        test_file = "pentest_tmp.txt"
        ftp.storbinary(f"STOR {test_file}", BytesIO(b"pentest"))
        ftp.delete(test_file)
        ftp.quit()
        return True
    except Exception:
        return False


async def enumerate_ftp(host, semaphore):
    async with semaphore:
        result = {
            "target": host,
            "port": 21,
            "timestamp": datetime.utcnow().isoformat(),
            "banner": None,
            "anonymous_login_allowed": False,
            "default_credentials_worked": [],
            "writable_directory": False,
            "error": None,
        }

        try:
            result["banner"] = await grab_banner(host)

            # Anonymous login
            anon = await asyncio.to_thread(
                test_login_sync, host, "anonymous", "anonymous@test.com"
            )
            result["anonymous_login_allowed"] = anon

            if anon:
                writable = await asyncio.to_thread(
                    writable_directory_test_sync, host
                )
                result["writable_directory"] = writable

            # Default creds
            for user, pwd in DEFAULT_CREDS:
                worked = await asyncio.to_thread(
                    test_login_sync, host, user, pwd
                )
                if worked:
                    result["default_credentials_worked"].append(
                        {"username": user, "password": pwd}
                    )

        except Exception as e:
            result["error"] = str(e)

        return result


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        targets = [line.strip() for line in f if line.strip()]

    tasks = [
        enumerate_ftp(target, semaphore)
        for target in targets
    ]

    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print(f"\nScan complete. Results saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async FTP Enumeration Tool")
    parser.add_argument("-f", "--file", required=True, help="Input file with IPs")
    parser.add_argument("-o", "--output", default="ftp_results.json", help="Output JSON file")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
