import datetime
import ipaddress
import logging
import os
import shutil
import time

from dataclasses import dataclass
from config import ARCHIVE_DIR, CHANGES_DIR, FILE_PATH, MAX_ENTRIES

logging.basicConfig(level=logging.INFO)

@dataclass
class IPAddressList():
    ips: str

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
    entries = []
    """Trim the entries in the IP addresses file to maintain a maximum limit based on timestamps."""
    with open(FILE_PATH, 'r') as f:
        entries = [line.strip() for line in f if line.strip()]  # Read existing entries

    # Sort entries by timestamp (the second part after '|')
    entries.sort(key=lambda x: int(x.split('|')[1]))  # Sort by the timestamp

    unique_ips = {}

    for entry in entries:
        ip, timestamp = entry.split('|')
        if ip not in unique_ips:
            unique_ips[ip] = timestamp 
            
    entries = [f"{key}|{value}" for key, value in unique_ips.items()]

    # If there are more than the maximum allowed entries, trim the oldest ones
    while len(entries) > MAX_ENTRIES:
        # Remove the oldest entry (first in the sorted list)
        entries.pop(0)
    
    # Write the trimmed entries back to the file
    with open(FILE_PATH, 'w') as f:
        for entry in entries:
            f.write(entry + "\n")
    
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
        
def check_overlap(file_path):
    with open(file_path, 'r') as f:
        entries = [line.strip() for line in f if line.strip()]  # Read existing entries

    overlaps = {}
    for i, entry in enumerate(entries):
        ip_network = ipaddress.ip_network(entry.split('|')[0], strict=False)
        overlapping_ips = []
        
        for j, other_entry in enumerate(entries):
            if i != j:
                other_ip_network = ipaddress.ip_network(other_entry.split('|')[0], strict=False)
                if ip_network.overlaps(other_ip_network):
                    overlapping_ips.append(other_entry)

        if overlapping_ips:
            overlaps[entry] = overlapping_ips

    if not overlaps:
        return "No overlapping entries found."

    # Format the response
    formatted_response = []
    for ip, overlapped in overlaps.items():
        formatted_response.append(f"{ip} overlaps with: {', '.join(overlapped)}")
    
    return "\n".join(formatted_response)
        
def get_ips(file_path, include_timestamp: bool = False):
    with open(file_path, 'r') as f:
        entries = [line.strip() for line in f if line.strip()]  # Read existing entries
    
    if include_timestamp:
        # Return IPs with timestamps formatted as date
        formatted_entries = []
        for entry in entries:
            ip, timestamp = entry.split('|')
            date_str = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
            formatted_entries.append(f"{ip} | {date_str}")
        return "\n".join(formatted_entries)

    # Extract IP addresses only
    ips = [entry.split('|')[0] for entry in entries]  # Get IP addresses without timestamps
    sorted_ips = sorted(ips, key=lambda ip: (ipaddress.ip_network(ip, strict=False).version, ipaddress.ip_network(ip, strict=False)))
    return "\n".join(sorted_ips)
        
def add_ips(ip_list: IPAddressList):
    # client_ip = request.client.host  # Get client IP
    # archive_file()  # Archive the current file before making changes
    # request_body = await request.body()  # Get the raw request body
    # log_changes(request_body.decode(), "POST", client_ip)  # Log the changes with request type and client IP

    # Normalize and prepare new entries
    new_entries = []
    for ip in ip_list['ips']:
        normalized_ip = normalize_ip(ip)
        timestamp = int(time.time())  # Get current time in seconds since epoch
        new_entries.append(f"{normalized_ip}|{timestamp}")  # Prepare new entry
        
    # Write new entries to the file
    with open(FILE_PATH, 'a') as f:  # Append to the file
        for entry in new_entries:
            f.write(entry + "\n")  # Store IP with Unix timestamp

    # Trim entries to ensure the maximum limit
    trim_entries()

    return f"IPs added {len(new_entries)} successfully"

def delete_ips(ip_list):
    #client_ip = request.client.host  # Get client IP
    #archive_file()  # Archive the current file before making changes
    #request_body = request.body()  # Get the raw request body
    #log_changes(request_body.decode(), "DELETE", client_ip)  # Log the changes with request type and client IP

    with open(FILE_PATH, 'r') as f:
        entries = [line.strip() for line in f if line.strip()]  # Read existing entries

    # Create a set of IPs to remove
    ips_to_remove = {normalize_ip(ip) for ip in ip_list['ips']}

    # Filter out the IPs to remove
    remaining_entries = [entry for entry in entries if entry.split('|')[0] not in ips_to_remove]

    # Write the remaining entries back to the file
    with open(FILE_PATH, 'w') as f:
        for entry in remaining_entries:
            f.write(entry + "\n")

    # Trim entries to ensure the maximum limit after deletion
    trim_entries()

    return f"IPs deleted {len(ips_to_remove)} successfully; IPs in list {len(entries) - len(ips_to_remove)}"
