# ProcessNetLimiter

<p align="center">
  <a href="README.md"><b>简体中文</b></a> | <a href="README_en.md"><b>English</b></a>
</p>

<p align="center">
  <a href="https://github.com/miccLi/process-net-limiter">
    <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?style=flat-square&logo=windows" alt="Platform">
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://www.riverbankcomputing.com/software/pyqt/">
    <img src="https://img.shields.io/badge/GUI-PyQt5-41CD52?style=flat-square&logo=qt&logoColor=white" alt="PyQt5">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-F5A623?style=flat-square" alt="License">
  </a>
  <a href="https://github.com/miccLi/process-net-limiter/actions">
    <img src="https://img.shields.io/badge/CI-Passing-brightgreen?style=flat-square&logo=github-actions&logoColor=white" alt="CI">
  </a>
</p>

<p align="center">
  <b>A lightweight, modern, industrial-grade process bandwidth limiter and network blocker for Windows 10 & 11.</b><br>
  Powered by an <b>EV-signed WinDivert kernel-level traffic shaper</b> and an <b>auto-fallback Windows Native QoS engine</b>, ProcessNetLimiter offers Task Manager-style process family trees, microsecond-accurate token-bucket pacing (strictly locks down to 1 KB/s, supports gaming UDP and multi-threaded CDNs), real-time live speed monitoring, and zero-residual clean uninstallation.
</p>

---

## ✨ Key Highlights

- 🌲 **Task Manager-Style Process Family Tree**:
  - Automatically groups associated processes (e.g., Steam and `steamwebhelper.exe`, cloud drive transfer daemons) into collapsible family trees;
  - Family parents aggregate total upload/download bandwidth and active socket connections;
  - Supports both full-family one-click throttling and granular sub-process single selection without affecting sibling processes.
- ⚡ **Real-Time Network Speed & Throughput Monitoring**:
  - Microsecond packet-level traffic accounting in the WinDivert loop and system-wide fallback counters via `psutil`;
  - Exponential Moving Average (EMA, $\alpha = 0.7$) eliminates spike jitters;
  - **Zero-flicker micro-refresh**: Dynamically updates text and colors in the tree without touching checkboxes, selection states, or scrollbars;
  - Header badge and tray tooltip display real-time global upload/download speeds.
- 🚀 **Dual-Engine Resilience & High Availability**:
  - **Kernel Driver Mode (Default & Priority)**: Leverages Microsoft EV-signed `WinDivert64.sys` with an asynchronous pacer token bucket queue for strict bidirectional throttling down to 1 KB/s (supporting gaming UDP and multi-connection CDNs);
  - **Native Engine Fallback (Auto-Healing)**: In environments where driver loading is blocked (e.g., restricted policies or HVCI isolation), seamlessly hot-migrates rules to Windows Native QoS policies and Advanced Firewall rules without crashing.
- 🛡️ **Network Compatibility & Conflict Avoidance**:
  - Diagnostic scanner identifies virtual network adapters (Wintun, WireGuard, OpenVPN, Tailscale) and game accelerators (UU, Leigod, etc.);
  - Automatically whitelists multicast (`224.0.0.0/4`, `239.255.255.250`) and broadcast (`255.255.255.255`) traffic to protect local network discovery protocols (SSDP, mDNS, LLMNR).
- 💾 **Rule Persistence & Version Drift Self-Healing**:
  - Persists active rules to `%LOCALAPPDATA%\ProcessNetLimiter\rules.json`;
  - Automatically restores rate limits on system reboot;
  - Dynamically recalculates executable paths when applications update versions (e.g., Chrome/edge directory version bumps), self-healing firewall and QoS bindings.
- 🖥️ **System Tray Daemon & Silent Boot**:
  - Minimizes to system tray on window close (`hide()`) ensuring background enforcement;
  - Registers Task Scheduler highest-privilege tasks (`schtasks.exe`) to start silently on boot without triggering UAC elevation prompts;
  - Provides a single-click **Emergency Network Restore** to instantly purge all limits across the system.
- 📦 **Production-Ready Packaging & Clean Uninstall**:
  - Windows application manifest (`app.manifest`) embedded with `requireAdministrator`, `PerMonitorV2` DPI scaling, and `longPathAware`;
  - Bundled with bilingual Inno Setup script (`installer/setup.iss`);
  - Incorporates `--uninstall-cleanup` silent hook in uninstaller to guarantee 0 lingering rules or broken connections after software removal.
- 🌐 **Bilingual Internationalization (i18n)**:
  - Runtime hot-switching between Simplified Chinese and English;
  - Automatically adopts operating system locale on initial launch.

---

## 🖥️ Process Tree Layout

The user interface adopts an ergonomic column structure:

| Column | Header | Description |
| :---: | :--- | :--- |
| **1** | **[x]** | Tristate checkbox (supports parent-child cascading & independent sub-items) |
| **2** | **Application / Process Family** | Application family tree with collapsible child nodes |
| **3** | **Active Limits** | High-visibility badge indicating current throttling or block status |
| **4** | **↑ Upload** | Real-time upload speed (live micro-refreshed, e.g., `↑ 142 KB/s`) |
| **5** | **↓ Download** | Real-time download speed (live micro-refreshed, e.g., `↓ 3.8 MB/s`) |
| **6** | **PID** | Process ID (family row shows total process count) |
| **7** | **Category** | Color-coded category tags (Game, Cloud, Downloader, Browser, etc.) |
| **8** | **Sockets** | Number of active TCP/UDP connections |
| **9** | **Executable Path** | Full path on disk (safely aligned to right for horizontal scrolling) |

---

## 🛠️ Installation & Getting Started

### Prerequisites
- **Operating System**: Windows 10 / Windows 11 (64-bit)
- **Privileges**: Administrator rights (UAC elevation)
- **Python**: Python 3.10+ (only required if running from source)

### Option 1: Prebuilt Installer (Recommended for Users)
1. Download the latest installer `ProcessNetLimiter-Setup-x64.exe` from [GitHub Releases](https://github.com/miccLi/process-net-limiter/releases);
2. Run the installer and choose your preferred language (English / 简体中文);
3. Launch ProcessNetLimiter from your Desktop or Start Menu.

### Option 2: Running from Source
1. **Clone the repository**:
   ```bash
   git clone https://github.com/miccLi/process-net-limiter.git
   cd process-net-limiter
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Launch with Administrator privileges**:
   - Double-click `run.bat` (automatically handles directory switching and UAC elevation);
   - Or run directly from an elevated terminal:
     ```bash
     python main.py
     ```

---

## ⌨️ Command Line Options

| Parameter | Description |
| :--- | :--- |
| *(None)* | Launches the main graphical interface directly. |
| `--minimized` | Starts the application minimized to the system tray (used by boot autostart). |
| `--uninstall-cleanup` | Silently purges all active firewall rules, QoS policies, Task Scheduler jobs, and persistent stores (used by Inno Setup uninstaller). |

---

## 🔨 Building from Source

To create an autonomous standalone executable using PyInstaller:

```bash
# Install PyInstaller
pip install pyinstaller

# Run the automated build script
python build_exe.py
```

The output will be placed in `dist/ProcessNetLimiter/`. To compile the setup installer, compile `installer/setup.iss` with Inno Setup 6.

---

## 🧪 Testing

Execute the comprehensive automated test suite (62 unit tests):

```bash
python run_tests.py
```

---

## 📄 License & Attributions

- The core source code of **ProcessNetLimiter** is released under the **[MIT License](LICENSE)**;
- The kernel traffic shaping driver relies on **[WinDivert](https://reqrypt.org/windivert.html)** (licensed under LGPLv3 / GPLv2) distributed via official digitally signed binaries;
- See [LICENSE](LICENSE) for full details on third-party notices.
