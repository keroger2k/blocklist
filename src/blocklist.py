import datetime
import ipaddress
import json
import logging
import os
import shutil
import time
import boto3

from datetime import datetime
from dataclasses import dataclass
from config import ARCHIVE_DIR, CHANGES_DIR, FILE_PATH, MAX_ENTRIES, BUCKET, KEY, FILE_NAME, WHITE_LIST

# Create S3 client and resource
s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3') 

# def archive_file():
#     """Archive the current IP address file with a timestamp."""
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     archived_file_path = os.path.join(ARCHIVE_DIR, f"ip_addresses_{timestamp}.txt")
#     shutil.copy(FILE_PATH, archived_file_path)
#     logging.info(f"File archived at: {archived_file_path}")

# def log_changes(request_body: str, request_type: str, client_ip: str):
#     """Log changes to a timestamped file, including the request type and client IP."""
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     changes_file_path = os.path.join(CHANGES_DIR, f"changes_{timestamp}.txt")
    
#     try:
#         with open(changes_file_path, 'w') as f:
#             f.write(f"Request Type: {request_type}\n")
#             f.write(f"Client IP: {client_ip}\n")
#             f.write(request_body)
#         logging.info(f"Changes logged in {changes_file_path}")
#     except Exception as e:
#         logging.error(f"Error logging changes: {e}")

# def check_overlap(file_path):
#     with open(file_path, 'r') as f:
#         entries = [line.strip() for line in f if line.strip()]  # Read existing entries

#     overlaps = {}
#     for i, entry in enumerate(entries):
#         ip_network = ipaddress.ip_network(entry.split('|')[0], strict=False)
#         overlapping_ips = []
        
#         for j, other_entry in enumerate(entries):
#             if i != j:
#                 other_ip_network = ipaddress.ip_network(other_entry.split('|')[0], strict=False)
#                 if ip_network.overlaps(other_ip_network):
#                     overlapping_ips.append(other_entry)

#         if overlapping_ips:
#             overlaps[entry] = overlapping_ips

#     if not overlaps:
#         return "No overlapping entries found."

#     # Format the response
#     formatted_response = []
#     for ip, overlapped in overlaps.items():
#         formatted_response.append(f"{ip} overlaps with: {', '.join(overlapped)}")
    
#     return "\n".join(formatted_response)

def is_ip_in_white_list(ip):
    try:
        ip_obj = ipaddress.ip_network(ip)
        
        for network in WHITE_LIST:
            network_obj = ipaddress.ip_network(network, strict=False)  # Create network object
            if network_obj.overlaps(ip_obj):
                return True  # IP is in one of the white list networks
        return False  # IP is not in any of the white list networks
    
    except ValueError as e:
        print(f"Invalid IP address format: {ip}")
        return False

def load_entries():
    """Load and return the JSON data from the IP file."""
    try:
        with open(FILE_PATH, 'r') as f:
            entries = json.load(f)
        return entries
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Error loading IP entries from {FILE_PATH}: {e}")
        return {}

def save_entries(entries: dict):
    """Save the updated entries to the file and upload to S3."""
    try:
        with open(FILE_PATH, 'w') as f:
            json.dump(entries, f, indent=4)
            
        print(f"INFO::Saving with ({len(entries)}) entries")
        s3_resource.Bucket(BUCKET).upload_file(FILE_PATH, KEY)
        logging.info(f"Entries saved and uploaded to S3: {FILE_PATH}")
    except (IOError, boto3.exceptions.S3UploadFailedError) as e:
        logging.error(f"Error saving entries or uploading to S3: {e}")

def trim_entries(entries: dict):
    """Trim the entries to keep only the latest MAX_ENTRIES."""
    sorted_entries = dict(sorted(entries.items(), key=lambda item: item[1]))
    trimmed_entries = dict(list(sorted_entries.items())[-MAX_ENTRIES:])
    save_entries(trimmed_entries)

def normalize_ip(ip: str) -> str:
    """Normalize the IP address to ensure it has a subnet mask."""
    try:
        ip_obj = ipaddress.ip_network(ip, strict=False)
        return str(ip_obj)  # Already has a subnet
    except ValueError:
        if ':' in ip:  # It's an IPv6 address
            return str(ipaddress.ip_address(ip) / 128)
        else:  # It's an IPv4 address
            return str(ipaddress.ip_address(ip) / 32)

def get_ips(include_timestamp: bool = False):
    """Retrieve and return the IPs from the file, optionally with timestamp."""
    entries = load_entries()
    
    if include_timestamp:
        # Return IPs with timestamps formatted as date
        formatted_entries = [f"{ip} | {datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')}"
                             for ip, timestamp in entries.items()]
        return "\n".join(formatted_entries)
    
    sorted_ips = sorted(entries.keys(), key=lambda ip: (ipaddress.ip_network(ip, strict=False).version, ip))
    print(f"INFO::Getting ({len(entries)}) entries")

    return "\n".join(sorted_ips)

def add_ips(ip_list: set):
    """Add new IPs to the file."""
    entries = load_entries()
    timestamp = int(time.time())  # Get current time in seconds since epoch
    print(f"INFO::Adding {len(ip_list)} to list of ({len(entries)}) entries")

    for ip in ip_list:
        if not is_ip_in_white_list(ip):
            normalized_ip = normalize_ip(ip)
            entries[normalized_ip] = timestamp
        else:
            print(f"{ip} found in a whitelist")
        

    trim_entries(entries) #calls save_entries()
    return "succcess"

def delete_ips(ip_list):
    """Delete specified IPs from the file."""
    entries = load_entries()
    ips_to_remove = {normalize_ip(ip) for ip in ip_list}
    print(f"INFO::Removing {len(ips_to_remove)} to list of ({len(entries)}) entries")

    # Remove the IPs that exist in the entries
    for ip in ips_to_remove:
        if ip in entries:
            del entries[ip]
        else:
            logging.info(f"IP {ip} not found in entries.")

    save_entries(entries)
    return "succcess"
