import asyncio
import json
import argparse
import socket
from datetime import datetime
import pymysql

TIMEOUT = 5
CONCURRENCY = 10

DEFAULT_CREDS = [
    ("root", ""),
    ("root", "root"),
    ("root", "password"),
    ("admin", "admin"),
    ("test", "test"),
]


def tcp_check(host):
    try:
        s = socket.create_connection((host, 3306), timeout=TIMEOUT)
        s.close()
        return True
    except:
        return False


def mysql_enum(host):
    result = {
        "target": host,
        "port": 3306,
        "timestamp": datetime.utcnow().isoformat(),
        "reachable": False,
        "version": None,
        "anonymous_login": False,
        "default_credentials_worked": [],
        "databases": [],
        "users": [],
        "super_priv": False,
        "file_priv": False,
        "local_infile": None,
        "error": None
    }

    try:
        if not tcp_check(host):
            return result

        result["reachable"] = True

        # Attempt anonymous login
        try:
            conn = pymysql.connect(
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
                conn = pymysql.connect(
                    host=host,
                    user=user,
                    password=pwd,
                    connect_timeout=TIMEOUT,
                    cursorclass=pymysql.cursors.DictCursor
                )

                with conn.cursor() as cursor:
                    cursor.execute("SELECT VERSION()")
                    version = cursor.fetchone()
                    result["version"] = version

                    cursor.execute("SHOW DATABASES")
                    result["databases"] = cursor.fetchall()

                    cursor.execute("SELECT user FROM mysql.user")
                    result["users"] = cursor.fetchall()

                    cursor.execute("SHOW GRANTS FOR CURRENT_USER")
                    grants = cursor.fetchall()
                    grant_text = str(grants)

                    if "SUPER" in grant_text:
                        result["super_priv"] = True
                    if "FILE" in grant_text:
                        result["file_priv"] = True

                    cursor.execute("SHOW VARIABLES LIKE 'local_infile'")
                    local_infile = cursor.fetchone()
                    result["local_infile"] = local_infile

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


async def async_mysql_enum(host, semaphore):
    async with semaphore:
        return await asyncio.to_thread(mysql_enum, host)


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = [async_mysql_enum(h, semaphore) for h in hosts]
    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4, default=str)

    print("MySQL enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async MySQL Enumerator")
    parser.add_argument("-f", "--file", required=True, help="Input file with hosts")
    parser.add_argument("-o", "--output", default="mysql_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
