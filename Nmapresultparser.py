import os
import xml.etree.ElementTree as ET
import csv
import argparse

# Function to parse Nmap results from XML format
def parse_xml(xml_file, csv_writer):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    for host in root.findall('.//host'):
        ip_address = host.find('.//address[@addrtype="ipv4"]').attrib['addr']

        for port in host.findall('.//port'):
            port_num = port.attrib['portid']
            service = port.find('.//service').attrib.get('name', 'Unknown')
            csv_writer.writerow([ip_address, port_num, service])

# Function to parse Nmap results from .nmap or .gnmap format
def parse_nmap_gnmap(nmap_file, csv_writer):
    with open(nmap_file, 'r') as file:
        lines = file.readlines()

    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 4:
            ip_address = parts[1]
            port_info = parts[3].split('/')
            port_num = port_info[0]
            service = port_info[2]
            csv_writer.writerow([ip_address, port_num, service])

def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description="Parse Nmap scan results and consolidate them into a CSV file.")
    
    # Add command-line arguments
    parser.add_argument("input_file", help="Nmap scan result file")
    parser.add_argument("output_csv", help="Output CSV file to store consolidated results")

    # Parse command-line arguments
    args = parser.parse_args()

    # Create a single CSV file to consolidate results
    with open(args.output_csv, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['IP Address', 'Port', 'Service'])

        if args.input_file.endswith('.xml'):
            parse_xml(args.input_file, csv_writer)

        elif args.input_file.endswith('.nmap') or args.input_file.endswith('.gnmap'):
            parse_nmap_gnmap(args.input_file, csv_writer)

    print(f"Parsing completed. Results are saved in '{args.output_csv}'.")

if __name__ == "__main__":
    main()
