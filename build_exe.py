# -*- coding: utf-8 -*-
"""
ProcessNetLimiter 生产级自动化构建脚本 (build_exe.py)
- 自动检测并提取合规 EV 数字签名的 WinDivert64.sys / WinDivert64.dll 驱动
- 内嵌 Windows 原生管理员提权清单 (app.manifest) 与 PerMonitorV2 高分屏支持
- 剥离冗余依赖，调用 PyInstaller 编译为独立分发二进制
"""
import os
import sys
import shutil
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("BuildScript")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")
MANIFEST_FILE = os.path.join(BASE_DIR, "app.manifest")


def find_windivert_binaries() -> tuple[str, str]:
    """定位 pydivert 包中的官方合规签名驱动文件"""
    try:
        import pydivert
        pkg_dir = os.path.dirname(pydivert.__file__)
        dll_dir = os.path.join(pkg_dir, "windivert_dll")
        sys_path = os.path.join(dll_dir, "WinDivert64.sys")
        dll_path = os.path.join(dll_dir, "WinDivert64.dll")

        if os.path.exists(sys_path) and os.path.exists(dll_path):
            logger.info(f"成功定位 WinDivert 驱动文件: {dll_dir}")
            return dll_path, sys_path
    except ImportError:
        pass

    raise FileNotFoundError("未能在当前 Python 环境中找到合规签名的 WinDivert64 驱动文件，请先安装 pydivert")


def build(mode: str = "onedir"):
    """
    执行 PyInstaller 构建
    :param mode: 'onedir' (生成绿色便携目录，推荐) 或 'onefile' (单文件可执行包)
    """
    logger.info(f"=== 开始构建 ProcessNetLimiter (模式: {mode}) ===")

    dll_path, sys_path = find_windivert_binaries()

    # 构造 PyInstaller 命令行参数
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=ProcessNetLimiter",
        "--noconfirm",
        "--clean",
        "--windowed",  # 无控制台黑框 GUI 程序
    ]

    if mode == "onefile":
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # 注入 Windows 清单文件 (要求管理员权限 + 高分屏)
    if os.path.exists(MANIFEST_FILE):
        cmd.extend(["--manifest", MANIFEST_FILE])
        logger.info(f"已附加清单文件: {MANIFEST_FILE}")

    # 包含 WinDivert 核心驱动二进制
    # 添加到 pydivert/windivert_dll 相对路径下
    cmd.extend([
        "--add-binary", f"{dll_path};pydivert/windivert_dll",
        "--add-binary", f"{sys_path};pydivert/windivert_dll",
        # 同时复制到 exe 所在根目录以防相对路径寻址
        "--add-binary", f"{dll_path};.",
        "--add-binary", f"{sys_path};.",
    ])

    # 排除无需打包的庞大无关第三方库以极致缩减体积
    excludes = [
        "tkinter", "unittest", "pydoc", "doctest", "argparse",
        "matplotlib", "numpy", "scipy", "PIL", "pandas"
    ]
    for ex in excludes:
        cmd.extend(["--exclude-module", ex])

    # 指定主程序入口文件
    main_py = os.path.join(BASE_DIR, "main.py")
    cmd.append(main_py)

    logger.info("正在执行打包命令: " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=BASE_DIR)

    if result.returncode != 0:
        logger.error(f"打包失败，PyInstaller 返回退出码: {result.returncode}")
        return False

    logger.info("=== 打包成功！产物已输出至 dist/ 目录 ===")
    return True


if __name__ == "__main__":
    mode_arg = sys.argv[1] if len(sys.argv) > 1 else "onedir"
    success = build(mode_arg)
    sys.exit(0 if success else 1)
