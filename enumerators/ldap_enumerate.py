import asyncio
import json
import argparse
from datetime import datetime
from ldap3 import Server, Connection, BASE, LEVEL, ALL, Tls
import ssl

TIMEOUT = 5
GLOBAL_TIMEOUT = 12
CONCURRENCY = 5
PORTS = [389, 636]


def ldap_enum_safe(host, port):
    result = {
        "target": host,
        "port": port,
        "timestamp": datetime.utcnow().isoformat(),
        "reachable": False,
        "anonymous_bind": False,
        "rootDSE": {},
        "naming_context": None,
        "users_sample": [],
        "error": None
    }

    try:
        use_ssl = port == 636
        tls = Tls(validate=ssl.CERT_NONE) if use_ssl else None

        server = Server(
            host,
            port=port,
            use_ssl=use_ssl,
            tls=tls,
            get_info=ALL,
            connect_timeout=TIMEOUT
        )

        conn = Connection(
            server,
            receive_timeout=TIMEOUT,
            auto_referrals=False
        )

        if not conn.bind():
            return result

        result["reachable"] = True

        # RootDSE (BASE only — safe)
        conn.search(
            search_base='',
            search_filter='(objectClass=*)',
            search_scope=BASE,
            attributes=['defaultNamingContext']
        )

        if conn.entries:
            result["anonymous_bind"] = True
            entry = conn.entries[0]

            naming_context = entry.defaultNamingContext.value
            result["naming_context"] = naming_context

            # LEVEL search only (not SUBTREE!)
            conn.search(
                search_base=naming_context,
                search_filter='(objectClass=user)',
                search_scope=LEVEL,
                attributes=['cn'],
                size_limit=10
            )

            result["users_sample"] = [
                str(e.cn) for e in conn.entries
            ]

        conn.unbind()

    except Exception as e:
        result["error"] = str(e)

    return result


async def async_ldap(host, port, semaphore):
    async with semaphore:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(ldap_enum_safe, host, port),
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
        for port in PORTS:
            tasks.append(async_ldap(host, port, semaphore))

    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("LDAP enumeration completed safely.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Safe LDAP Enumerator")
    parser.add_argument("-f", "--file", required=True)
    parser.add_argument("-o", "--output", default="ldap_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
