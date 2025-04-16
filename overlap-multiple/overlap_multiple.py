#!/usr/bin/env python3
# Copyright (c) 2025 Shamya
# Licensed under the MIT License. See LICENSE file in the repository.

import ipaddress
import argparse

def parse_range(ip_range):
    """Convert IP range to a list of CIDR blocks."""
    try:
        if '-' in ip_range:
            start_ip, end_ip = ip_range.split('-')
            return list(ipaddress.summarize_address_range(
                ipaddress.ip_address(start_ip.strip()),
                ipaddress.ip_address(end_ip.strip())
            ))
        return [ipaddress.ip_network(ip_range, strict=False)]
    except ValueError as e:
        print(f"Invalid range: {ip_range} ({e})")
        return []

def get_common_ranges(files):
    """Find overlapping IP ranges across multiple files."""
    cidrs = []
    for file in files:
        try:
            with open(file, 'r') as f:
                ranges = [line.strip() for line in f if line.strip()]
            cidrs.extend((cidr, file) for r in ranges for cidr in parse_range(r))
        except FileNotFoundError:
            print(f"File not found: {file}")
            continue

    common = []
    for i in range(len(cidrs)):
        for j in range(i + 1, len(cidrs)):
            cidr1, file1 = cidrs[i]
            cidr2, file2 = cidrs[j]
            if cidr1.overlaps(cidr2):
                common.append((file1, cidr1, file2, cidr2))
    
    return common

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare IP ranges across multiple files and find overlaps.")
    parser.add_argument('-f', '--files', nargs='+', required=True, help="File paths to compare (at least 2 required)")
    args = parser.parse_args()

    if len(args.files) < 2:
        print("Please provide at least two files to compare.")
    else:
        common_ranges = get_common_ranges(args.files)
        
        print("Common IP ranges:")
        if common_ranges:
            for file1, cidr1, file2, cidr2 in common_ranges:
                print(f"{file1}: {cidr1} overlaps with {file2}: {cidr2}")
        else:
            print("No overlapping IP ranges found.")
