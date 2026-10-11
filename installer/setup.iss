; =====================================================================
; ProcessNetLimiter - Professional Inno Setup Script
; Windows 10/11 x64 现代进程网络限速与阻断桌面工具专业安装向导
; 支持中英文双语、管理员 UAC 提权、桌面快捷方式与卸载彻底清理钩子
; =====================================================================

#define MyAppName "ProcessNetLimiter"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ProcessNetLimiter Open Source Project"
#define MyAppURL "https://github.com/miccLi/process-net-limiter"
#define MyAppExeName "ProcessNetLimiter.exe"

[Setup]
; 基础应用信息与全局 GUID (用于版本升级覆盖安装)
AppId={{D37E8491-58A2-4CFB-9B21-B88E8F5C1B69}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 安装路径与 64 位原生架构
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

; 权限要求：必须以管理员权限安装，以便注册计划任务与网络驱动
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; 输出目录与文件名
OutputDir=..\dist
OutputBaseFilename=ProcessNetLimiter-Setup-x64
Compression=lzma2/ultra64
SolidCompression=yes

; 界面视觉风格
WizardStyle=modern
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "开机自启 (通过系统计划任务静默常驻系统托盘)"; Flags: unchecked; Languages: chinesesimplified
Name: "autostart"; Description: "Start with Windows (Run minimized in system tray)"; Flags: unchecked; Languages: english

[Files]
; 打包来自 dist/ProcessNetLimiter 绿色分发目录下的全部文件
Source: "..\dist\ProcessNetLimiter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; 安装完成后启动程序
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; 若勾选了开机自启，调用计划任务创建
Filename: "schtasks.exe"; Parameters: "/Create /TN ""ProcessNetLimiter_AutoStart"" /TR """"{app}\{#MyAppExeName}"""" --minimized"" /SC ONLOGON /RL HIGHEST /F"; Flags: runhidden; Tasks: autostart

[UninstallRun]
; =====================================================================
; 关键防御机制：卸载前强制调用 --uninstall-cleanup
; 自动扫描并清除所有 NetLimit_* QoS 策略、Windows 防火墙出入站规则与计划任务
; 彻底根除“卸载后遗留断网”隐患！
; =====================================================================
Filename: "{app}\{#MyAppExeName}"; Parameters: "--uninstall-cleanup"; Flags: runhidden waituntilterminated

; 注销可能存在的计划任务自启
Filename: "schtasks.exe"; Parameters: "/Delete /TN ""ProcessNetLimiter_AutoStart"" /F"; Flags: runhidden

[UninstallDelete]
; 清理用户本地持久化配置与规则缓存数据库目录
Type: filesandordirs; Name: "{localappdata}\ProcessNetLimiter"
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.ini"
