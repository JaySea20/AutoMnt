# Automnt - Developer Documentation

## Overview
`Automnt` is a Python-based application for managing Rclone mounts. The app leverages JSON-based configuration files for defining mount objects, tracking active mounts, and managing global settings. This documentation is intended for developers who wish to understand the app’s structure, the JSON schemas, and the available methods.

---

## Directory Structure
```plaintext
.
├── automnt.py        # Main Python script containing all logic
├── config.json       # Global configuration for default settings
├── mounts.json       # List of mount objects
├── pids.json         # Tracks active mount processes (runtime data)
├── automnt.log       # Log file for operational events
```

---

## JSON File Details

### 1. `config.json`
Global settings that apply across all mounts.

#### Example:
```json
{
    "global_config": {
        "defaults": {
            "options": {
                "--vfs-cache-mode": "writes",
                "--buffer-size": "32M"
            },
            "auto_restart": false,
            "description": "Default mount configuration",
            "enable": true
        },
        "watchdog_interval": 10,
        "log_level": "INFO",
        "mount_base_dir": "/home/user/mounts"
    }
}
```

#### Key Fields:
- **`defaults.options`**: Default Rclone mount options.
- **`defaults.auto_restart`**: Auto-restart policy for mounts.
- **`defaults.description`**: Description applied to new mounts.
- **`watchdog_interval`**: Interval (in seconds) for the watchdog to check mounts.
- **`log_level`**: Verbosity of logs (e.g., `INFO`, `DEBUG`).
- **`mount_base_dir`**: Base directory for mount points.

---

### 2. `mounts.json`
Contains an array of mount objects, each representing an Rclone mount.

#### Example:
```json
[
    {
        "name": "backup_drive",
        "remote": {
            "name": "remote1",
            "type": "s3"
        },
        "mount_point": "/home/user/mounts/backup_drive",
        "options": ["--vfs-read-chunk-size", "64M"],
        "auto_restart": true,
        "description": "Backup drive for critical files",
        "enable": true
    }
]
```

#### Key Fields:
- **`name`**: Unique identifier for the mount.
- **`remote.name`**: Name of the Rclone remote.
- **`remote.type`**: Type of the remote (e.g., `s3`, `drive`).
- **`mount_point`**: Filesystem path where the remote is mounted.
- **`options`**: Mount-specific Rclone options.
- **`auto_restart`**: Whether the mount should auto-restart if it fails.
- **`description`**: Description of the mount.
- **`enable`**: Whether the mount is enabled.

---

### 3. `pids.json`
Tracks active mounts during runtime.

#### Example:
```json
{
    "backup_drive": {
        "pid": 1234,
        "mount_point": "/home/user/mounts/backup_drive",
        "timestamp": "2024-12-14 12:34:56"
    }
}
```

#### Key Fields:
- **`pid`**: Process ID of the active mount.
- **`mount_point`**: Filesystem path of the active mount.
- **`timestamp`**: Time when the mount was started.

---

## Methods and Functions

### 1. `start_mnt(*mount_names)`
Starts one or more mounts by name.
- **Inputs**: Mount names as positional arguments.
- **Logic**: Resolves each name to a mount object and starts it.

### 2. `stop_mnt(*mount_names)`
Stops one or more mounts by name.
- **Inputs**: Mount names as positional arguments.
- **Logic**: Terminates the mount process and unmounts the directory.

### 3. `mnt_status(mnt_name=None)`
Gets the status of a specific mount or all mounts.
- **Inputs**: Mount name (optional).
- **Returns**: A dictionary with mount names as keys and their status as values.

### 4. `watchdog()`
Monitors all active mounts and restarts failed ones if `auto_restart` is enabled.
- **Interval**: Defined by `watchdog_interval` in `config.json`.

### 5. `import_mounts_from_rclone()`
Imports remotes from Rclone and writes them as mount objects to `mounts.json`.
- **Logic**: Uses `rclone listremotes` to fetch remote names and generates default mount configurations.

---

## Example Usage

### Start All Mounts
```bash
python3 automnt.py start all
```

### Stop a Specific Mount
```bash
python3 automnt.py stop backup_drive
```

### Check Status of All Mounts
```bash
python3 automnt.py status
```

### Import Mounts from Rclone
```bash
python3 automnt.py import
```

---

## Developer Notes
1. Ensure `rclone` is installed and configured on the host system.
2. Modify `config.json` to set global defaults and application behavior.
3. `mounts.json` should only be edited via the application to maintain consistency.
4. Use `automnt.log` to debug issues or monitor operations.

---

## Contact
For any questions or contributions, please reach out to the project maintainer.

