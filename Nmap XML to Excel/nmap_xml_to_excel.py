#!/usr/bin/env python3
#
# Script to analyze Nmap XML and generate an Excel file with two sheets:
# 1. Live Hosts: IP and hostname.
# 2. Port Details: IP, port, protocol, service, status, and details.
#
# Usage: python nmap_xml_to_excel.py <nmap_xml_file> [--exclude-ports <ports>] [--output <excel_file>]
# Example: python nmap_xml_to_excel.py scan.xml --exclude-ports 80,443 --output report.xlsx
#

import argparse
import sys
import xml.etree.ElementTree as ET
import pandas as pd

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Convert Nmap XML to Excel with live hosts and port details.")
parser.add_argument("xml_file", help="Path to Nmap XML file")
parser.add_argument("--exclude-ports", help="Comma-separated list of ports to exclude (e.g., 80,443)", default="")
parser.add_argument("--output", help="Output Excel file name", default="nmap_report.xlsx")
args = parser.parse_args()

# Convert excluded ports to a set
exclude_ports = set(args.exclude_ports.split(",")) if args.exclude_ports else set()

# Parse XML file
try:
    tree = ET.parse(args.xml_file)
    root = tree.getroot()
except ET.ParseError as e:
    print(f"Error: Failed to parse XML file: {e}", file=sys.stderr)
    sys.exit(1)
except FileNotFoundError:
    print(f"Error: File '{args.xml_file}' not found", file=sys.stderr)
    sys.exit(1)

# Data structures
live_hosts = []  # List of dicts for live hosts
port_details = []  # List of dicts for port details

# Iterate through each host
for host in root.findall('.//host'):
    # Get IP address
    addr_elem = host.find('address')
    if addr_elem is None or 'addr' not in addr_elem.attrib:
        print(f"Debug: Skipping host with missing address", file=sys.stderr)
        continue
    ipaddress = addr_elem.attrib['addr']

    # Get hostname (PTR)
    hostname = ""
    for hostname_elem in host.findall('.//hostname'):
        if hostname_elem.attrib.get('type') == 'PTR':
            hostname = hostname_elem.attrib.get('name', '')
            break

    # Add to live hosts
    live_hosts.append({"IP Address": ipaddress, "Hostname": hostname})

    # Process ports
    for port_elem in host.findall('.//port'):
        portid = port_elem.attrib.get('portid', '')
        protocol = port_elem.attrib.get('protocol', '')
        if portid in exclude_ports:
            print(f"Debug: Excluding port {portid} for {ipaddress}", file=sys.stderr)
            continue

        # Get port state
        state_elem = port_elem.find('state')
        state = state_elem.attrib.get('state', 'unknown').capitalize() if state_elem is not None else 'Unknown'

        # Get service details
        service_name = ""
        product = ""
        version = ""
        service_elem = port_elem.find('service')
        if service_elem is not None:
            service_name = service_elem.attrib.get('name', '')
            product = service_elem.attrib.get('product', '')
            version = service_elem.attrib.get('version', '')

        # Add to port details
        port_details.append({
            "IP Address": ipaddress,
            "Port": portid,
            "Protocol": protocol,
            "Service": service_name,
            "Product": product,
            "Version": version,
            "Status": state
        })

# Create DataFrames
live_hosts_df = pd.DataFrame(live_hosts)
port_details_df = pd.DataFrame(port_details)

# Handle empty DataFrames
if live_hosts_df.empty:
    print("Warning: No live hosts found in the XML file", file=sys.stderr)
    live_hosts_df = pd.DataFrame(columns=["IP Address", "Hostname"])
if port_details_df.empty:
    print("Warning: No port details found in the XML file (possibly due to port exclusion)", file=sys.stderr)
    port_details_df = pd.DataFrame(columns=[
        "IP Address", "Port", "Protocol", "Service", "Product", "Version", "Status"
    ])

# Write to Excel
try:
    with pd.ExcelWriter(args.output, engine='openpyxl') as writer:
        live_hosts_df.to_excel(writer, sheet_name="Live Hosts", index=False)
        port_details_df.to_excel(writer, sheet_name="Port Details", index=False)
    print(f"Excel file '{args.output}' created successfully")
except Exception as e:
    print(f"Error: Failed to write Excel file: {e}", file=sys.stderr)
    sys.exit(1)
