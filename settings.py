import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

bucket_name = os.getenv('BUCKET_NAME')
prefix = os.getenv('PREFIX')
discovery_folder = os.getenv('DATA_DISCOVERY_FOLDER')
discovery_file = os.getenv('DATA_DISCOVERY_FILE')
