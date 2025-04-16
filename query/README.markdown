# query.py

A Python script to convert CIDR ranges from a file into a query format (e.g., `asset.ipv4 BETWEEN x AND y`) for use in external systems like network monitoring tools.

## Features

- **Query Generation**: Creates queries for IPv4 and IPv6 CIDRs.
- **Output Options**: Prints to stdout or saves to a file (`--output`).
- **Error Handling**: Reports invalid CIDRs and file errors.
- **Simple Format**: Joins ranges with `||` for easy integration.

## Prerequisites

- Python 3.3+ (uses `ipaddress` module).

## Installation

1. Clone the repository or copy `query.py`:

   ```bash
   git clone https://github.com/sam1101-sys/Mixed-Scripts.git
   cd Mixed-Scripts/query
   ```

2. Verify Python:

   ```bash
   python3 --version
   ```

## Usage

1. Create a file with CIDR ranges. Example (`cidrs.txt`):

   ```
   192.168.1.0/30
   2001:db8::/126
   ```

2. Run the script:

   ```bash
   python query.py -f cidrs.txt
   ```

3. Save to a file:

   ```bash
   python query.py -f cidrs.txt -o query.txt
   ```

### Command-Line Options

- `-f, --file`: File with CIDR ranges (required).
- `-o, --output`: Output file for query (optional).

### Example Output

**Command**:
```bash
python query.py -f cidrs.txt
```

**Output**:
```
Generated Query:
asset.ipv4 BETWEEN 192.168.1.0 AND 192.168.1.3 || asset.ipv6 BETWEEN 2001:db8:: AND 2001:db8::3
```

## Integration

Use with `Mixed-Scripts`:
```bash
python query.py -f ranges.txt -o query.txt
python CIDR_2_IP.py -f ranges.txt -o ips.txt
nmap -iL ips.txt -oX scan.xml
python nmap_xml_to_excel.py scan.xml
```

## Debugging

- **Verify File**:
  ```bash
  cat cidrs.txt
  ```
- **Test CIDR**:
  ```bash
  echo "192.168.1.0/30" > test.txt
  python query.py -f test.txt
  ```

## License

MIT License. See [LICENSE](../../LICENSE).

Copyright (c) 2025 Shamya
