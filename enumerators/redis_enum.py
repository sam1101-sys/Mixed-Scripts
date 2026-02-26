import asyncio
import json
import argparse
import socket
from datetime import datetime
import redis

TIMEOUT = 5
CONCURRENCY = 10


def tcp_check(host):
    try:
        s = socket.create_connection((host, 6379), timeout=TIMEOUT)
        s.close()
        return True
    except:
        return False


def redis_enum(host):
    result = {
        "target": host,
        "port": 6379,
        "timestamp": datetime.utcnow().isoformat(),
        "reachable": False,
        "unauthenticated_access": False,
        "version": None,
        "role": None,
        "config_dir": None,
        "dbsize": None,
        "sample_keys": [],
        "protected_mode": None,
        "requirepass": None,
        "error": None
    }

    try:
        if not tcp_check(host):
            return result

        result["reachable"] = True

        r = redis.Redis(
            host=host,
            port=6379,
            socket_timeout=TIMEOUT,
            decode_responses=True
        )

        # Try simple PING
        r.ping()
        result["unauthenticated_access"] = True

        # INFO
        info = r.info()
        result["version"] = info.get("redis_version")
        result["role"] = info.get("role")
        result["protected_mode"] = info.get("protected_mode")

        # CONFIG GET (read-only)
        try:
            config = r.config_get("*")
            result["config_dir"] = config.get("dir")
            result["requirepass"] = config.get("requirepass")
        except:
            pass

        # DB size
        try:
            result["dbsize"] = r.dbsize()
        except:
            pass

        # Sample keys (limited)
        try:
            keys = r.keys("*")
            result["sample_keys"] = keys[:10]
        except:
            pass

    except redis.exceptions.AuthenticationError:
        result["unauthenticated_access"] = False
    except Exception as e:
        result["error"] = str(e)

    return result


async def async_redis_enum(host, semaphore):
    async with semaphore:
        return await asyncio.to_thread(redis_enum, host)


async def main(input_file, output_file):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    with open(input_file, "r") as f:
        hosts = [h.strip() for h in f if h.strip()]

    tasks = [async_redis_enum(h, semaphore) for h in hosts]
    results = await asyncio.gather(*tasks)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print("Redis enumeration completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async Redis Enumerator")
    parser.add_argument("-f", "--file", required=True, help="Input file with hosts")
    parser.add_argument("-o", "--output", default="redis_results.json")
    args = parser.parse_args()

    asyncio.run(main(args.file, args.output))
