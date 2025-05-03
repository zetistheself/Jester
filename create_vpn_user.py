import subprocess
import re
import json
import uuid
import secrets
import os
import public_ip
import sys


def generate_keys() -> list[str]:
    result = subprocess.run([
        "docker", "run", "--rm", "teddysun/xray", "xray", "x25519"
    ], text=True, stdout=subprocess.PIPE)
    keys = re.findall(r'\S{43}', result.stdout)
    return keys[0], keys[1]


def get_public_ipv4() -> str:
    try:
        ip = public_ip.get()
    except Exception as e:
        print(f"Error getting public IP: {e}")
        return None
    return ip


def generate_vless_uri(id: str, ip: str, port: int, short_id: str, public_key: str):
    return f"vless://{id}@{ip}:{port}?type=tcp&encryption=none&flow=xtls-rprx-vision&security=reality&sni=www.cloudflare.com&fp=chrome&pbk={public_key}&sid={short_id}#%D0%A8%D1%83%D1%82%20VPN"


def generate_config(private_key: str, id: str, short_id: str):
    return {
        "log": {
            "loglevel": "debug"
        },
        "inbounds": [
            {
                "port": 443,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": id,
                            "flow": "xtls-rprx-vision"
                        }
                    ],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "show": False,
                        "dest": "www.cloudflare.com:443",
                        "xver": 0,
                        "serverNames": [
                            "www.cloudflare.com"
                        ],
                        "privateKey": private_key,
                        "shortIds": [
                            short_id
                        ]
                    }
                }
            }
        ],
        "outbounds": [
            {
                "protocol": "freedom"
            }
        ]
    }


def save_config(config: dict):
    with open("xray-config.json", "w") as f:
        json.dump(config, f)


def run_container(name: str, port: int, rate: int):
    pwd = os.getcwd()
    subprocess.run(['docker', 'build', '-t', f'xray-{name}', "--build-arg", f"TRANSFER_RATE={rate}", '-f', 'Dockerfile', '.'])
    subprocess.run(["docker", "run", "-d", "--name", f"xray-{name}",
                    "-v", f"{pwd}/xray-config.json:/etc/xray/config.json", 
                    "-p", f"{port}:443",
                    "--restart=always",
                    "--device", "/dev/net/tun",
                    "--cap-add=NET_ADMIN",
                    f"xray-{name}"])


def main():
    private_key, public_key = generate_keys()
    id = str(uuid.uuid4())
    short_id = secrets.token_hex(4)
    save_config(generate_config(private_key, id, short_id))
    if len(sys.argv) != 4:
        print("Usage: python3 create_vpn_user.py <name> <port> <speed>")
        sys.exit(1)
    name = sys.argv[1]
    port = sys.argv[2]
    transfer_rate = sys.argv[3] + "mbit"
    run_container(name, port, transfer_rate)
    print(generate_vless_uri(id, get_public_ipv4(), port, short_id, public_key))


if __name__ == "__main__":
    main()