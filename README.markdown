# Mixed-Scripts

A collection of Python and Bash scripts for network scanning, analysis, security auditing, and visualization. These tools automate tasks such as IP range processing, service discovery, vulnerability checks, database connectivity testing, web screenshot capture, and scan result formatting, designed for network administrators and security professionals.

## Scripts Overview

1. **CIDR_2_IP.py**:
   - Converts CIDR ranges (e.g., `192.168.1.0/24`) or IP ranges (e.g., `192.168.1.1-192.168.1.10`) into a list of IPs.
   - Supports IPv4/IPv6, deduplication, and output files.

2. **nmap_xml_to_excel.py**:
   - Parses Nmap XML into an Excel file with:
     - **Live Hosts**: IPs and hostnames.
     - **Port Details**: IP, port, protocol, service, product, version, status.
   - Supports port exclusion.

3. **nfs_automater.sh**:
   - Detects NFS shares on IPs/hostnames using `showmount`.
   - Outputs share details and hosts with shares.

4. **Pythonanonymouslogin.py**:
   - Tests FTP servers for anonymous login vulnerabilities.
   - Supports custom ports, verbose logging, and output files.

5. **extractIP.py**:
   - Extracts host IPs from CIDR ranges, excluding network/broadcast addresses.
   - Processes multiple files with output file option.

6. **overlap.py**:
   - Finds overlapping IP ranges (CIDR or IP ranges) between two files.
   - Optimizes scan range selection.

7. **overlap_multiple.py**:
   - Extends `overlap.py` for multiple files.
   - Identifies overlaps across datasets.

8. **query.py**:
   - Converts CIDR ranges into query format (e.g., `asset.ipv4 BETWEEN x AND y`).
   - Aids IP filtering for external tools.

9. **check_psql_connections.sh**:
   - Tests PostgreSQL connectivity on IPs using `psql`.
   - Reports connection success/failure with customizable username and port.

10. **screenshot.sh**:
    - Captures screenshots of web pages at IP:port using headless Chrome.
    - Saves PNGs in a timestamped directory, with protocol detection (http/https).

## Features

- **Automation**: Simplifies IP management, service checks, and visualization.
- **Integration**: Scripts form a cohesive network auditing workflow.
- **Portability**: Uses Python standard libraries and common Linux tools.
- **Error Handling**: Robust validation and reporting.
- **Open Source**: MIT License.

## Prerequisites

- **Python 3.3+**: For Python scripts.
- **Python Packages** (for `nmap_xml_to_excel.py`):
  - `pandas`, `openpyxl`
  - Install:
    ```bash
    pip install pandas openpyxl
    ```
- **Bash**: For `nfs_automater.sh`, `check_psql_connections.sh`, `screenshot.sh`.
- **showmount**: For `nfs_automater.sh`.
  - Install (Debian/Ubuntu):
    ```bash
    sudo apt update
    sudo apt install nfs-common
    ```
- **psql**: For `check_psql_connections.sh`.
  - Install (Debian/Ubuntu):
    ```bash
    sudo apt install postgresql-client
    ```
- **google-chrome**: For `screenshot.sh`.
  - Install (Debian/Ubuntu):
    ```bash
    sudo apt install google-chrome-stable
    ```

## Installation

```bash
git clone https://github.com/sam1101-sys/Mixed-Scripts.git
cd Mixed-Scripts
pip install pandas openpyxl
chmod +x *.sh
```

Verify:
```bash
python3 --version
showmount --version
psql --version
google-chrome --version
```

## Usage

### CIDR_2_IP.py
```bash
echo "192.168.1.0/24" > ranges.txt
python CIDR_2_IP.py -f ranges.txt -o ips.txt
```

### nmap_xml_to_excel.py
```bash
nmap -sV -oX scan.xml 192.168.1.0/24
python nmap_xml_to_excel.py scan.xml --output report.xlsx
```

### nfs_automater.sh
```bash
echo -e "192.168.1.1\n192.168.1.2" > hosts.txt
./nfs_automater.sh hosts.txt
```

### Pythonanonymouslogin.py
```bash
echo -e "192.168.1.1\n192.168.1.2" > ips.txt
python Pythonanonymouslogin.py -f ips.txt -o ftp_results.txt
```

### extractIP.py
```bash
echo "192.168.1.0/30" > ranges.txt
python extractIP.py -f ranges.txt -o hosts.txt
```

### overlap.py
```bash
echo "192.168.1.0/30" > file1.txt
echo "192.168.1.0-192.168.1.5" > file2.txt
python overlap.py -f file1.txt file2.txt
```

### overlap_multiple.py
```bash
echo "192.168.2.0/24" > file3.txt
python overlap_multiple.py -f file1.txt file2.txt file3.txt
```

### query.py
```bash
python query.py -f ranges.txt
```

### check_psql_connections.sh
```bash
echo -e "192.168.1.1\n192.168.1.2" > ips.txt
./check_psql_connections.sh -h ips.txt -o psql_results.txt
```

### screenshot.sh
```bash
echo -e "192.168.1.1:80\n192.168.1.2:443" > urls.txt
./screenshot.sh -f urls.txt
```

### Example Workflow
```bash
# Generate IPs
echo "192.168.1.0/24" > ranges.txt
python extractIP.py -f ranges.txt -o hosts.txt
python CIDR_2_IP.py -f ranges.txt -o all_ips.txt

# Check overlaps
python overlap_multiple.py -f ranges.txt other_ranges.txt

# Generate query
python query.py -f ranges.txt > query.txt

# Scan services
./nfs_automater.sh hosts.txt
python Pythonanonymouslogin.py -f hosts.txt -o ftp_results.txt
./check_psql_connections.sh -h hosts.txt -o psql_results.txt

# Capture web screenshots
sed 's/$/:80/' hosts.txt > urls.txt
./screenshot.sh -f urls.txt

# Analyze with Nmap
nmap -iL hosts.txt -sV -oX scan.xml
python nmap_xml_to_excel.py scan.xml --output report.xlsx
```

## Directory Structure

```
Mixed-Scripts/
├── CIDR_2_IP/
│   ├── CIDR_2_IP.py
│   ├── README.md
├── extractIP/
│   ├── extractIP.py
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
├── overlap/
│   ├── overlap.py
│   ├── README.md
├── overlap_multiple/
│   ├── overlap_multiple.py
│   ├── README.md
├── query/
│   ├── query.py
│   ├── README.md
├── check_psql_connections/
│   ├── check_psql_connections.sh
│   ├── README.md
├── screenshot/
│   ├── screenshot.sh
│   ├── README.md
├── LICENSE
├── README.md
```

## Debugging

- **Verify Inputs**: `cat <input_file>`
- **Check Dependencies**:
  ```bash
  python3 --version
  pip show pandas openpyxl
  showmount --version
  psql --version
  google-chrome --version
  ```
- **Test Connectivity**: `ping -c 1 192.168.1.1`
- **Verbose Mode** (for `Pythonanonymouslogin.py`):
  ```bash
  python Pythonanonymouslogin.py -f ips.txt -v
  ```
- **Check Outputs**: `cat <output_file>`, `ls screenshots_*`

## Contributing

Submit pull requests or issues:
1. Fork the repo.
2. Create a branch (`git checkout -b feature/your-feature`).
3. Commit (`git commit -m "Add feature"`).
4. Push (`git push origin feature/your-feature`).
5. Open a pull request.

## License

Licensed under the MIT License. See [LICENSE](LICENSE).

Copyright (c) 2025 Shamya

## Acknowledgments

- Built with Python (`ipaddress`, `ftplib`, `argparse`, `pandas`, `openpyxl`) and Bash (`showmount`, `psql`, `google-chrome`).
- Designed for network security, auditing, and visualization.