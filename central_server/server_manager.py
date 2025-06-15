import database
import paramiko
import re
import datetime
import redis

from sqlalchemy import func


r = redis.Redis()


def check_config_availability(speed, payment_id):
    with database.Session() as session:
        servers = session.query(database.Server).all()
        if not servers:
            return False
        for server in servers:
            database.delete_old_orderings(session)
            speed_sum = session.query(func.sum(database.UserTariff.speed)).filter_by(server_id=server.id).scalar() or 0
            server_ordering_speed = session.query(func.sum(database.ServerOrdering.speed)).filter_by(server_id=server.id).scalar() or 0
            if speed_sum + speed + server_ordering_speed <= 650:
                server_ordering = database.ServerOrdering(
                    server_id=server.id,
                    created_at=datetime.datetime.utcnow(),
                    payment_id=payment_id,
                    speed=speed,
                )
                session.add(server_ordering)
                session.commit()
                return server.id
        return False


def get_available_port(server):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server.ip, username='root', password=server.password)
    stdin, stdout, stderr = client.exec_command(
        "python3 -c 'import socket; s = socket.socket(); s.bind((\"\", 0)); print(s.getsockname()[1]); s.close()'"
    )
    stdout = int(stdout.read().decode().strip())
    if stderr.read().decode() != '':
        print(f"Error: {stderr.read().decode()}")
        return None
    client.close()
    return stdout


def get_error_message(stderr):
    error = stderr.read().decode()
    if error != '':
        print(f"Error: {error}")
    return error


def run_vpn_script(server, port, name, speed):
    try:
        if not r.set(f"{server}_lock", 1, ex=3600, nx=True):
            print(f"Server({server}) is busy, please try again later.")
            return None
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server.ip, username='root', password=server.password)
        stdin, stdout, stderr = client.exec_command(f"cd Jester && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python3 create_vpn_user.py {name} {port} {speed}")
        stdout = stdout.read().decode()
        key = re.search(r'vless://(.*)', stdout).group(0)
        get_error_message(stderr)
        client.close()
        if key is None:
            print("Error: No key found in output.")
            return None
        return key
    finally:
        r.delete(f"{server}_lock")


def create_vpn_config(name, speed, server):
    port = get_available_port(server)
    if not port:
        print("Нет доступных портов.")
        return None
    key = run_vpn_script(server, port, name, speed)
    if not key:
        return None
    return key
