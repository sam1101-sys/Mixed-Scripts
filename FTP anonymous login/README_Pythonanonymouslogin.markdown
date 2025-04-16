# FTP Anonymous Login Checker

A Python script to check for FTP servers allowing anonymous logins on a list of IP addresses. It attempts to connect to each IP using the `anonymous` username and password, reporting whether login is possible. Ideal for network security audits.

## Features

- **Anonymous Login Check**: Tests FTP servers for anonymous access (username: `anonymous`, password: `anonymous`).
- **Input Flexibility**: Reads IPs from a file, one per line.
- **Output Options**: Prints results to stdout or saves to a file using `--output`.
- **Custom Port Support**: Specify non-standard FTP ports with `--port`.
- **Verbose Mode**: Show detailed error messages with `--verbose`.
- **IP Validation**: Skips invalid IPs using `ipaddress`.
- **No External Dependencies**: Uses Python’s standard library (`ftplib`, `argparse`, `ipaddress`).

## Prerequisites

- Python 3.3 or higher (due to `ipaddress` module).

No external packages are required.

## Installation

1. Clone the repository or download `Pythonanonymouslogin.py`:

   ```bash
   git clone https://github.com/sam1101-sys/Mixed-Scripts.git
   cd Mixed-Scripts
   ```

2. Ensure Python 3 is installed:

   ```bash
   python3 --version
   ```

## Usage

1. Create a file with IP addresses, one per line. Example (`ips.txt`):

   ```
   192.168.1.1
   192.168.1.2
   ```

2. Run the script:

   ```bash
   python Pythonanonymouslogin.py -f ips.txt
   ```

3. Save results to a file and use a non-standard port:

   ```bash
   python Pythonanonymouslogin.py -f ips.txt -o ftp_results.txt -p 2121
   ```

4. Enable verbose mode for detailed errors:

   ```bash
   python Pythonanonymouslogin.py -f ips.txt -v
   ```

### Command-Line Options

- `-f, --file`: Path to the input file with IP addresses (required).
- `-o, --output`: Path to save results (optional).
- `-p, --port`: FTP port (default: 21).
- `-v, --verbose`: Show detailed error messages (optional).

### Example Output

**Input File (`ips.txt`)**:
```
192.168.1.1
192.168.1.2
invalid
```

**Command**:
```bash
python Pythonanonymouslogin.py -f ips.txt -o ftp_results.txt
```

**Terminal Output**:
```
Skipping invalid IP: invalid
FTP anonymous login is possible on 192.168.1.1:21
FTP anonymous login is not possible on 192.168.1.2:21
Results saved to ftp_results.txt
```

**Output File (`ftp_results.txt`)**:
```
FTP anonymous login is possible on 192.168.1.1:21
FTP anonymous login is not possible on 192.168.1.2:21
```

## Integration with Other Tools

Combine with `CIDR_2_IP.py` and `nmap_xml_to_excel.py` for a network scanning workflow:

```bash
# Generate IP list
echo "192.168.1.0/24" > ranges.txt
python CIDR_2_IP.py -f ranges.txt -o ips.txt

# Scan for FTP servers
nmap -iL ips.txt -p 21 -sV -oX ftp_scan.xml
python nmap_xml_to_excel.py ftp_scan.xml --output ftp_report.xlsx

# Check anonymous login (use IPs with open port 21)
python Pythonanonymouslogin.py -f ftp_ips.txt -o ftp_results.txt
```

## Debugging

If no results or errors occur:

- **Verify Input File**:
  ```bash
  cat ips.txt
  ```
  Ensure valid IPs (e.g., `192.168.1.1`).

- **Test FTP Connectivity**:
  ```bash
  ftp 192.168.1.1
  ```

- **Check Output File**:
  ```bash
  cat ftp_results.txt
  ```

- **Verbose Mode**:
  ```bash
  python Pythonanonymouslogin.py -f ips.txt -v
  ```

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for bug reports, feature requests, or improvements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Shamya

## Acknowledgments

- Built with Python’s `ftplib`, `argparse`, and `ipaddress` modules.
- Designed for network security professionals.