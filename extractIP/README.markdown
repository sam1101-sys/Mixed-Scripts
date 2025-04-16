# extractIP.py

A Python script to extract individual host IP addresses from CIDR ranges in multiple files, excluding network and broadcast addresses. Ideal for generating target lists for network scans.

## Features

- **CIDR Parsing**: Processes IPv4 and IPv6 CIDR ranges (e.g., `192.168.1.0/30`, `2001:db8::/126`).
- **Deduplication**: Removes duplicate IPs.
- **Multiple Files**: Handles multiple input files.
- **Output Options**: Prints to stdout or saves to a file (`--output`).
- **Error Handling**: Reports invalid CIDRs and file errors.

## Prerequisites

- Python 3.3+ (uses `ipaddress` module).

## Installation

1. Clone the repository or copy `extractIP.py`:

   ```bash
   git clone https://github.com/sam1101-sys/Mixed-Scripts.git
   cd Mixed-Scripts/extractIP
   ```

2. Verify Python:

   ```bash
   python3 --version
   ```

## Usage

1. Create files with CIDR ranges. Example (`ranges.txt`):

   ```
   192.168.1.0/30
   2001:db8::/126
   ```

2. Run the script:

   ```bash
   python extractIP.py -f ranges.txt
   ```

3. Save to a file:

   ```bash
   python extractIP.py -f ranges.txt -o hosts.txt
   ```

### Command-Line Options

- `-f, --files`: Files with CIDR ranges (required, multiple allowed).
- `-o, --output`: Output file for IPs (optional).

### Example Output

**Input (`ranges.txt`)**:
```
192.168.1.0/30
```

**Command**:
```bash
python extractIP.py -f ranges.txt
```

**Output**:
```
Extracted IPs:
192.168.1.1
192.168.1.2
```

## Integration

Use with other `Mixed-Scripts` tools:
```bash
python extractIP.py -f ranges.txt -o hosts.txt
./nfs_automater.sh hosts.txt
python Pythonanonymouslogin.py -f hosts.txt
```

## Debugging

- **Verify Input**:
  ```bash
  cat ranges.txt
  ```
- **Test CIDR**:
  ```bash
  echo "192.168.1.0/30" > test.txt
  python extractIP.py -f test.txt
  ```

## License

MIT License. See [LICENSE](../../LICENSE).

Copyright (c) 2025 Shamya
