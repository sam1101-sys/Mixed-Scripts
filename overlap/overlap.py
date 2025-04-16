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

def get_common_ranges(file1, file2):
    """Find overlapping IP ranges between two files."""
    ranges1 = []
    ranges2 = []
    try:
        with open(file1, 'r') as f1:
            ranges1 = [line.strip() for line in f1 if line.strip()]
    except FileNotFoundError:
        print(f"File not found: {file1}")
        return []
    try:
        with open(file2, 'r') as f2:
            ranges2 = [line.strip() for line in f2 if line.strip()]
    except FileNotFoundError:
        print(f"File not found: {file2}")
        return []

    cidrs1 = [(cidr, file1) for r in ranges1 for cidr in parse_range(r)]
    cidrs2 = [(cidr, file2) for r in ranges2 for cidr in parse_range(r)]

    common = []
    for cidr1, file1_name in cidrs1:
        for cidr2, file2_name in cidrs2:
            if cidr1.overlaps(cidr2):
                common.append((file1_name, cidr1, file2_name, cidr2))
    
    return common

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare IP ranges from two files and find overlaps.")
    parser.add_argument('-f', '--files', nargs=2, required=True, help="Two file paths to compare")
    args = parser.parse_args()

    file1, file2 = args.files
    common_ranges = get_common_ranges(file1, file2)
    
    print("Common IP ranges:")
    if common_ranges:
        for file1_name, cidr1, file2_name, cidr2 in common_ranges:
            print(f"{file1_name}: {cidr1} overlaps with {file2_name}: {cidr2}")
    else:
        print("No overlapping IP ranges found.")
