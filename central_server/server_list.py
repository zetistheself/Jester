import os

from dotenv import load_dotenv


load_dotenv()

server_list = {
    '103.80.87.125': os.getenv('103.80.87.125'),
}
