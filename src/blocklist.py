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
from config import ARCHIVE_DIR, CHANGES_DIR, FILE_PATH, MAX_ENTRIES, BUCKET, KEY, FILE_NAME

logging.basicConfig(level=logging.INFO,force=True)
s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3') 

def archive_file():
    """Archive the current IP address file with a timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archived_file_path = os.path.join(ARCHIVE_DIR, f"ip_addresses_{timestamp}.txt")
    shutil.copy(FILE_PATH, archived_file_path)
       
def log_changes(request_body: str, request_type: str, client_ip: str):
    """Log changes to a timestamped file, including the request type and client IP."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    changes_file_path = os.path.join(CHANGES_DIR, f"changes_{timestamp}.txt")
    with open(changes_file_path, 'w') as f:
        f.write(f"Request Type: {request_type}\n")
        f.write(f"Client IP: {client_ip}\n")
        f.write(request_body)

def trim_entries():
    entries = {}
    """Trim the entries in the IP addresses file to maintain a maximum limit based on timestamps."""
    with open(FILE_PATH, 'r+') as f:
        entries = json.load(f)
        
    sorted_dict = dict(sorted(entries.items(), key=lambda item: item[1]))
    trimmed_dict = dict(list(sorted_dict.items())[-MAX_ENTRIES:])
    
    write_file_to_s3(trimmed_dict)
    
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
        
def get_ips(include_timestamp: bool = False):
    entries = {}
    with open(FILE_PATH, 'r') as f:
         entries = json.load(f)
    
    if include_timestamp:
        # Return IPs with timestamps formatted as date
        formatted_entries = []
        for entry in entries.keys():
            date_str = datetime.fromtimestamp(int(entries[entry])).strftime('%Y-%m-%d %H:%M:%S')
            formatted_entries.append(f"{entry} | {date_str}")
        return "\n".join(formatted_entries)

    # Extract IP addresses only
    sorted_ips = sorted(entries.keys(), key=lambda ip: (ipaddress.ip_network(ip, strict=False).version, ipaddress.ip_network(ip, strict=False)))
    return "\n".join(sorted_ips)
        
def add_ips(ip_list: set):
    # client_ip = request.client.host  # Get client IP
    # archive_file()  # Archive the current file before making changes
    # request_body = await request.body()  # Get the raw request body
    # log_changes(request_body.decode(), "POST", client_ip)  # Log the changes with request type and client IP

    # Normalize and prepare new entries
    new_entries = {}
    for ip in ip_list:
        normalized_ip = normalize_ip(ip)
        timestamp = int(time.time())  # Get current time in seconds since epoch
        new_entries[normalized_ip] = timestamp

    # Write new entries to the file
    # Append to the file and Store IP with Unix timestamp
    write_file_to_s3(new_entries)

    # Trim entries to ensure the maximum limit
    trim_entries()

    return "IPs added successfully"

def delete_ips(ip_list):
    #client_ip = request.client.host  # Get client IP
    #archive_file()  # Archive the current file before making changes
    #request_body = request.body()  # Get the raw request body
    #log_changes(request_body.decode(), "DELETE", client_ip)  # Log the changes with request type and client IP
    entries = {}

    with open(FILE_PATH, 'r+') as f:
        entries = json.load(f)

        # Create a set of IPs to remove
        ips_to_remove = {normalize_ip(ip) for ip in ip_list}

        for key in ips_to_remove:
            try:
                del entries[key]
            except KeyError as e:
                logging.info(f"Unknown Key: {e}")
        
        f.seek(0)
        json.dump(entries, f, indent=4)
        f.truncate()
        
    s3_resource.Bucket(BUCKET).upload_file(FILE_PATH,KEY)

    return "IPs deleted successfully"

def write_file_to_s3(entries: dict):
    # Write entries to file
    with open(FILE_PATH, 'r+') as f:
        original_file = json.load(f)
        for key in entries.keys():
            original_file[key] = entries[key]
        f.seek(0)
        json.dump(original_file, f, indent=4)
        f.truncate()
        
        
    # Post file to S3
    s3_resource.Bucket(BUCKET).upload_file(FILE_PATH,KEY)