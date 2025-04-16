import ftplib
import argparse

def check_ftp_anonymous_login(ip):
    try:
        ftp = ftplib.FTP(ip)
        ftp.login('anonymous', 'anonymous')
        ftp.quit()
        return True
    except ftplib.all_errors:
        return False

def main():
    parser = argparse.ArgumentParser(description='Check FTP anonymous logins for a list of IP addresses.')
    parser.add_argument('-f', '--file', required=True, help='File containing a list of IP addresses, one per line.')

    args = parser.parse_args()

    try:
        with open(args.file, 'r') as file:
            ip_list = [line.strip() for line in file]

        for ip in ip_list:
            if check_ftp_anonymous_login(ip):
                print(f'FTP anonymous login is possible on {ip}')
            else:
                print(f'FTP anonymous login is not possible on {ip}')
    except FileNotFoundError:
        print(f"Error: File '{args.file}' not found.")

if __name__ == "__main__":
    main()
