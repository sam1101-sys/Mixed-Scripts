import asyncio
import json
import argparse
import socket
from datetime import datetime
from impacket.krb5 import constants
from impacket.krb5.asn1 import AS_REQ, KRB_ERROR
from impacket.krb5.types import Principal
from impacket.krb5.kerberosv5 import sendReceive
from impacket.krb5.crypto import Key
from impacket.krb5 import getKerberosTGT

TIMEOUT = 5
CONCURRENCY = 10

TEST_USERS = [
    "administrator",
    "guest",
    "krbtgt"
]


def tcp_check(host):
    try:
        s = socket.create_connection((host, 88), timeout=TIMEOUT)
        s.close()
        return True
    except:
        return False


def kerberos_enum(host):
    result = {
        "target": host,
        "port": 88,
        "timestamp": datetime.utcnow().isoformat(),
        "reachable": False,
        "realm_detected": None,
        "user_exists": [],
        "asrep_roastable": [],
        "error": None
    }

    try:
        if not tcp_check(host):
            return result

        result["reachable"] = True

        for user in TEST_USERS:
            try:
                # Attempt AS-REQ without preauth
                principal = Principal(user, type=constants.PrincipalNameType.NT_PRINCIPAL.value)

                try:
                    getKerberosTGT(principal, "", "", "", None, kdcHost=host)
                except Exception as e:
                    err = str(e)

                    if "KDC_ERR_PREAUTH_REQUIRED" in err:
                        result["user_exists"].append(user)

                    if "KDC_ERR_PREAUTH_REQUIRED" not in err and "KDC_ERR_C_PRINCIPAL_UNKNOWN" not in err:
                        result["asrep_roastable"].append(user)

            except:
                pass

    except Exception as e:
        result["error"] = str(e)

    return result


async def async_kerberos_enum(host, semaphore):
    async with semaphore:
        return await asyncio.to_thread(kerberos_enum, host)


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = [async_kerberos_enum(h, semaphore) for h in hosts]
    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("Kerberos enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async Kerberos Enumerator")
    parser.add_argument("-f", "--file", required=True, help="Input file with hosts")
    parser.add_argument("-o", "--output", default="kerberos_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
