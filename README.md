# ProcessNetLimiter (进程网络限速助手)

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
  <b>一款专为 Windows 10/11 打造的轻量级、工业级进程带宽管理与网络阻断桌面工具。</b><br>
  搭载 <b>WinDivert 微软官方 EV 认证内核级流量整形驱动</b> 与 <b>Windows 原生 QoS / 防火墙双引擎自愈架构</b>，提供任务管理器式进程家族树状管理、微秒级令牌桶双向硬限速（严格卡死 1KB/s，支持网游 UDP 与多线程下载）、实时动态流量监控、高权限静默常驻及零残留卸载清理保障。
</p>

---

## ✨ 核心特性

- 🌲 **任务管理器风格进程家族树**：
  - 智能将同一应用的关联进程（如 Steam 主程序与 `steamwebhelper.exe`、百度网盘与传输宿主等）聚合为可折叠的多级树状视图；
  - 家族父节点聚合汇总展示全家族的总下载/上传速度与活跃连接数；
  - 创新三态复选框逻辑，既支持对整个应用一键限速，也支持展开家族对某一个特定子进程精准控制而不误伤兄弟进程。
- ⚡ **实时网络流量测速与吞吐监控**：
  - 基于 WinDivert 收包循环微秒级物理数据包统计，辅以整机 `psutil` 流量采样兜底；
  - 指数移动平均（EMA，$\alpha = 0.7$）平滑过滤突发波动，静默周期自动衰减归零；
  - **零闪烁微刷新机制**：每秒精准更新速度文本与颜色，绝不触碰复选框、不重构列表项、不干扰用户滚动；
  - 顶部看板与托盘 Tooltip 实时同步全局上下行真实带宽。
- 🚀 **双引擎高可用与平滑降级自愈**：
  - **内核驱动模式 (默认优先)**：采用微软官方数字签名的 `WinDivert64.sys` 驱动，搭配异步 Pacer 延迟队列，实现与 NetLimiter 同级的入站/出站双向精准控速，毫秒级生效，完美支持游戏 UDP 阻断与 CDN 极限压制；
  - **原生兼容模式 (优雅降级)**：若驱动被杀软拦截或系统开启高强度隔离，引擎自动热降级至 Windows 原生 QoS 组策略与高级防火墙模式，策略无缝迁移，0 闪退崩溃。
- 🛡️ **网络兼容性防护与冲突避让**：
  - 自动识别 Wintun、WireGuard、OpenVPN、Tailscale 等 TUN/TAP 虚拟网卡及雷神、UU 等游戏加速器网段（`198.18.0.0/15`）；
  - 智能放行组播（`224.0.0.0/4`, `239.255.255.250`）与局域网广播（`255.255.255.255`），消除对 SSDP、mDNS、LLMNR 局域网服务发现的误伤。
- 💾 **策略规则持久化与路径漂移自愈**：
  - 本地规则库自动持久化于 `%LOCALAPPDATA%\ProcessNetLimiter\rules.json`，重启开机自动重新对齐；
  - 目标程序版本迭代升级导致安装路径变更（如 Chrome/Edge 版本号路径变动）时，自愈算法自动校准绝对路径并重载防火墙绑定。
- 🖥️ **系统托盘常驻与无感开机启动**：
  - 关闭主窗口时默认平滑最小化至系统托盘常驻，保障后台限速持续生效；
  - 依托 Windows 计划任务（`schtasks.exe`）注册最高运行级别，开机直接静默进驻托盘，无需每次开机重复弹窗 UAC；
  - 托盘提供 **⚡ 紧急恢复网络** 按钮，瞬时清空全局所有限速与阻断。
- 📦 **生产级独立打包与零残留卸载清理**：
  - 内嵌 Windows 官方清单（`app.manifest`），声明 `requireAdministrator` 提权、`PerMonitorV2` 高分屏缩放与长路径支持；
  - 提供 Inno Setup 专业安装向导（`installer/setup.iss`），支持双语安装；
  - 卸载执行段注入 `--uninstall-cleanup` 命令行静默钩子，卸载时彻底清除所有 `NetLimit_*` 组策略与防火墙规则，杜绝“卸载后遗留断网”隐患。
- 🌐 **中英双语国际化 (i18n)**：
  - 运行时支持秒级热切换简体中文与英文，启动时自动适配操作系统本地语言。

---

## 🖥️ 界面布局设计

列表列采用符合人体工学的信息重要性排布：

| 列序 | 列名 | 说明 |
| :---: | :--- | :--- |
| **1** | **[x]** | 批量复选框（支持父子级联动多选与单选解耦） |
| **2** | **程序名称 / 进程家族** | 家族友好名称及可折叠展开的多级进程树 |
| **3** | **当前限制状态** | 核心关注项前置，高亮显示当前生效的限速或阻断策略 |
| **4** | **↑ 上传** | 实时微秒级测速（动态微刷新，如 `↑ 142 KB/s`） |
| **5** | **↓ 下载** | 实时微秒级测速（动态微刷新，如 `↓ 3.8 MB/s`） |
| **6** | **PID** | 进程标识符（家族行显示进程总数） |
| **7** | **类别** | 彩色分类徽章（游戏、网盘、下载器、浏览器等） |
| **8** | **网络连接** | 当前活跃 TCP/UDP 套接字数量 |
| **9** | **执行文件路径** | 绝对物理路径，置于最右侧，窗口收窄时不遮挡核心信息 |

---

## 🛠️ 安装与快速开始

### 运行环境要求
- **操作系统**：Windows 10 / Windows 11 (64位)
- **权限要求**：管理员权限（UAC 提权）
- **Python 环境**：Python 3.10 或更高版本（仅从源码运行时需要）

### 途径一：预编译安装包（普通用户推荐）
1. 在 [GitHub Releases](https://github.com/miccLi/process-net-limiter/releases) 下载最新版本的 `ProcessNetLimiter-Setup-x64.exe`；
2. 运行安装向导，按提示完成安装（可选开机自启动）；
3. 从桌面或开始菜单启动即可。

### 途径二：从源代码运行
1. **克隆代码库**：
   ```bash
   git clone https://github.com/miccLi/process-net-limiter.git
   cd process-net-limiter
   ```
2. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```
3. **以管理员权限运行**：
   - 双击根目录下的 `run.bat`（自动处理管理员提权）；
   - 或在管理员 PowerShell/CMD 中执行：
     ```bash
     python main.py
     ```

---

## ⌨️ 命令行参数速查

| 参数 | 说明 |
| :--- | :--- |
| *(无参数)* | 正常启动并显示主窗口。 |
| `--minimized` | 启动后自动最小化进驻系统托盘（开机计划任务专用）。 |
| `--uninstall-cleanup` | 静默注销全部防火墙规则、QoS 策略、计划任务与本地规则库（Inno Setup 卸载钩子专用）。 |

---

## 🔨 二进制构建与打包

使用内置自动化构建脚本将项目打包为独立单文件或目录型 `.exe`：

```bash
# 安装 PyInstaller
pip install pyinstaller

# 运行自动化打包脚本（自动提取官方 EV 签名驱动并嵌入 manifest）
python build_exe.py
```

构建产物将输出至 `dist/ProcessNetLimiter/`。若需编译安装向导，使用 Inno Setup 6 编译 `installer/setup.iss` 即可。

---

## 🧪 单元测试

项目内置了高覆盖率的自动化测试套件（涵盖限速引擎、流量监控、规则持久化、降级自愈及卸载清理等 62 项用例）：

```bash
python run_tests.py
```

---

## 📄 开源许可证与第三方声明

- 本项目核心代码基于 [MIT License](LICENSE) 协议开源；
- 内核流量整形模块依托官方合规数字签名的 [WinDivert](https://reqrypt.org/windivert.html) 驱动（遵循 LGPLv3 / GPLv2 双许可协议），由 PyPI `pydivert` 包分发；
- 完整第三方许可证声明详见 [LICENSE](LICENSE)。
