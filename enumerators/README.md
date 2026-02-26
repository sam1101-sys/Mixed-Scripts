# Enumerators Guide

This folder contains service enumeration scripts for automated pentest workflows.

## 1) Input Format
Create a targets file with one host/IP per line:

```txt
10.10.10.10
192.168.1.50
example.internal
```

Lines starting with `#` are treated as comments by most async scripts.

## 2) How To Run

## Legacy scripts (`-f`)
Most existing scripts use:

```bash
python3 <script>.py -f targets.txt -o output.json
```

Example:

```bash
python3 ftp_enum.py -f targets.txt -o ftp_results.json
```

## New async scripts (`-i`, optional `-p`, `-c`)
Newer async scripts use:

```bash
python3 <script>.py -i targets.txt -o output.json -p <ports> -c 20
```

Example:

```bash
python3 weblogic_enum_async.py -i targets.txt -o weblogic_results.json -c 30
```

Show script-specific options:

```bash
python3 <script>.py -h
```

## 3) Output Location
Each script writes JSON to the file passed in `-o/--output`. If omitted, each script has its own default output file name.

## 4) Expected Output Shape
Output is JSON. Shapes differ slightly by script.

## New async script format (top-level)

```json
{
  "generated_at": "2026-02-26T23:00:00+00:00",
  "service": "weblogic_http",
  "ports": [7001, 7002, 8001, 9001, 80, 443],
  "summary": {
    "total_targets": 2,
    "total_checks": 12,
    "reachable": 4
  },
  "results": [
    {
      "target": "10.10.10.10",
      "port": 7001,
      "reachable": true,
      "error": null
    }
  ]
}
```

## Typical per-target fields
- `target`, `port`, `service`, `timestamp`
- `reachable`
- service-specific details (`version`, `features`, `endpoints`, etc.)
- `error` (`null` when successful)
- `evidence` (for detailed protocol checks in async scripts)

## 5) Where To Look For Issues

## A) Script does not start
Run:

```bash
python3 <script>.py -h
```

If import errors appear, install missing packages.

Known missing dependencies seen during checks:
- `MongoDB_enum.py`: requires `pymongo`
- `kerberso_enum.py`: requires `impacket`
- `mssql_enum_multi.py`: requires `pytds`

## B) Target-level failures
Check `error` field inside each result object.

Common values:
- `tcp_unreachable: ...`
- `connect_failed: ...`
- `io_failed: ...`
- `unhandled_exception: ...`

## C) Empty or low findings
- Confirm target/port is correct and reachable.
- Increase concurrency carefully (`-c`) if scans are too slow.
- For async scripts, verify `-p` includes expected service ports.

## D) Syntax validation
Run full syntax check for all scripts:

```bash
python3 -m py_compile *.py
```

## 6) Quick Batch Examples

Run WebLogic async scan:

```bash
python3 weblogic_enum_async.py -i targets.txt -o weblogic_enum_results.json
```

Run AJP async scan:

```bash
python3 ajp_enum_async.py -i targets.txt -o ajp_enum_results.json
```

Run legacy SMTP scan:

```bash
python3 smtp_enum_multi.py -f targets.txt -o smtp_results.json
```

## 7) Current Script Inventory

- `9200_elastic.py`
- `MongoDB_enum.py`
- `PostgreSQL_enum.py`
- `SNMP_enumeration.py`
- `ajp_enum_async.py`
- `amqp_enum_async.py`
- `docker_api_enum_async.py`
- `docker_registry_enum_async.py`
- `ftp_enum.py`
- `ibmmq_enum_async.py`
- `java_rmi.py`
- `jdwp_enum.py`
- `kerberso_enum.py`
- `ldap_enumerate.py`
- `memcached_enum_async.py`
- `mqtt_enum_async.py`
- `mssql_enum_multi.py`
- `mssql_enum_multi_1434.py`
- `mysql_enum.py`
- `nats_enum_async.py`
- `nfs_enum.py`
- `redis_enum.py`
- `smb_enum.py`
- `smtp_enum_multi.py`
- `telnet_enum_multi.py`
- `vnc_enum.py`
- `weblogic_enum_async.py`
- `winrm_5985.py`
- `zookeeper_enum_async.py`
