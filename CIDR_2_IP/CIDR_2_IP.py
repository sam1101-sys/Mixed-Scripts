#!/usr/bin/env python3
# Copyright (c) 2025 Shamya
# Licensed under the MIT License. See LICENSE file in the repository.

import argparse
import ipaddress

def extract_ips_from_file(file_path):
    ip_set = set()
    try:
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                if '/' in line:  # CIDR notation
                    try:
                        network = ipaddress.ip_network(line, strict=False)
                        for ip in network:
                            ip_set.add(str(ip))
                    except (ipaddress.NetmaskValueError, ipaddress.AddressValueError):
                        print(f"Invalid CIDR format in line: {line}")
                elif '-' in line:  # IP address range
                    try:
                        start_ip, end_ip = line.split('-')
                        start_ip = ipaddress.ip_address(start_ip.strip())
                        end_ip = ipaddress.ip_address(end_ip.strip())
                        if int(start_ip) > int(end_ip):
                            print(f"Invalid range (start > end) in line: {line}")
                            continue
                        for ip in range(int(start_ip), int(end_ip) + 1):
                            ip_set.add(str(ipaddress.ip_address(ip)))
                    except (ValueError, ipaddress.AddressValueError):
                        print(f"Invalid IP range format in line: {line}")
                else:
                    print(f"Invalid input format in line: {line}")
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    return sorted(ip_set)  # Sort for consistent output

# Parse command line arguments
parser = argparse.ArgumentParser(description="Extract IP addresses from CIDR ranges or IP address ranges in a file")
parser.add_argument("-f", "--file", required=True, help="Path to the file containing CIDR ranges or IP address ranges")
parser.add_argument("-o", "--output", help="Output file path")
args = parser.parse_args()

# Extract IP addresses
ip_addresses = extract_ips_from_file(args.file)

# Output results
if ip_addresses:
    if args.output:
        try:
            with open(args.output, 'w') as f:
                for ip in ip_addresses:
                    f.write(f"{ip}\n")
            print(f"IP addresses written to {args.output}")
        except IOError as e:
            print(f"Error writing to output file: {e}")
    else:
        for ip in ip_addresses:
            print(ip)
else:
    print("No valid IP addresses found")
