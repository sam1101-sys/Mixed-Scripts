import asyncio
import json
import argparse
import socket
from datetime import datetime
from impacket.smbconnection import SMBConnection

TIMEOUT = 5
CONCURRENCY = 10


def tcp_check(host):
    try:
        s = socket.create_connection((host, 445), timeout=TIMEOUT)
        s.close()
        return True
    except:
        return False


def smb_enum(host):
    result = {
        "target": host,
        "port": 445,
        "timestamp": datetime.utcnow().isoformat(),
        "reachable": False,
        "os": None,
        "domain": None,
        "smbv1": None,
        "signing_required": None,
        "null_session": False,
        "shares": [],
        "admin_share_access": False,
        "ipc_access": False,
        "error": None
    }

    try:
        if not tcp_check(host):
            return result

        result["reachable"] = True

        # Anonymous connection attempt
        conn = SMBConnection(host, host, timeout=TIMEOUT)
        conn.login("", "")  # Null session attempt
        result["null_session"] = True

        # OS & Domain
        result["os"] = conn.getServerOS()
        result["domain"] = conn.getServerDomain()

        # SMBv1 check
        result["smbv1"] = conn.getDialect() == "NT LM 0.12"

        # Signing required?
        result["signing_required"] = conn.isSigningRequired()

        # Enumerate shares
        shares = conn.listShares()
        for share in shares:
            share_name = share['shi1_netname'][:-1]
            result["shares"].append(share_name)

        # Check ADMIN$ access
        try:
            conn.connectTree("ADMIN$")
            result["admin_share_access"] = True
        except:
            pass

        # Check IPC$ access
        try:
            conn.connectTree("IPC$")
            result["ipc_access"] = True
        except:
            pass

        conn.logoff()

    except Exception as e:
        result["error"] = str(e)

    return result


async def async_smb_enum(host, semaphore):
    async with semaphore:
        return await asyncio.to_thread(smb_enum, host)


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = [async_smb_enum(h, semaphore) for h in hosts]
    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("SMB enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async SMB Enumerator")
    parser.add_argument("-f", "--file", required=True, help="Input file with hosts")
    parser.add_argument("-o", "--output", default="smb_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
