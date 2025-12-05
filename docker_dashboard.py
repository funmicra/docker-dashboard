#!/usr/bin/env python3
import os
import time
import docker
import paramiko
from tabulate import tabulate
from dotenv import load_dotenv
import shutil
import threading
import signal

docker_rows = []
rows_lock = threading.Lock()
terminal_width, terminal_height = shutil.get_terminal_size()

# Load env
load_dotenv()
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", 30))
ACTIVE_HOSTNAME = os.getenv("ACTIVE_HOSTNAME", None)
SSH_MODE = os.getenv("SSH", "OFF").upper()
SSH_HOST = os.getenv("SSH_HOST", "localhost")
SSH_USER = os.getenv("SSH_USER", "funmicra")
SSH_KEY = os.path.expanduser(os.getenv("SSH_KEY", "~/.ssh/id_rsa"))
SSH_PORT = int(os.getenv("SSH_PORT", 22))

# Update terminal size on resize
def handle_resize(signum, frame):
    global terminal_width, terminal_height
    terminal_width, terminal_height = shutil.get_terminal_size()

signal.signal(signal.SIGWINCH, handle_resize)

# Helpers
def print_banner(text):
    BLUE_BG = "\033[44m"
    RESET = "\033[0m"
    print(f"{BLUE_BG}{text.center(terminal_width)}{RESET}")

def print_divider():
    BLUE_BG = "\033[44m"
    RESET = "\033[0m"
    print(f"{BLUE_BG}{'=' * terminal_width}{RESET}")

def calc_cpu(stats):
    try:
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        percpu = len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
        return (cpu_delta / system_delta) * percpu * 100.0 if system_delta > 0 else 0.0
    except:
        return 0.0

def color_status(text):
    text_lower = text.lower()
    if "running" in text_lower:
        return f"\033[32m{text}\033[0m"
    elif "exited" in text_lower or "stopped" in text_lower:
        return f"\033[31m{text}\033[0m"
    else:
        return f"\033[33m{text}\033[0m"

def color_status_table(table_str):
    """Color the Status column while preserving alignment."""
    lines = table_str.splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("+") or line.startswith("| Name") or line.strip() == "":
            new_lines.append(line)
            continue
        parts = line.split("|")
        if len(parts) >= 4:
            parts[3] = f" {color_status(parts[3].strip())} "
        new_lines.append("|".join(parts))
    return "\n".join(new_lines)

# Local Docker
def docker_list_local():
    try:
        client = docker.from_env()
        rows = []
        for c in client.containers.list(all=True):
            try:
                stats = c.stats(stream=False)
                cpu = calc_cpu(stats)
                mem = stats["memory_stats"]["usage"] / (1024**2)
            except:
                cpu, mem = 0.0, 0.0
            rows.append([c.name, c.image.tags[0] if c.image.tags else "<none>", c.status, f"{cpu:.1f}%", f"{mem:.1f} MB", "local"])
        return rows
    except Exception as e:
        print(f"[!] Local Docker error: {e}")
        return []

# Remote Docker
def run_remote(cmd):
    try:
        key = paramiko.RSAKey.from_private_key_file(SSH_KEY)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(SSH_HOST, username=SSH_USER, pkey=key, port=SSH_PORT, timeout=10)
        stdin, stdout, stderr = client.exec_command(cmd)
        data = stdout.read().decode().strip()
        client.close()
        return data
    except Exception as e:
        print(f"[!] SSH error: {e}")
        return ""

def get_remote_hostname():
    return run_remote("hostname").strip()

def docker_list_remote():
    global ACTIVE_HOSTNAME
    if SSH_MODE != "ON":
        return []

    if ACTIVE_HOSTNAME is None:
        ACTIVE_HOSTNAME = get_remote_hostname() or SSH_HOST

    raw_stats = run_remote('docker stats --no-stream --format "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}"')
    raw_ps = run_remote('docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}"')
    if not raw_ps:
        return []

    stats_dict = {}
    if raw_stats:
        for line in raw_stats.splitlines():
            parts = line.split("|")
            if len(parts) >= 3:
                name, cpu, mem = parts
                stats_dict[name] = (cpu, mem.split("/")[0])

    rows = []
    for line in raw_ps.splitlines():
        parts = line.split("|")
        if len(parts) >= 3:
            name, image, status = parts
            cpu, mem = stats_dict.get(name, ("-", "-"))
            rows.append([name, image, status, cpu, mem, ACTIVE_HOSTNAME])
    return rows

# Background updater
def update_docker_stats():
    global docker_rows
    while True:
        rows = []
        if SSH_MODE == "ON":
            rows += docker_list_remote()
        rows += docker_list_local()
        with rows_lock:
            docker_rows = rows
        time.sleep(REFRESH_INTERVAL)

# Dashboard
def draw_dashboard(start_time):
    BLUE_BG = "\033[44m"
    RESET = "\033[0m"
    last_rows = []
    last_refresh = 0

    while True:
        now = time.time()

        # Redraw dashboard every REFRESH_INTERVAL
        if now - last_refresh >= REFRESH_INTERVAL or not last_rows:
            os.system("clear")

            # Top banners
            print_banner(f"📡 Connected to: {ACTIVE_HOSTNAME or SSH_HOST}")
            print_banner("🐳 Docker Infrastructure Dashboard")
            print_divider()

            # Table
            with rows_lock:
                rows_copy = docker_rows.copy()
            if rows_copy:
                table_content = tabulate(
                    rows_copy,
                    headers=["Name", "Image", "Status", "CPU", "Mem", "Source"],
                    tablefmt="fancy_grid",
                    stralign="center"
                )
                table_content = color_status_table(table_content)
                table_lines = table_content.splitlines()
                for line in table_lines:
                    print(line.center(terminal_width))
            else:
                table_lines = ["No containers found"]
                print("No containers found".center(terminal_width))

            # Reserve one line for the timer
            print(" " * terminal_width)

            last_rows = rows_copy
            last_refresh = now

        # Timer update every second
        uptime_sec = int(time.time() - start_time)
        h, rem = divmod(uptime_sec, 3600)
        m, s = divmod(rem, 60)
        uptime_str = f"{h:02d}h {m:02d}m {s:02d}s"

        # Countdown to next refresh
        elapsed_since_refresh = int(now - last_refresh)
        remaining = REFRESH_INTERVAL - elapsed_since_refresh
        if remaining < 0:
            remaining = 0

        msg = f"🔄 Refreshing in {remaining}s | Uptime: {uptime_str}"

        # Move cursor up 1 line (reserved timer line), clear line, print updated timer
        print(f"\033[1A\033[2K{BLUE_BG}{msg.center(terminal_width)}{RESET}", end="\r", flush=True)

        time.sleep(1)



# Main
def main():
    start_time = time.time()

    # Initial fetch
    rows = []
    if SSH_MODE == "ON":
        rows += docker_list_remote()
    rows += docker_list_local()
    with rows_lock:
        docker_rows[:] = rows

    # Start updater thread
    threading.Thread(target=update_docker_stats, daemon=True).start()

    # Launch dashboard
    draw_dashboard(start_time)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[+] Dashboard terminated.")


