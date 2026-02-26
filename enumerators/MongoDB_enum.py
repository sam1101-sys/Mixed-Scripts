import asyncio
import json
import argparse
import socket
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure

TIMEOUT = 5
CONCURRENCY = 10

DEFAULT_CREDS = [
    ("admin", "admin"),
    ("root", "root"),
    ("mongo", "mongo"),
]


def tcp_check(host):
    try:
        s = socket.create_connection((host, 27017), timeout=TIMEOUT)
        s.close()
        return True
    except:
        return False


def mongo_enum(host):
    result = {
        "target": host,
        "port": 27017,
        "timestamp": datetime.utcnow().isoformat(),
        "reachable": False,
        "unauthenticated_access": False,
        "default_credentials_worked": [],
        "version": None,
        "databases": [],
        "collections_sample": {},
        "replica_set": None,
        "error": None
    }

    try:
        if not tcp_check(host):
            return result

        result["reachable"] = True

        # Unauthenticated access attempt
        try:
            client = MongoClient(
                host,
                27017,
                serverSelectionTimeoutMS=TIMEOUT * 1000
            )

            info = client.server_info()
            result["version"] = info.get("version")

            dbs = client.list_database_names()
            result["unauthenticated_access"] = True
            result["databases"] = dbs

            # Sample collections (limited)
            for db in dbs[:3]:
                try:
                    collections = client[db].list_collection_names()
                    result["collections_sample"][db] = collections[:5]
                except:
                    continue

            # Replica set info
            try:
                status = client.admin.command("replSetGetStatus")
                result["replica_set"] = status.get("set")
            except:
                pass

            client.close()
            return result

        except OperationFailure:
            pass
        except ServerSelectionTimeoutError:
            return result

        # Try default credentials
        for user, pwd in DEFAULT_CREDS:
            try:
                client = MongoClient(
                    host,
                    27017,
                    username=user,
                    password=pwd,
                    authSource="admin",
                    serverSelectionTimeoutMS=TIMEOUT * 1000
                )

                info = client.server_info()
                result["version"] = info.get("version")

                dbs = client.list_database_names()
                result["default_credentials_worked"].append({
                    "username": user,
                    "password": pwd
                })

                result["databases"] = dbs

                client.close()
                break

            except:
                continue

    except Exception as e:
        result["error"] = str(e)

    return result


async def async_mongo_enum(host, semaphore):
    async with semaphore:
        return await asyncio.to_thread(mongo_enum, host)


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = [async_mongo_enum(h, semaphore) for h in hosts]
    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4, default=str)

    print("MongoDB enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async MongoDB Enumerator")
    parser.add_argument("-f", "--file", required=True, help="Input file with hosts")
    parser.add_argument("-o", "--output", default="mongo_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
