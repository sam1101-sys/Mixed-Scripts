# Nmap XML to Excel

A Python script to parse Nmap XML scan results and generate an Excel file with two sheets: one for live hosts and another for detailed port information. This tool simplifies network scan analysis by converting complex Nmap XML output into organized, tabular data.

## Features

- **Live Hosts Sheet**: Lists all live hosts with their IP addresses and hostnames (PTR records).
- **Port Details Sheet**: Provides detailed information including IP, port, protocol, service, product, version, and port status (open, closed, filtered, etc.).
- **Port Exclusion**: Optionally exclude specific ports (e.g., 80, 443) from the output using the `--exclude-ports` flag.
- **Error Handling**: Robustly handles invalid XML, missing files, and incomplete data with clear error messages.
- **Customizable Output**: Specify the output Excel file name using the `--output` flag.
- **Debug Support**: Prints debug messages to help diagnose issues with XML parsing or data filtering.

## Prerequisites

- Python 3.6 or higher
- Required Python packages:
  - `pandas`
  - `openpyxl`

Install dependencies using pip:

```bash
pip install pandas openpyxl
```

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/nmap-xml-to-excel.git
   cd nmap-xml-to-excel
   ```

2. Ensure dependencies are installed (see Prerequisites).

## Usage

1. Generate an Nmap XML scan file (e.g., with service detection for richer data):

   ```bash
   nmap -sV -oX scan.xml 192.168.1.0/24
   ```

2. Run the script to process the XML and generate an Excel file:

   ```bash
   python nmap_xml_to_excel.py scan.xml
   ```

3. Customize the output file name or exclude specific ports:

   ```bash
   python nmap_xml_to_excel.py scan.xml --exclude-ports 80,443 --output report.xlsx
   ```

### Command-Line Options

- `xml_file`: Path to the Nmap XML file (required).
- `--exclude-ports`: Comma-separated list of ports to exclude (e.g., `80,443`). Default: none.
- `--output`: Output Excel file name. Default: `nmap_report.xlsx`.

### Example Output

The script generates an Excel file (`nmap_report.xlsx`) with two sheets:

**Live Hosts** (Sheet 1):

| IP Address | Hostname |
| --- | --- |
| 192.168.1.1 | router.example.com |
| 192.168.1.2 |  |

**Port Details** (Sheet 2):

| IP Address | Port | Protocol | Service | Product | Version | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 192.168.1.1 | 22 | tcp | ssh | OpenSSH | 7.9p1 | Open |
| 192.168.1.1 | 23 | tcp | telnet |  |  | Closed |
| 192.168.1.2 | 443 | tcp | https | Apache httpd | 2.4.41 | Open |

## Debugging

If the script produces no output or encounters errors:

- **Verify XML**: Ensure the XML file contains hosts and ports:

  ```bash
  grep '<port ' scan.xml | grep 'state="open"'
  ```

- **Check Debug Messages**: Look for `Debug:` or `Warning:` messages printed to the terminal.

- **Validate XML**: Confirm the XML is well-formed:

  ```bash
  xmllint --noout scan.xml
  ```

- **Test Without Exclusion**: Run without `--exclude-ports` to rule out over-filtering.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for bug reports, feature requests, or improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 Shamya

## Acknowledgments

- Built with Python, `xml.etree.ElementTree`, `pandas`, and `openpyxl`.
- Inspired by the need to simplify Nmap scan analysis for network administrators.
