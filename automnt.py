import subprocess
import json
import os
import getpass
import time

CONFIG_FILE = "config.json"
PIDS_FILE = "pids.json"
MOUNTS_FILE = "mounts.json"
MOUNT_BASE_DIR = f"/home/{getpass.getuser()}/mounts"
LOG_FILE = "automnt.log"

# Default values for mount objects
MOUNT_DEFAULTS = {
    "options": [],
    "auto_restart": False,
    "description": "No description provided",
    "enable": True
}

# Default global configurations
GLOBAL_DEFAULTS = {
    "default_options": {
        "--vfs-cache-mode": "writes",
        "--buffer-size": "32M"
    },
    "watchdog_interval": 10,
    "log_level": "INFO",
    "mount_base_dir": MOUNT_BASE_DIR
}

def log_message(message):
    with open(LOG_FILE, "a") as log_file:
        log_file.write(message + "\n")

def is_valid_mount(mount):
    """
    Check if the mount has the minimum required information: valid remote and mount_point.
    """
    remote = mount.get("remote", {})
    mount_point = mount.get("mount_point")

    if not isinstance(remote, dict) or "name" not in remote or "type" not in remote:
        return False
    if not isinstance(mount_point, str) or not mount_point.strip():
        return False

    return True

def load_global_config():
    """
    Load the global configuration from the CONFIG_FILE.
    """
    global_config = GLOBAL_DEFAULTS.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as file:
                config_data = json.load(file).get("global_config", {})
                global_config.update(config_data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            log_message(f"Error loading global config: {e}")
    return global_config

def load_mounts():
    """
    Load the mount configuration from the MOUNTS_FILE.
    """
    if os.path.exists(MOUNTS_FILE):
        with open(MOUNTS_FILE, "r") as file:
            mounts = json.load(file)
            # Apply defaults to all mounts and validate minimum requirements
            for mount in mounts:
                for key, value in MOUNT_DEFAULTS.items():
                    mount.setdefault(key, value)
                if not is_valid_mount(mount):
                    mount["enable"] = False
                    log_message(f"Mount {mount.get('name', 'Unnamed')} disabled due to invalid configuration.")
            return mounts
    return []

def save_mounts(mounts):
    """
    Save mount objects to the MOUNTS_FILE.
    """
    try:
        with open(MOUNTS_FILE, "w") as file:
            json.dump(mounts, file, indent=4)
    except IOError as e:
        log_message(f"Error saving mounts: {e}")

def save_pids(pids):
    with open(PIDS_FILE, "w") as file:
        json.dump(pids, file, indent=4)

def load_pids():
    try:
        with open(PIDS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def resolve_mount(name):
    """
    Resolve a mount name to a mount object using the MOUNTS_FILE.
    """
    mounts = load_mounts()
    for mount in mounts:
        if mount["name"] == name:
            return mount
    log_message(f"Mount '{name}' not found.")
    return None

def start_mount(mount):
    """
    Start an Rclone mount based on a mount object.
    """
    if not mount.get("enable", True):
        log_message(f"Mount {mount['name']} is disabled and will not be started.")
        return

    global_config = load_global_config()
    default_options = global_config.get("default_options", {})

    os.makedirs(mount["mount_point"], exist_ok=True)
    command = ["rclone", "mount", mount["remote"]["name"], mount["mount_point"], "--daemon"]

    # Add global default options
    for option, value in default_options.items():
        command.extend([option, value])

    # Add mount-specific options
    if "options" in mount:
        command.extend(mount["options"])

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    pids = load_pids()
    pids[mount["name"]] = {
        "pid": process.pid,
        "mount_point": mount["mount_point"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_pids(pids)
    log_message(f"Started mount for {mount['name']} (PID: {process.pid})")

def stop_mount(mount_name):
    """
    Stop a specific Rclone mount using its name.
    """
    pids = load_pids()
    if mount_name in pids:
        pid = pids[mount_name]["pid"]
        mount_point = pids[mount_name]["mount_point"]
        try:
            os.kill(pid, 15)  # SIGTERM
            log_message(f"Stopped mount for {mount_name} (PID: {pid})")
        except ProcessLookupError:
            log_message(f"Process {pid} not found for {mount_name}. Cleaning up.")
        subprocess.run(["fusermount", "-u", mount_point], check=False)
        del pids[mount_name]
        save_pids(pids)

def validate_mount(mount_point):
    """
    Check if the specified mount point is still valid.
    """
    return os.path.ismount(mount_point)

def start_mnt(*mount_names):
    """
    Start one or more mounts by their names.
    """
    for name in mount_names:
        mount = resolve_mount(name)
        if mount:
            start_mount(mount)

def stop_mnt(*mount_names):
    """
    Stop one or more mounts by their names.
    """
    for name in mount_names:
        stop_mount(name)

def mnt_status(mnt_name=None):
    """
    Get the status of all mounts or a specific mount.
    """
    mounts = load_mounts()
    pids = load_pids()

    def get_status(mount):
        name = mount["name"]
        if not mount.get("enable", True):
            return "Disabled"
        elif name in pids:
            return "Active" if validate_mount(pids[name]["mount_point"]) else "Inactive"
        return "Not Mounted"

    if mnt_name:
        mount = resolve_mount(mnt_name)
        if mount:
            return {mnt_name: get_status(mount)}
        else:
            return {mnt_name: "Not Found"}
    else:
        return {m["name"]: get_status(m) for m in mounts}

def watchdog():
    """
    Monitor all active mounts and restart failed ones if auto_restart is enabled.
    """
    global_config = load_global_config()
    interval = global_config.get("watchdog_interval", 10)

    log_message("Watchdog started.")
    while True:
        pids = load_pids()
        mounts = load_mounts()
        for mount in mounts:
            if not mount.get("enable", True):
                continue
            if mount["name"] in pids and not validate_mount(pids[mount["name"]]["mount_point"]):
                if mount.get("auto_restart", False):
                    log_message(f"Mount {mount['name']} failed. Restarting...")
                    start_mount(mount)
                else:
                    log_message(f"Mount {mount['name']} failed. Auto-restart disabled.")
        time.sleep(interval)

def import_mounts_from_rclone():
    """
    Import mounts from Rclone's config and write them to the MOUNTS_FILE.
    """
    try:
        result = subprocess.run(
            ["rclone", "listremotes"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        remotes = result.stdout.strip().split("\n")
        mounts = load_mounts()
        for remote in remotes:
            if remote:  # Ensure it's not an empty line
                mount_name = remote.strip(":")
                mount_point = os.path.join(MOUNT_BASE_DIR, mount_name)
                mount = {
                    "name": mount_name,
                    "remote": {"name": remote, "type": "unknown"},
                    "mount_point": mount_point,
                    "options": [],
                    "auto_restart": False,
                    "description": f"Imported mount for {remote}",
                    "enable": True
                }
                if not any(m["name"] == mount_name for m in mounts):
                    mounts.append(mount)
        save_mounts(mounts)
        log_message("Mounts imported successfully from Rclone.")
    except subprocess.CalledProcessError as e:
        log_message(f"Error importing mounts from Rclone: {e.stderr}")

def cli():
    import sys
    if len(sys.argv) < 2:
        print("Usage: automnt.py <start|stop|watchdog|status|import> [mount-name|all]")
        return

    action = sys.argv[1]
    target = sys.argv[2:] if len(sys.argv) > 2 else []

    if action == "start":
        if "all" in target:
            for mount in load_mounts():
                start_mount(mount)
        else:
            start_mnt(*target)
    elif action == "stop":
        if "all" in target:
            for mount_name in list(load_pids().keys()):
                stop_mount(mount_name)
        else:
            stop_mnt(*target)
    elif action == "watchdog":
        watchdog()
    elif action == "status":
        result = mnt_status(target[0] if target else None)
        if isinstance(result, dict):
            for name, status in result.items():
                print(f"{name}: {status}")
        else:
            print(result)
    elif action == "import":
        import_mounts_from_rclone()
    else:
        print("Invalid action. Use start, stop, watchdog, status, or import.")

if __name__ == "__main__":
    cli()

