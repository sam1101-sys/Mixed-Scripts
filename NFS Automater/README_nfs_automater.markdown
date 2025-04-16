# NFS Automater

A Bash script to automate the discovery of NFS (Network File System) shares on a list of IP addresses or hostnames. It queries each host using `showmount` and logs the results to files, making it useful for network auditing and security assessments.

## Features

- **NFS Share Detection**: Identifies NFS exports on specified hosts using `showmount -e`.
- **Input Flexibility**: Reads IPs or hostnames from a file, one per line.
- **Output Files**:
  - `nfs_share_results.txt`: Detailed NFS share information.
  - `nfs_found_ips.txt`: List of hosts with NFS shares.
- **Error Handling**: Validates input files, checks for `showmount`, and handles unresponsive hosts.
- **Overwrite Protection**: Prompts before overwriting existing output files.
- **Integration**: Works with `CIDR_2_IP.py` and `nmap_xml_to_excel.py` for comprehensive network scanning.

## Prerequisites

- Bash-compatible shell (e.g., `/bin/bash`).
- `showmount` command (part of `nfs-common` or `nfs-utils`).
  - Install on Debian/Ubuntu:
    ```bash
    sudo apt update
    sudo apt install nfs-common
    ```
  - Install on Red Hat/CentOS:
    ```bash
    sudo yum install nfs-utils
    ```

## Installation

1. Clone the repository or download `nfs_automater.sh`:

   ```bash
   git clone https://github.com/sam1101-sys/Mixed-Scripts.git
   cd Mixed-Scripts
   ```

2. Make the script executable:

   ```bash
   chmod +x nfs_automater.sh
   ```

3. Ensure `showmount` is installed:

   ```bash
   showmount --version
   ```

## Usage

1. Create a file with IP addresses or hostnames, one per line. Example (`hosts.txt`):

   ```
   192.168.1.1
   192.168.1.2
   example.com
   ```

2. Run the script:

   ```bash
   ./nfs_automater.sh hosts.txt
   ```

### Example Output

**Input File (`hosts.txt`)**:
```
192.168.1.1
192.168.1.2
```

**Command**:
```bash
./nfs_automater.sh hosts.txt
```

**Terminal Output** (if `192.168.1.1` has shares):
```
NFS shares found on 192.168.1.1:
/export  192.168.1.0/24
----------------------
Results have been saved to nfs_share_results.txt
List of IPs with NFS shares saved to nfs_found_ips.txt
```

**Output Files**:
- `nfs_share_results.txt`:
  ```
  NFS shares found on 192.168.1.1:
/export  192.168.1.0/24
----------------------
No NFS shares found on 192.168.1.2
----------------------
  ```
- `nfs_found_ips.txt`:
  ```
  192.168.1.1
  ```

## Integration with Other Tools

Combine with `CIDR_2_IP.py` and `nmap_xml_to_excel.py` for a full network scanning workflow:

```bash
# Generate IP list
echo "192.168.1.0/24" > ranges.txt
python CIDR_2_IP.py -f ranges.txt -o ips.txt

# Check for NFS shares
./nfs_automater.sh ips.txt

# Scan NFS hosts
nmap -iL nfs_found_ips.txt -p 2049 -sV -oX nfs_scan.xml
python nmap_xml_to_excel.py nfs_scan.xml --output nfs_report.xlsx
```

## Debugging

If no shares are found or errors occur:

- **Verify Input File**:
  ```bash
  cat hosts.txt
  ```
  Ensure it contains valid IPs or hostnames.

- **Check `showmount`**:
  ```bash
  showmount -e 192.168.1.1
  ```

- **Test Connectivity**:
  ```bash
  ping -c 1 192.168.1.1
  ```

- **Check Output Files**:
  ```bash
  cat nfs_share_results.txt
  ```

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for bug reports, feature requests, or improvements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Shamya

## Acknowledgments

- Built with Bash and `showmount`.
- Designed for network administrators and security professionals.