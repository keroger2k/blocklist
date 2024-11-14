import os

FILE_NAME = os.environ['fileName']
FILE_PATH = os.path.join("/tmp", FILE_NAME)
BUCKET = os.environ['fileBucket']
KEY = os.environ['fileKey']

MAX_ENTRIES = 50000
CHANGES_DIR = "changes" #not used yet.
ARCHIVE_DIR = "archive" #not used yet.

WHITE_LIST = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "165.224.131.248/29",
    "165.224.129.248/29",
    "63.156.199.10/32"
]