import asyncio
import json
import argparse
import socket
from datetime import datetime
import psycopg2

TIMEOUT = 5
CONCURRENCY = 10

DEFAULT_CREDS = [
    ("postgres", ""),
    ("postgres", "postgres"),
    ("postgres", "password"),
    ("admin", "admin"),
]


def tcp_check(host):
    try:
        s = socket.create_connection((host, 5432), timeout=TIMEOUT)
        s.close()
        return True
    except:
        return False


def pg_enum(host):
    result = {
        "target": host,
        "port": 5432,
        "timestamp": datetime.utcnow().isoformat(),
        "reachable": False,
        "anonymous_login": False,
        "default_credentials_worked": [],
        "version": None,
        "databases": [],
        "roles": [],
        "superuser": False,
        "error": None
    }

    try:
        if not tcp_check(host):
            return result

        result["reachable"] = True

        # Anonymous login attempt
        try:
            conn = psycopg2.connect(
                host=host,
                user="",
                password="",
                connect_timeout=TIMEOUT
            )
            result["anonymous_login"] = True
            conn.close()
        except:
            pass

        # Try default credentials
        for user, pwd in DEFAULT_CREDS:
            try:
                conn = psycopg2.connect(
                    host=host,
                    user=user,
                    password=pwd,
                    connect_timeout=TIMEOUT
                )
                cursor = conn.cursor()

                # Version
                cursor.execute("SELECT version();")
                result["version"] = cursor.fetchone()[0]

                # Databases
                cursor.execute("SELECT datname FROM pg_database;")
                result["databases"] = [row[0] for row in cursor.fetchall()]

                # Roles
                cursor.execute("SELECT rolname, rolsuper FROM pg_roles;")
                roles = cursor.fetchall()
                result["roles"] = [r[0] for r in roles]

                # Superuser?
                for r in roles:
                    if r[1] is True:
                        result["superuser"] = True

                result["default_credentials_worked"].append({
                    "username": user,
                    "password": pwd
                })

                conn.close()
                break

            except:
                continue

    except Exception as e:
        result["error"] = str(e)

    return result


async def async_pg_enum(host, semaphore):
    async with semaphore:
        return await asyncio.to_thread(pg_enum, host)


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = [async_pg_enum(h, semaphore) for h in hosts]
    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("PostgreSQL enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async PostgreSQL Enumerator")
    parser.add_argument("-f", "--file", required=True, help="Input file with hosts")
    parser.add_argument("-o", "--output", default="postgres_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
