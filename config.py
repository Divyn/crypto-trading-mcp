import os
from dotenv import load_dotenv

load_dotenv()

BITQUERY_TOKEN = os.getenv("BITQUERY_TOKEN", "")
