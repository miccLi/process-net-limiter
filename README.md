# ProcessNetLimiter (进程网络限速助手)

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
</p>

<p align="center">
  <b>一款专为 Windows 打造的轻量级、现代化进程网络带宽管理与限速桌面工具。</b><br>
  搭载 **WinDivert 微软认证内核级流量整形驱动** 与 **Windows 原生 QoS 双引擎架构**，提供类似任务管理器的进程家族树状管理、微秒级令牌桶双向限速（完美卡死 1KB/s，支持游戏 UDP 与多线程下载）以及极速异步响应。
</p>

---

## ✨ 核心特性

- 🌲 **任务管理器风格进程家族树**：
  - 智能将同一应用的关联进程（如 Steam 主进程与 WebHelper、百度网盘与传输宿主等）聚合为可折叠的多级树状菜单；
  - 家族父节点聚合汇总展示全家族的总下载/上传速度与总连接数；
  - 支持直接勾选家族父节点对全应用一键限速，亦支持展开家族仅对特定关键子进程进行精准控制。
- 🎯 **智能分类与优先级置顶**：
  - 内置常见特征识别引擎，自动归类并支持按 **⚡ 下载器**、**☁️ 网盘**、**🎮 游戏**、**🌐 浏览器/通讯** 快捷筛选；
  - 始终将**已受限进程**与核心网络密集型应用（下载器 > 网盘 > 游戏）置顶排序在列表前列。
- 🚀 **多档位限速与完全阻断**：
  - **完全断开连接 (0 KB/s)**：毫秒级切断目标程序的出入站网络连接；
  - **预设档位**：提供 `1 KB/s` (极限测试)、`100 KB/s` (低速让出带宽)、`1000 KB/s` (平稳中速) 等档位；
  - **自定义速度**：支持自由输入任意数值并选择 `KB/s` 或 `MB/s` 单位。
- ⚙️ **上传与下载独立配置**：
  - 既支持上传与下载联动同步设置，也可随时开启“分别设置上传和下载”，指定不同的上下行限速目标。
- 🚀 **双引擎架构 (WinDivert 内核驱动 + 原生 QoS 兼容回退)**：
  - **内核驱动模式 (默认优先)**：采用微软官方数字签名的 `WinDivert64.sys` 驱动，配合高精度微秒级令牌桶算法（Token Bucket），实现与 NetLimiter 同级的毫秒级生效、严格卡死 1KB/s、入站/出站双向精准控速，并全面支持网游 UDP 与多线程并发下载；
  - **原生兼容模式 (优雅降级)**：若处于特定受限环境，系统自动无缝降级至 Windows 原生 QoS 组策略与高级防火墙模式，确保全平台高可用。
- ⚡ **一键批量操作与安全还原**：
  - 多选进程合并为单次极速批处理下发，操作毫无卡顿；
  - 提供醒目的“一键解除全部限制”，瞬间清除系统中所有限速与阻断策略，确保网络 100% 恢复初始状态。

---

## 🖥️ 界面布局设计

表格列采用符合人体工学的信息重要性排布：

| 列序 | 列名 | 说明 |
| :--- | :--- | :--- |
| **1** | **[x]** | 批量复选框（支持父子级联动多选） |
| **2** | **程序名称 / 进程家族** | 家族友好名称及可折叠展开的多级进程树 |
| **3** | **当前限制状态** | 核心关注项前置，清晰展示当前生效的限速或断网策略 |
| **4** | **PID** | 进程标识符（家族行显示进程总数） |
| **5** | **类别** | 游戏、网盘、下载器等彩色分类徽章 |
| **6** | **网络连接** | 当前活跃套接字（Socket）数量 |
| **7** | **执行文件路径** | 置于最右侧，窗口收窄时平滑滚动，不挤占核心视图 |

---

## 🛠️ 安装与快速开始

### 运行环境要求
- **操作系统**：Windows 10 / Windows 11 (64位)
- **Python 环境**：Python 3.10 或更高版本

### 快速启动步骤
1. **获取代码**：
   ```bash
   git clone https://github.com/miccLi/process-net-limiter.git
   cd process-net-limiter
   ```
2. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```
3. **启动程序**：
   - **推荐方式**：双击根目录下的 `run.bat`，系统会自动弹出 Windows UAC 管理员提权对话框，点击“是”即可享有完整网络策略管理权限；
   - **命令行方式**：以管理员身份运行 PowerShell 或 CMD：
     ```bash
     python main.py
     ```

---

## 📖 常用操作指南

1. **查看与筛选**：打开软件后，所有运行中的程序自动分组为进程家族，点击分类按钮（如“⚡ 筛选下载器”、“🎮 筛选游戏”）可快速聚焦目标应用；
2. **选择目标**：
   - 若要限制整个应用家族，直接勾选其父级复选框；
   - 若仅想限制某一个辅助子进程，点击展开家族后单独勾选该子项；
3. **设定与应用**：在底部下拉框中选择速度档位（或输入自定义速率），点击 `🚀 应用限速`，策略将在 0.5 秒内极速下发；
4. **解除限制**：勾选程序后点击 `❌ 取消选中限制`，或随时点击 `⚡ 一键解除全部限制` 恢复全局网络。

---

## 🧪 单元测试

项目内置了标准单元测试套件，用于验证策略转换、进程扫描与网速计算模块：
```bash
python run_tests.py
```

---

## 📄 开源许可证与第三方组件

- 本项目主体基于 [MIT License](LICENSE) 协议开源，允许自由用于学习、二次开发或商业用途；
- 内核流量整形模块依托 [WinDivert](https://reqrypt.org/windivert.html) 驱动（遵循 LGPLv3 / GPLv2 双许可协议），由 PyPI `pydivert` 官方包合规打包引入。
