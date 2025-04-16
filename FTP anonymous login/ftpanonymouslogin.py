#!/usr/bin/env python3
# Copyright (c) 2025 Shamya
# Licensed under the MIT License. See LICENSE file in the repository.

import ftplib
import argparse
import ipaddress

def check_ftp_anonymous_login(ip, port=21, verbose=False):
    try:
        ftp = ftplib.FTP()
        ftp.connect(ip, port=port, timeout=5)
        ftp.login('anonymous', 'anonymous')
        ftp.quit()
        return True
    except ftplib.all_errors as e:
        if verbose:
            print(f'Error on {ip}:{port}: {e}')
        return False
    except Exception as e:
        if verbose:
            print(f'Unexpected error on {ip}:{port}: {e}')
        return False

def main():
    parser = argparse.ArgumentParser(description='Check FTP anonymous logins for a list of IP addresses.')
    parser.add_argument('-f', '--file', required=True, help='File containing a list of IP addresses, one per line.')
    parser.add_argument('-o', '--output', help='Output file to save results')
    parser.add_argument('-p', '--port', type=int, default=21, help='FTP port (default: 21)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed error messages')

    args = parser.parse_args()

    try:
        with open(args.file, 'r') as file:
            ip_list = [line.strip() for line in file if line.strip()]

        results = []
        for ip in ip_list:
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                print(f"Skipping invalid IP: {ip}")
                continue
            result = check_ftp_anonymous_login(ip, port=args.port, verbose=args.verbose)
            message = f'FTP anonymous login {"possible" if result else "not possible"} on {ip}:{args.port}'
            print(message)
            results.append(message)

        if args.output:
            with open(args.output, 'w') as f:
                for message in results:
                    f.write(f'{message}\n')
            print(f"Results saved to {args.output}")

    except FileNotFoundError:
        print(f"Error: File '{args.file}' not found.")
    except IOError as e:
        print(f"Error: Failed to write to output file: {e}")

if __name__ == "__main__":
    main()
