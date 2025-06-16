import os

from dotenv import load_dotenv


load_dotenv()

server_list = {
    '103.80.87.125': os.getenv('103.80.87.125'),
    '103.80.86.51': os.getenv('103.80.86.51'),
    '103.80.86.99': os.getenv('103.80.86.99'),
}
