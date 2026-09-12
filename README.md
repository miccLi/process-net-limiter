# 进程网络限速助手 (ProcessNetLimiter)

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/Language-Python%203.10+-brightgreen?style=flat-square" alt="Language">
  <img src="https://img.shields.io/badge/GUI-PyQt5-purple?style=flat-square" alt="PyQt5">
  <img src="https://img.shields.io/badge/License-MIT-orange?style=flat-square" alt="License">
</p>

**ProcessNetLimiter** 是一个轻量级、现代化的 Windows 桌面应用程序。能够实时枚举系统中所有正在运行的程序，智能将**游戏、网盘、下载器**优先置顶，支持多选并自由限制上传与下载速度（提供 `完全断开连接`、`1 KB/s`、`100 KB/s`、`1000 KB/s` 及 `自定义限速`），且支持上传和下载独立配置与一键解除所有限制。

---

## ✨ 核心特性

- 🎯 **智能分类与优先置顶**：
  - 自动识别并分类：⚡ 下载器（迅雷、IDM、qBittorrent等）、☁️ 网盘（OneDrive、百度网盘、阿里云盘等）、🎮 游戏（Steam、Epic、原神、CS2等）、🌐 浏览器与通讯。
  - 排序优先级：已限速程序 > 下载器 > 网盘 > 游戏 > 活跃网络连接程序 > 普通后台进程。
- 🚀 **灵活速度限制档位**：
  - **完全断开连接 (0 KB/s)**：一键彻底阻断目标程序的网络通信。
  - **1 KB/s**：极速限制，适合断流测试或后台静默。
  - **100 KB/s**：低速限制，保留基本心跳包与连接，不占带宽。
  - **1000 KB/s**：约 1 MB/s 中速限制，在后台下载的同时确保前台浏览和游戏毫无延迟。
  - **自定义速度限制**：支持自由输入任意数值与单位（KB/s、MB/s）。
- ⚙️ **上传与下载独立控制**：
  - 既支持“上传下载联动设置”，也支持分别独立配置上传速度与下载速度。
- ⚡ **一键解除全部限制**：
  - 一键扫描并清空所有由本工具下发的 QoS 限速策略与断网规则，恢复全局正常网络。
- 🛡️ **原生 Windows QoS + 高级防火墙机制**：
  - 无需安装第三方不稳定驱动或未签名驱动，不报毒，不导致蓝屏，随用随关。
- 🎨 **极简深色现代化 UI**：
  - 基于 PyQt5 打造的现代化深色质感界面，支持多选、实时搜索与高分屏缩放。

---

---

## 🛠️ 安装与运行

### 依赖环境
- Windows 10 / Windows 11
- Python 3.10 或更高版本

### 安装步骤
1. 克隆代码仓库：
   ```bash
   git clone https://github.com/miccLi/process-net-limiter.git
   cd process-net-limiter
   ```
2. 安装所需依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 启动程序：
   - **推荐方式**：双击运行 `run.bat`（会自动检测并请求管理员权限以确保 QoS 规则正常下发）。
   - **命令运行**：右键以管理员身份打开 PowerShell/CMD，运行：
     ```bash
     python main.py
     ```

---

## 📖 使用指南

1. **刷新与筛选**：打开程序后，所有正在运行的进程会自动分类呈现，游戏、网盘和下载器会自动置顶。
2. **勾选程序**：在表格左侧勾选一个或多个想要限速的目标进程（支持点击行快速选中）。
3. **选择限速档位**：
   - 在底部下拉框中选择预设限速（1 KB/s、100 KB/s、1000 KB/s、完全断网或自定义）。
   - 如需分别设置，勾选“分别设置上传和下载速度”。
4. **应用限速**：点击 `🚀 应用限速`，规则将在 1 秒内生效。
5. **解除限制**：
   - 勾选程序后点击 `❌ 取消选中限制`；
   - 或随时点击 `⚡ 一键解除全部限制` 恢复初始网络状态。

---

## 📄 开源许可证

本项目采用宽松的 [MIT License](LICENSE) 开源，任何人均可自由用于个人学习、修改或商业用途。


---

---

## 📄 开源许可证

本项目采用宽松的 [MIT License](LICENSE) 开源，任何人均可自由用于个人学习、修改或商业用途。
