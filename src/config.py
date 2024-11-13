import os

FILE_NAME = os.environ['fileName']
FILE_PATH = os.path.join("/tmp", FILE_NAME)
BUCKET = os.environ['fileBucket']
KEY = os.environ['fileKey']

MAX_ENTRIES = 50000
CHANGES_DIR = "changes" #not used yet.
ARCHIVE_DIR = "archive" #not used yet.