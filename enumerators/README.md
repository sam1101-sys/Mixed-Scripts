# Enumerators Guide

## Purpose
This folder contains service-specific enumeration scripts for read-only pentest discovery.

## Input File
Use a plain text file with one host/IP per line:

```txt
10.10.10.10
192.168.1.25
example.internal
```

## How To Run

## Legacy scripts
Use:

```bash
python3 <script>.py -f targets.txt -o output.json
```

## Async scripts
Use:

```bash
python3 <script>.py -i targets.txt -o output.json -p <ports> -c 20
```

Get script options:

```bash
python3 <script>.py -h
```

## Output
Each script writes JSON to the file passed with `-o`.

## Dependency Notes (current environment)
- `MongoDB_enum.py`: needs `pymongo`
- `kerberso_enum.py`: needs `impacket`
- `mssql_enum_multi.py`: needs `pytds`

## Security Findings: What Counts As An Issue
Treat these as security findings in output:
- Unauthenticated or anonymous access is allowed
- Default credentials work
- Sensitive/admin/debug interfaces are exposed
- Weak auth modes are enabled (no auth, null session, insecure protocol)
- Service/version exposure maps to known vulnerable families

Use `error` only for operational failures (timeout/import/network), not as a security finding.

## Per-Script Findings + Sample Output

## 9200_elastic.py
Security issues/findings:
- `unauthenticated_access: true`
- `security_enabled: false`
- `indices` or `snapshot_repositories` exposed without auth

Sample output:
```json
{"target":"10.10.10.10","port":9200,"reachable":true,"unauthenticated_access":true,"version":"7.10.2","security_enabled":false,"indices":["users"],"error":null}
```

## MongoDB_enum.py
Security issues/findings:
- `unauthenticated_access: true`
- `default_credentials_worked` not empty
- `databases`/`collections_sample` exposed

Sample output:
```json
{"target":"10.10.10.20","port":27017,"reachable":true,"unauthenticated_access":true,"default_credentials_worked":["admin:admin"],"version":"6.0.6","databases":["admin","app"],"error":null}
```

## PostgreSQL_enum.py
Security issues/findings:
- `anonymous_login: true`
- `default_credentials_worked` not empty
- `superuser: true`

Sample output:
```json
{"target":"10.10.10.30","port":5432,"reachable":true,"anonymous_login":false,"default_credentials_worked":["postgres:postgres"],"version":"14.10","roles":["postgres"],"superuser":true,"error":null}
```

## SNMP_enumeration.py
Security issues/findings:
- `working_community` found (`public`/`private` etc.)
- `system_info` returns sensitive host metadata

Sample output:
```json
{"target":"10.10.10.40","port":161,"responsive":true,"working_community":"public","system_info":{"sysName":"router1"},"error":null}
```

## ftp_enum.py
Security issues/findings:
- `anonymous_login_allowed: true`
- `default_credentials_worked` not empty
- `writable_directory: true`

Sample output:
```json
{"target":"10.10.10.50","port":21,"banner":"220 FTP Server","anonymous_login_allowed":true,"default_credentials_worked":[],"writable_directory":false,"error":null}
```

## java_rmi.py
Security issues/findings:
- `jrmi_detected: true` (exposed RMI surface)
- `possible_registry: true`
- `jmx_detected: true`

Sample output:
```json
{"target":"10.10.10.60","port":1099,"reachable":true,"jrmi_detected":true,"possible_registry":true,"jmx_detected":false,"ssl_possible":false,"error":null}
```

## jdwp_enum.py
Security issues/findings:
- `jdwp_exposed: true` (high-risk debug interface)

Sample output:
```json
{"target":"10.10.10.61","port":5005,"reachable":true,"jdwp_exposed":true,"vm_version_response":"Java Debug Wire Protocol (Reference Implementation)","error":null}
```

## kerberso_enum.py
Security issues/findings:
- `asrep_roastable` not empty
- `user_exists` leakage supports user enumeration

Sample output:
```json
{"target":"10.10.10.70","port":88,"reachable":true,"realm_detected":"CORP.LOCAL","user_exists":["svc_backup"],"asrep_roastable":["legacyuser"],"error":null}
```

## ldap_enumerate.py
Security issues/findings:
- `anonymous_bind: true`
- `rootDSE` leaks naming contexts/server metadata without auth

Sample output:
```json
{"target":"10.10.10.80","port":389,"reachable":true,"anonymous_bind":true,"rootDSE":{"namingContexts":["dc=corp,dc=local"]},"error":null}
```

## mssql_enum_multi.py
Security issues/findings:
- `open: true`
- `default_credentials_worked` not empty

Sample output:
```json
{"target":"10.10.10.90","port":1433,"open":true,"default_credentials_worked":["sa:Password123"],"error":null}
```

## mssql_enum_multi_1434.py
Security issues/findings:
- `responsive: true` with exposed SQL Browser instance metadata
- `instances` reveals server naming/topology

Sample output:
```json
{"target":"10.10.10.91","port":1434,"responsive":true,"instances":[{"ServerName":"SQL01","InstanceName":"MSSQLSERVER"}],"error":null}
```

## mysql_enum.py
Security issues/findings:
- `anonymous_login: true`
- `default_credentials_worked` not empty
- `super_priv: true` or `file_priv: true`
- `local_infile: true`

Sample output:
```json
{"target":"10.10.10.100","port":3306,"reachable":true,"version":"8.0.35","anonymous_login":false,"default_credentials_worked":["root:root"],"super_priv":true,"file_priv":true,"local_infile":true,"error":null}
```

## nfs_enum.py
Security issues/findings:
- `exports_found: true`
- `exports` contains sensitive shared paths

Sample output:
```json
{"target":"10.10.10.110","port":2049,"reachable":true,"exports_found":true,"exports":["/srv/backups *(rw,sync,no_root_squash)"],"error":null}
```

## redis_enum.py
Security issues/findings:
- `unauthenticated_access: true`
- `requirepass` unset/false
- `protected_mode: no/false`

Sample output:
```json
{"target":"10.10.10.120","port":6379,"reachable":true,"unauthenticated_access":true,"version":"7.0.15","protected_mode":"no","requirepass":false,"sample_keys":["session:1"],"error":null}
```

## smb_enum.py
Security issues/findings:
- `null_session: true`
- `admin_share_access: true` or `ipc_access: true`
- `signing_required: false`
- `smbv1: true`

Sample output:
```json
{"target":"10.10.10.130","port":445,"reachable":true,"os":"Windows Server 2019","smbv1":false,"signing_required":false,"null_session":true,"shares":["IPC$","C$"],"admin_share_access":true,"error":null}
```

## smtp_enum_multi.py
Security issues/findings:
- `open_relay: true`
- `vrfy: true` or `expn: true`
- weak/legacy `auth` options exposed

Sample output:
```json
{"target":"10.10.10.140","port":25,"open":true,"banner":"220 mail","starttls":false,"auth":["LOGIN","PLAIN"],"vrfy":true,"expn":false,"open_relay":true,"error":null}
```

## telnet_enum_multi.py
Security issues/findings:
- `open: true` (cleartext remote access)
- sensitive `banner`/`ntlm_info` leakage

Sample output:
```json
{"target":"10.10.10.150","port":23,"open":true,"banner":"Welcome to BusyBox","negotiate":"IAC WILL ECHO","ntlm_info":null,"error":null}
```

## vnc_enum.py
Security issues/findings:
- `no_auth: true`
- exposed auth methods indicate weak access controls

Sample output:
```json
{"target":"10.10.10.160","port":5900,"reachable":true,"rfb_version":"RFB 003.008","auth_methods":[1,2],"no_auth":true,"vnc_auth_supported":true,"error":null}
```

## winrm_5985.py
Security issues/findings:
- `wsman_endpoint: true` exposed to untrusted network
- `basic_supported: true` on HTTP (5985)

Sample output:
```json
{"target":"10.10.10.170","port":5985,"reachable":true,"wsman_endpoint":true,"http_status":401,"auth_methods":["Negotiate","NTLM","Basic"],"ntlm_supported":true,"basic_supported":true,"error":null}
```

## ajp_enum_async.py
Security issues/findings:
- `ajp13_detected: true`
- `cpong_received: true` confirms active AJP listener

Sample output:
```json
{"target":"10.10.10.180","port":8009,"service":"ajp","reachable":true,"ajp13_detected":true,"cpong_received":true,"supported_methods":[],"error":null}
```

## amqp_enum_async.py
Security issues/findings:
- `amqp_detected: true` on exposed broker port
- `protocol_header_accepted: true` unauth broker handshake surface

Sample output:
```json
{"target":"10.10.10.181","port":5672,"service":"amqp","reachable":true,"amqp_detected":true,"protocol_header_accepted":true,"response_hex":"0100000000000000","error":null}
```

## docker_api_enum_async.py
Security issues/findings:
- `api_accessible: true`
- `containers` list retrievable without auth
- `/info` and `/version` exposed

Sample output:
```json
{"target":"10.10.10.182","port":2375,"service":"docker_api","reachable":true,"api_accessible":true,"version":{"version":"26.1.3"},"containers":[{"id":"abc","image":"nginx:latest"}],"error":null}
```

## docker_registry_enum_async.py
Security issues/findings:
- `registry_api_available: true`
- `catalog` readable without auth
- `tags` enumeration exposed

Sample output:
```json
{"target":"10.10.10.183","port":5000,"service":"docker_registry","reachable":true,"registry_api_available":true,"distribution_api_version":"registry/2.0","catalog":["backend/app"],"tags":{"backend/app":["latest"]},"error":null}
```

## ibmmq_enum_async.py
Security issues/findings:
- `mq_listener_detected: true` internet-exposed MQ listener
- `banner`/`version` leaked

Sample output:
```json
{"target":"10.10.10.184","port":1414,"service":"ibm_mq","reachable":true,"mq_listener_detected":true,"version":"9.3.2","banner":"AMQ...","error":null}
```

## memcached_enum_async.py
Security issues/findings:
- `memcached_detected: true` on exposed host
- `stats`/`slabs` data accessible without auth

Sample output:
```json
{"target":"10.10.10.185","port":11211,"service":"memcached","reachable":true,"memcached_detected":true,"version":"1.6.21","stats":{"curr_items":"142"},"slabs":{"1":{"chunk_size":"96"}},"error":null}
```

## mqtt_enum_async.py
Security issues/findings:
- `mqtt_detected: true` + accepted unauth connect
- `supported_protocol_levels` includes modern versions without auth gating

Sample output:
```json
{"target":"10.10.10.186","port":1883,"service":"mqtt","reachable":true,"mqtt_detected":true,"supported_protocol_levels":[4,5],"features":{"session_present_supported":false,"auth_required_or_rejected":false},"error":null}
```

## nats_enum_async.py
Security issues/findings:
- `nats_detected: true` exposed broker
- `features.auth_required: false` from server INFO
- cluster/version metadata leakage

Sample output:
```json
{"target":"10.10.10.187","port":4222,"service":"nats","reachable":true,"nats_detected":true,"version":"2.10.18","cluster":"nats-cluster","features":{"auth_required":false,"jetstream":true},"error":null}
```

## weblogic_enum_async.py
Security issues/findings:
- `admin_console_exposed: true`
- `wls_wsat_exposed: true`
- `bea_wls_internal_exposed: true`
- `t3_probe.t3_detected: true`
- `version_risk.potentially_vulnerable: true`

Sample output:
```json
{"target":"10.10.10.188","port":7001,"service":"weblogic_http","reachable":true,"weblogic_detected":true,"version":"12.2.1.4","admin_console_exposed":true,"wls_wsat_exposed":true,"bea_wls_internal_exposed":false,"t3_probe":{"t3_detected":true},"version_risk":{"potentially_vulnerable":true,"notable_cves":["CVE-2020-14882","CVE-2023-21839"]},"error":null}
```

## zookeeper_enum_async.py
Security issues/findings:
- `zookeeper_detected: true`
- `four_letter` commands (`ruok/stat/envi`) accessible remotely
- `mode`/`version` leakage

Sample output:
```json
{"target":"10.10.10.189","port":2181,"service":"zookeeper","reachable":true,"zookeeper_detected":true,"version":"3.7.2","mode":"follower","four_letter":{"ruok":{"ok":true,"response":"imok"}},"error":null}
```

## Troubleshooting / Where To Look For Issues

## Security issues (actual findings)
Check service-specific flags above in each result object.

## Operational issues (scan failures)
Check `error` fields:
- `tcp_unreachable: ...`
- `connect_failed: ...`
- `io_failed: ...`
- `unhandled_exception: ...`

## Quick sanity checks
```bash
python3 -m py_compile *.py
python3 <script>.py -h
```
