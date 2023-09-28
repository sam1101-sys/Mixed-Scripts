import argparse
import ipaddress
import re

# Function to extract IP addresses from CIDR ranges or IP address ranges
def extract_ips_from_file(file_path):
    ip_list = []
    try:
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if '/' in line:  # Check if it's a CIDR notation
                    network = ipaddress.IPv4Network(line, strict=False)
                    for ip in network:
                        ip_list.append(str(ip))
                elif '-' in line:  # Check if it's an IP address range
                    start_ip, end_ip = line.split('-')
                    start_ip = ipaddress.IPv4Address(start_ip.strip())
                    end_ip = ipaddress.IPv4Address(end_ip.strip())
                    for ip in range(int(start_ip), int(end_ip) + 1):
                        ip_list.append(str(ipaddress.IPv4Address(ip)))
                else:
                    print(f"Invalid input format in line: {line}")
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    
    return ip_list

# Parse command line arguments
parser = argparse.ArgumentParser(description="Extract IP addresses from CIDR ranges or IP address ranges in a file")
parser.add_argument("-f", "--file", required=True, help="Path to the file containing CIDR ranges or IP address ranges")

args = parser.parse_args()

# Extract IP addresses from the specified file
ip_addresses = extract_ips_from_file(args.file)

# Print the list of IP addresses
for ip in ip_addresses:
    print(ip)
