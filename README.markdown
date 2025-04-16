# Mixed-Scripts

A collection of Python and Bash scripts for network scanning, analysis, and security auditing. These tools automate tasks such as IP range expansion, NFS share discovery, FTP anonymous login checks, and Nmap result processing, making them ideal for network administrators and security professionals.

## Scripts Overview

The repository includes the following scripts:

1. **CIDR_2_IP.py**:
   - Converts CIDR ranges (e.g., `192.168.1.0/24`) or IP ranges (e.g., `192.168.1.1-192.168.1.10`) from a file into a list of IP addresses.
   - Supports IPv4 and IPv6, with deduplication and output file options.
   - Useful for generating IP lists for network scans.

2. **nmap_xml_to_excel.py**:
   - Parses Nmap XML output and generates an Excel file with two sheets:
     - **Live Hosts**: IP addresses and hostnames.
     - **Port Details**: IP, port, protocol, service, product, version, and status.
   - Supports excluding specific ports and customizable output.

3. **nfs_automater.sh**:
   - Checks for NFS shares on a list of IPs or hostnames using `showmount`.
   - Outputs detailed share information and a list of hosts with shares to files.
   - Integrates with other scripts for network auditing.

4. **Pythonanonymouslogin.py**:
   - Tests FTP servers for anonymous login (username: `anonymous`, password: `anonymous`) on a list of IPs.
   - Supports non-standard ports, verbose error logging, and output files.
   - Useful for identifying insecure FTP configurations.

## Features

- **Automation**: Streamlines network scanning and analysis tasks.
- **Integration**: Scripts work together for a complete workflow (e.g., IP generation → scanning → analysis).
- **Portability**: Minimal dependencies, using Python standard libraries and common Linux tools.
- **Error Handling**: Robust validation and error reporting.
- **Open Source**: Licensed under the MIT License for free use and modification.

## Prerequisites

- **Python 3.3+**: Required for `CIDR_2_IP.py`, `nmap_xml_to_excel.py`, and `Pythonanonymouslogin.py`.
- **Python Packages** (for `nmap_xml_to_excel.py`):
  - `pandas`
  - `openpyxl`
  - Install with:
    ```bash
    pip install pandas openpyxl
    ```
- **Bash**: Required for `nfs_automater.sh`.
- **showmount**: Required for `nfs_automater.sh` (part of `nfs-common` or `nfs-utils`).
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

1. Clone the repository:

   ```bash
   git clone https://github.com/sam1101-sys/Mixed-Scripts.git
   cd Mixed-Scripts
   ```

2. Install Python dependencies (for `nmap_xml_to_excel.py`):

   ```bash
   pip install pandas openpyxl
   ```

3. Make Bash scripts executable:

   ```bash
   chmod +x nfs_automater.sh
   ```

4. Verify prerequisites:

   ```bash
   python3 --version
   showmount --version
   ```

## Usage

Each script has its own usage instructions, summarized below. See individual READMEs in subdirectories for details.

### 1. CIDR_2_IP.py
Generate IP addresses from CIDR or IP ranges:

```bash
echo "192.168.1.0/24" > ranges.txt
python CIDR_2_IP.py -f ranges.txt -o ips.txt
```

### 2. nmap_xml_to_excel.py
Convert Nmap XML to Excel:

```bash
nmap -sV -oX scan.xml 192.168.1.0/24
python nmap_xml_to_excel.py scan.xml --output report.xlsx
```

### 3. nfs_automater.sh
Check for NFS shares:

```bash
echo -e "192.168.1.1\n192.168.1.2" > hosts.txt
./nfs_automater.sh hosts.txt
```

### 4. Pythonanonymouslogin.py
Test FTP anonymous logins:

```bash
echo -e "192.168.1.1\n192.168.1.2" > ips.txt
python Pythonanonymouslogin.py -f ips.txt -o ftp_results.txt
```

### Example Workflow
Combine scripts for a comprehensive network audit:

```bash
# Generate IP list
echo "192.168.1.0/24" > ranges.txt
python CIDR_2_IP.py -f ranges.txt -o ips.txt

# Check NFS shares
./nfs_automater.sh ips.txt

# Scan for FTP servers
nmap -iL ips.txt -p 21 -sV -oX ftp_scan.xml
python nmap_xml_to_excel.py ftp_scan.xml --output ftp_report.xlsx

# Test FTP anonymous logins (use IPs with open port 21)
python Pythonanonymouslogin.py -f ftp_ips.txt -o ftp_results.txt
```

## Directory Structure

```
Mixed-Scripts/
├── CIDR_2_IP/
│   ├── CIDR_2_IP.py
│   ├── README.md
├── ftp_anonymous_login/
│   ├── Pythonanonymouslogin.py
│   ├── README.md
├── nmap_xml_to_excel/
│   ├── nmap_xml_to_excel.py
│   ├── README.md
├── nfs_automater/
│   ├── nfs_automater.sh
│   ├── README.md
├── LICENSE
├── README.md
```

## Debugging

If scripts produce unexpected results:

- **Verify Inputs**:
  ```bash
  cat <input_file>
  ```
  Ensure files contain valid IPs, hostnames, or Nmap XML.

- **Check Dependencies**:
  ```bash
  python3 --version
  pip show pandas openpyxl
  showmount --version
  ```

- **Test Connectivity**:
  ```bash
  ping -c 1 192.168.1.1
  nmap -p 21 192.168.1.1
  showmount -e 192.168.1.1
  ```

- **Verbose Mode** (for `Pythonanonymouslogin.py`):
  ```bash
  python Pythonanonymouslogin.py -f ips.txt -v
  ```

- **Check Output Files**:
  ```bash
  cat <output_file>
  ```

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for bug reports, feature requests, or improvements. Follow these steps:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Shamya

## Acknowledgments

- Built with Python (`ipaddress`, `ftplib`, `argparse`, `pandas`, `openpyxl`) and Bash (`showmount`).
- Designed for network security and administration tasks.
- Inspired by the need to automate network auditing workflows.