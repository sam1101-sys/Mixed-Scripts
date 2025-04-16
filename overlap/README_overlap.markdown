# overlap.py

A Python script to find overlapping IP ranges between two files containing CIDR or IP range notations. Helps optimize network scan planning by identifying redundant ranges.

## Features

- **Range Support**: Handles CIDR (e.g., `192.168.1.0/24`) and IP ranges (e.g., `192.168.1.1-192.168.1.10`).
- **IPv4/IPv6**: Processes both address types.
- **Error Handling**: Reports missing files and invalid ranges.
- **Clear Output**: Lists overlapping ranges with file origins or “no overlaps” message.

## Prerequisites

- Python 3.3+ (uses `ipaddress` module).

## Installation

1. Clone the repository or copy `overlap.py`:

   ```bash
   git clone https://github.com/sam1101-sys/Mixed-Scripts.git
   cd Mixed-Scripts/overlap
   ```

2. Verify Python:

   ```bash
   python3 --version
   ```

## Usage

1. Create two files with IP ranges. Example:

   - `file1.txt`:
     ```
     192.168.1.0/30
     ```
   - `file2.txt`:
     ```
     192.168.1.0-192.168.1.5
     ```

2. Run the script:

   ```bash
   python overlap.py -f file1.txt file2.txt
   ```

### Command-Line Options

- `-f, --files`: Two files with IP ranges (required).

### Example Output

**Command**:
```bash
python overlap.py -f file1.txt file2.txt
```

**Output**:
```
Common IP ranges:
file1.txt: 192.168.1.0/30 overlaps with file2.txt: 192.168.1.0/30
```

## Integration

Use before scanning with `Mixed-Scripts` tools:
```bash
python overlap.py -f ranges1.txt ranges2.txt
python CIDR_2_IP.py -f ranges1.txt -o ips.txt
nmap -iL ips.txt -oX scan.xml
python nmap_xml_to_excel.py scan.xml
```

## Debugging

- **Verify Files**:
  ```bash
  cat file1.txt
  ```
- **Test Ranges**:
  ```bash
  echo "192.168.1.0/30" > test.txt
  python overlap.py -f test.txt file2.txt
  ```

## License

MIT License. See [LICENSE](../../LICENSE).

Copyright (c) 2025 Shamya