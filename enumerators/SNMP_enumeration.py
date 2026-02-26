import asyncio
import json
import argparse
from datetime import datetime
from pysnmp.hlapi import *

TIMEOUT = 3
CONCURRENCY = 20

COMMUNITY_STRINGS = [
    "public",
    "private",
    "manager",
    "admin"
]


OIDS = {
    "sysDescr": "1.3.6.1.2.1.1.1.0",
    "sysName": "1.3.6.1.2.1.1.5.0",
    "sysLocation": "1.3.6.1.2.1.1.6.0",
    "sysContact": "1.3.6.1.2.1.1.4.0",
}

INTERFACE_OID = "1.3.6.1.2.1.2.2.1.2"
IP_OID = "1.3.6.1.2.1.4.20.1.1"
PROCESS_OID = "1.3.6.1.2.1.25.4.2.1.2"
SOFTWARE_OID = "1.3.6.1.2.1.25.6.3.1.2"


def snmp_get(host, community, oid):
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=1),  # v2c
        UdpTransportTarget((host, 161), timeout=TIMEOUT, retries=0),
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )

    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

    if errorIndication or errorStatus:
        return None

    for varBind in varBinds:
        return str(varBind[1])

    return None


def snmp_walk(host, community, oid):
    results = []

    for (errorIndication,
         errorStatus,
         errorIndex,
         varBinds) in nextCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=1),
        UdpTransportTarget((host, 161), timeout=TIMEOUT, retries=0),
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
        lexicographicMode=False
    ):

        if errorIndication or errorStatus:
            break

        for varBind in varBinds:
            results.append(str(varBind[1]))

    return results


async def enumerate_snmp(host, semaphore):
    async with semaphore:
        result = {
            "target": host,
            "port": 161,
            "timestamp": datetime.utcnow().isoformat(),
            "responsive": False,
            "working_community": None,
            "system_info": {},
            "interfaces": [],
            "ip_addresses": [],
            "processes": [],
            "installed_software": [],
            "error": None
        }

        try:
            for community in COMMUNITY_STRINGS:
                test = await asyncio.to_thread(snmp_get, host, community, OIDS["sysDescr"])
                if test:
                    result["responsive"] = True
                    result["working_community"] = community
                    break

            if not result["responsive"]:
                return result

            comm = result["working_community"]

            # System info
            for key, oid in OIDS.items():
                val = await asyncio.to_thread(snmp_get, host, comm, oid)
                if val:
                    result["system_info"][key] = val

            # Interfaces
            result["interfaces"] = await asyncio.to_thread(
                snmp_walk, host, comm, INTERFACE_OID
            )

            # IP addresses
            result["ip_addresses"] = await asyncio.to_thread(
                snmp_walk, host, comm, IP_OID
            )

            # Processes
            result["processes"] = await asyncio.to_thread(
                snmp_walk, host, comm, PROCESS_OID
            )

            # Installed software
            result["installed_software"] = await asyncio.to_thread(
                snmp_walk, host, comm, SOFTWARE_OID
            )

        except Exception as e:
            result["error"] = str(e)

        return result


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = [enumerate_snmp(h, semaphore) for h in hosts]
    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("SNMP enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async SNMP Enumerator")
    parser.add_argument("-f", "--file", required=True, help="Input file with hosts")
    parser.add_argument("-o", "--output", default="snmp_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
