# CIDR_2_IP

A Python script to extract individual IP addresses from CIDR ranges (e.g., `192.168.1.0/24`) or IP address ranges (e.g., `192.168.1.1-192.168.1.10`) specified in a file. Supports both IPv4 and IPv6, making it ideal for network scanning, IP inventory, or integration with tools like Nmap.

## Features

- **CIDR Support**: Processes IPv4 and IPv6 CIDR notations (e.g., `192.168.1.0/24`, `2001:db8::/32`).
- **IP Range Support**: Handles IP address ranges (e.g., `192.168.1.1-192.168.1.10`).
- **Deduplication**: Removes duplicate IPs for clean output.
- **Output Options**: Prints to stdout or saves to a file using the `--output` flag.
- **Robust Error Handling**: Validates inputs and handles invalid CIDR, IP ranges, or file errors gracefully.
- **No External Dependencies**: Uses only Python’s standard library (`ipaddress`, `argparse`).

## Prerequisites

- Python 3.3 or higher (due to `ipaddress` module availability).

No external packages are required, making the script lightweight and portable.

## Installation

1. Clone the repository or download `CIDR_2_IP.py`:

   ```bash
   git clone https://github.com/sam1101-sys/Mixed-Scripts.git
   cd Mixed-Scripts
   ```

2. Ensure Python 3 is installed:

   ```bash
   python3 --version
   ```

## Usage

1. Create a file containing CIDR ranges or IP ranges, one per line. Example (`ranges.txt`):

   ```
   192.168.1.0/30
   192.168.1.10-192.168.1.12
   2001:db8::/126
   ```

2. Run the script to print IP addresses:

   ```bash
   python CIDR_2_IP.py -f ranges.txt
   ```

3. Save output to a file:

   ```bash
   python CIDR_2_IP.py -f ranges.txt -o ips.txt
   ```

### Command-Line Options

- `-f, --file`: Path to the input file containing CIDR or IP ranges (required).
- `-o, --output`: Path to the output file to save IP addresses (optional).

### Example Output

**Input File (`ranges.txt`)**:
```
192.168.1.0/30
192.168.1.10-192.168.1.12
2001:db8::/126
```

**Command**:
```bash
python CIDR_2_IP.py -f ranges.txt
```

**Output**:
```
192.168.1.0
192.168.1.1
192.168.1.10
192.168.1.11
192.168.1.12
192.168.1.2
192.168.1.3
2001:db8::
2001:db8::1
2001:db8::2
2001:db8::3
```

**Output File (`ips.txt`)**:
```bash
python CIDR_2_IP.py -f ranges.txt -o ips.txt
```
Creates `ips.txt` with the same IPs, one per line.

## Integration with Nmap

Use `CIDR_2_IP.py` to generate IP lists for Nmap scans, then analyze results with tools like `nmap_xml_to_excel.py`:

```bash
python CIDR_2_IP.py -f ranges.txt -o ips.txt
nmap -iL ips.txt -sV -oX scan.xml
python nmap_xml_to_excel.py scan.xml --output report.xlsx
```

## Debugging

If the script produces unexpected results:

- **Verify Input File**: Ensure each line is a valid CIDR (e.g., `192.168.1.0/24`) or IP range (e.g., `192.168.1.1-192.168.1.10`). Invalid lines are reported:

  ```
  Invalid CIDR format in line: 192.168.1.0/33
  Invalid input format in line: invalid
  ```

- **Check File Existence**:
  ```bash
  ls ranges.txt
  ```

- **Test with Simple Input**:
  ```bash
  echo "192.168.1.0/30" > test.txt
  python CIDR_2_IP.py -f test.txt
  ```

- **Python Version**:
  ```bash
  python3 --version
  ```

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for bug reports, feature requests, or improvements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Shamya

## Acknowledgments

- Built with Python’s `ipaddress` and `argparse` modules.
- Designed to complement network scanning workflows with Nmap.
