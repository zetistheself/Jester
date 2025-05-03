import paramiko


def get_free_port():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("linkedmail.ru", username='root', password="1TYp68p5y")
    stdin, stdout, stderr = client.exec_command("comm -23 <(seq 1024 65535 | sort) <(ss -tuln | awk '{print $5}' | grep -oE '[0-9]+$' | sort -n | uniq) | head -n 1")
    if stderr.read().decode() != '':
        print(f"Error: {stderr.read().decode()}")
        return None
    return int(stdout.read().strip())


print(get_free_port())
