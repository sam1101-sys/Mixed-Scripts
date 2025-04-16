# overlap_multiple.py

A Python script to find overlapping IP ranges across multiple files containing CIDR or IP range notations. Extends `overlap.py` for broader network range analysis.

## Features

- **Multi-File Support**: Compares 2+ files.
- **Range Support**: Handles CIDR and IP ranges for IPv4/IPv6.
- **Error Handling**: Skips missing files and invalid ranges.
- **Clear Output**: Lists overlaps or “no overlaps” message.

## Prerequisites

- Python 3.3+ (uses `ipaddress` module).

## Installation

1. Clone the repository or copy `overlap_multiple.py`:

   ```bash
   git clone https://github.com/sam1101-sys/Mixed-Scripts.git
   cd Mixed-Scripts/overlap_multiple
   ```

2. Verify Python:

   ```bash
   python3 --version
   ```

## Usage

1. Create files with IP ranges. Example:

   - `file1.txt`:
     ```
     192.168.1.0/30
     ```
   - `file2.txt`:
     ```
     192.168.1.0-192.168.1.5
     ```
   - `file3.txt`:
     ```
     192.168.2.0/24
     ```

2. Run the script:

   ```bash
   python overlap_multiple.py -f file1.txt file2.txt file3.txt
   ```

### Command-Line Options

- `-f, --files`: Files with IP ranges (at least 2 required).

### Example Output

**Command**:
```bash
python overlap_multiple.py -f file1.txt file2.txt file3.txt
```

**Output**:
```
Common IP ranges:
file1.txt: 192.168.1.0/30 overlaps with file2.txt: 192.168.1.0/30
```

## Integration

Use to optimize ranges:
```bash
python overlap_multiple.py -f ranges1.txt ranges2.txt ranges3.txt
python extractIP.py -f ranges1.txt -o hosts.txt
nmap -iL hosts.txt -oX scan.xml
python nmap_xml_to_excel.py scan.xml
```

## Debugging

- **Verify Files**:
  ```bash
  cat file1.txt
  ```
- **Test Ranges**:
  ```bash
  python overlap_multiple.py -f file1.txt file2.txt
  ```

## License

MIT License. See [LICENSE](../../LICENSE).

Copyright (c) 2025 Shamya