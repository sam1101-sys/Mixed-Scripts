import asyncio
import json
import argparse
import socket
import ssl
from datetime import datetime
import requests

TIMEOUT = 5
CONCURRENCY = 10
PORTS = [5985, 5986]


def tcp_check(host, port):
    try:
        s = socket.create_connection((host, port), timeout=TIMEOUT)
        s.close()
        return True
    except:
        return False


def get_ssl_info(host, port):
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                return {
                    "subject": cert.get("subject"),
                    "issuer": cert.get("issuer")
                }
    except:
        return None


def winrm_enum(host, port):
    result = {
        "target": host,
        "port": port,
        "timestamp": datetime.utcnow().isoformat(),
        "reachable": False,
        "wsman_endpoint": False,
        "http_status": None,
        "auth_methods": [],
        "ntlm_supported": False,
        "basic_supported": False,
        "kerberos_supported": False,
        "ssl_info": None,
        "server_header": None,
        "error": None
    }

    try:
        if not tcp_check(host, port):
            return result

        result["reachable"] = True

        scheme = "https" if port == 5986 else "http"
        url = f"{scheme}://{host}:{port}/wsman"

        r = requests.get(
            url,
            timeout=TIMEOUT,
            verify=False
        )

        result["http_status"] = r.status_code
        result["server_header"] = r.headers.get("Server")

        if r.status_code in [200, 401]:
            result["wsman_endpoint"] = True

        # Authentication header
        www_auth = r.headers.get("WWW-Authenticate")
        if www_auth:
            methods = www_auth.split(",")
            for m in methods:
                method = m.strip()
                result["auth_methods"].append(method)

                if "NTLM" in method.upper():
                    result["ntlm_supported"] = True
                if "BASIC" in method.upper():
                    result["basic_supported"] = True
                if "KERBEROS" in method.upper() or "NEGOTIATE" in method.upper():
                    result["kerberos_supported"] = True

        # SSL cert info
        if port == 5986:
            result["ssl_info"] = get_ssl_info(host, port)

    except Exception as e:
        result["error"] = str(e)

    return result


async def async_winrm_enum(host, port, semaphore):
    async with semaphore:
        return await asyncio.to_thread(winrm_enum, host, port)


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = []
    for host in hosts:
        for port in PORTS:
            tasks.append(async_winrm_enum(host, port, semaphore))

    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("WinRM enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async WinRM Enumerator")
    parser.add_argument("-f", "--file", required=True)
    parser.add_argument("-o", "--output", default="winrm_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
