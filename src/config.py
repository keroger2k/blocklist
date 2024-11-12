import os

FILE_PATH = "/tmp/" + os.environ['fileName']
BUCKET = os.environ['fileBucket']
KEY = os.environ['fileKey']

MAX_ENTRIES = 50000
CHANGES_DIR = "changes" #not used yet.
ARCHIVE_DIR = "archive" #not used yet.