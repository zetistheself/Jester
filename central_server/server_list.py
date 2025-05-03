import os

from dotenv import load_dotenv


load_dotenv()

server_list = {
    'linkedmail.ru': os.getenv('linkedmail.ru'),
}
