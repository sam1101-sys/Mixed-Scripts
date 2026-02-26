import asyncio
import json
import argparse
from datetime import datetime
import socket
import ssl

import pytds

TIMEOUT = 5
GLOBAL_TIMEOUT = 15
CONCURRENCY = 10

DEFAULT_CREDS = [
    ("sa", ""),
    ("sa", "password"),
    ("sa", "admin"),
    ("sa", "123456"),
]


def tcp_connect(host, port=1433):
    try:
        s = socket.create_connection((host, port), timeout=TIMEOUT)
        s.close()
        return True
    except:
        return False


def try_login(host, username, password):
    try:
        conn = pytds.connect(
            server=host,
            database="master",
            user=username,
            password=password,
            timeout=TIMEOUT,
            login_timeout=TIMEOUT,
            as_dict=True
        )
        cursor = conn.cursor()
        cursor.execute("SELECT @@version")
        version = cursor.fetchone()

        cursor.execute("SELECT SYSTEM_USER")
        user = cursor.fetchone()

        cursor.execute("SELECT IS_SRVROLEMEMBER('sysadmin')")
        is_sysadmin = cursor.fetchone()

        cursor.execute("SELECT name FROM sys.databases")
        databases = cursor.fetchall()

        # Check xp_cmdshell (no execution)
        cursor.execute("""
            SELECT value_in_use 
            FROM sys.configurations 
            WHERE name = 'xp_cmdshell'
        """)
        xp_status = cursor.fetchone()

        conn.close()

        return {
            "success": True,
            "version": version,
            "system_user": user,
            "is_sysadmin": is_sysadmin,
            "databases": databases,
            "xp_cmdshell_enabled": xp_status
        }

    except Exception:
        return {"success": False}


async def enumerate_mssql(host, semaphore):
    async with semaphore:
        result = {
            "target": host,
            "port": 1433,
            "timestamp": datetime.utcnow().isoformat(),
            "open": False,
            "default_credentials_worked": [],
            "error": None
        }

        try:
            # TCP check
            open_port = await asyncio.to_thread(tcp_connect, host)
            result["open"] = open_port

            if not open_port:
                return result

            # Try default credentials
            for user, pwd in DEFAULT_CREDS:
                login_result = await asyncio.to_thread(
                    try_login, host, user, pwd
                )

                if login_result.get("success"):
                    result["default_credentials_worked"].append({
                        "username": user,
                        "password": pwd,
                        "details": login_result
                    })
                    break

        except Exception as e:
            result["error"] = str(e)

        return result


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [line.strip() for line in f if line.strip()]

    tasks = [enumerate_mssql(h, semaphore) for h in hosts]
    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4, default=str)

    print("MSSQL enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", required=True, help="Input file with hosts")
    parser.add_argument("-o", "--output", default="mssql_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
