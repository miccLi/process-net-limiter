; =====================================================================
; Inno Setup 6.x Simplified Chinese Official Community Translation
; =====================================================================

[LangOptions]
LanguageName=简体中文
LanguageID=$0804
LanguageCodePage=936

[Messages]
; --- Application Titles ---
SetupAppTitle=安装
SetupWindowTitle=安装 - %1
UninstallAppTitle=卸载
UninstallWindowTitle=卸载 - %1

; --- Buttons ---
ButtonBack=< 上一步(&B)
ButtonNext=下一步(&N) >
ButtonInstall=安装(&I)
ButtonOK=确定
ButtonCancel=取消
ButtonYes=是(&Y)
ButtonYesToAll=全是(&A)
ButtonNo=否(&N)
ButtonNoToAll=全否(&O)
ButtonFinish=完成(&F)
ButtonBrowse=浏览(&B)...
ButtonWizardBrowse=浏览(&R)...
ButtonNewFolder=新建文件夹(&M)

; --- Wizard Common Messages ---
ExitSetupTitle=退出安装程序
ExitSetupMessage=安装尚未完成。如果您现在退出，程序将不会被安装。%n%n您可以稍后再次运行安装程序以完成安装。%n%n确定要退出安装程序吗？
AboutSetupMenuItem=关于安装程序(&A)...
AboutSetupTitle=关于安装程序
AboutSetupMessage=%1 版本 %2%n%3%n%n%1 官方网站:%n%4
AboutSetupNote=

; --- Welcome & License ---
ClickNext=单击“下一步”继续，或单击“取消”退出安装程序。
BeveledLabel=

; --- Directory Selection ---
SelectDirTitle=选择目标位置
SelectDirLabel=程序将安装到以下文件夹中。
SelectDirBrowseLabel=单击“下一步”继续。如果要选择其它文件夹，请单击“浏览”。
DiskSpaceMBLabel=至少需要有 [mb] MB 的可用磁盘空间。
CannotInstallToNetworkDrive=不能安装到网络驱动器。
CannotInstallToUNCPath=不能安装到 UNC 路径。
InvalidPath=您必须输入包含盘符的完整路径，例如:%n%nC:\APP%n%n或形如以下格式的 UNC 路径:%n%n\\server\share
InvalidDrive=您选择的驱动器或 UNC 共享不存在或无法访问。请选择其它位置。
DiskSpaceWarningTitle=磁盘空间不足
DiskSpaceWarning=安装程序至少需要 %1 KB 的可用磁盘空间才能安装，但所选驱动器只有 %2 KB 可用。%n%n您仍要继续吗？
DirNameTooLong=文件夹名称或路径太长。
InvalidDirName=文件夹名称无效。
BadDirNameChars=文件夹名称不能包含以下任何字符:%n%n%1
DirExistsTitle=文件夹已存在
DirExists=文件夹:%n%n%1%n%n已存在。您仍要安装到此文件夹吗？
DirDoesntExistTitle=文件夹不存在
DirDoesntExist=文件夹:%n%n%1%n%n不存在。您要创建此文件夹吗？

; --- Program Group Selection ---
SelectComponentsTitle=选择组件
SelectComponentsLabel=选择您要安装的组件；清除您不想安装的组件。单击“下一步”继续。
ComponentSize1=%1 KB
ComponentSize2=%1 MB
ComponentsDiskSpaceMBLabel=当前选择至少需要 [mb] MB 的磁盘空间。

; --- Tasks ---
SelectTasksTitle=选择附加任务
SelectTasksLabel=选择您想要安装程序在安装 %1 时执行的附加任务，然后单击“下一步”。

; --- Ready to Install ---
ReadyLabel1=安装程序现在准备开始在您的计算机上安装 %1。
ReadyLabel2a=单击“安装”继续此安装，或单击“上一步”检查或更改任何设置。
ReadyLabel2b=单击“安装”继续此安装。
ReadyMemoUserInfo=用户信息:
ReadyMemoDir=目标位置:
ReadyMemoType=安装类型:
ReadyMemoComponents=选定组件:
ReadyMemoGroup=程序文件夹:
ReadyMemoTasks=附加任务:

; --- Installing ---
InstallingLabel=安装程序正在将 %1 安装到您的计算机中，请稍候。

; --- Finishing ---
FinishedHeadingLabel=正在完成 %1 安装向导
FinishedLabelNoIcons=%1 已在您的计算机中安装完成。
FinishedLabel=%1 已在您的计算机中安装完成。可以通过选择已安装的图标来启动此应用程序。
ClickFinish=单击“完成”退出安装程序。

; --- Status Messages ---
StatusClosingApplications=正在关闭应用程序...
StatusCreateDirs=正在创建目录...
StatusExtractFiles=正在解压缩文件...
StatusCreateIcons=正在创建快捷方式...
StatusCreateIniEntries=正在创建 INI 条目...
StatusCreateRegistryEntries=正在创建注册表项...
StatusRegisterFiles=正在注册文件...
StatusSavingVersionCreation=正在保存版本信息...
StatusRollback=正在撤销更改...

; --- Uninstaller ---
ConfirmUninstall=您确定要完全删除 %1 及其所有组件吗？
UninstallStatusLabel=正在从您的计算机中删除 %1，请稍候。
UninstalledAll=%1 已成功从您的计算机中删除。
UninstalledMost=%1 卸载完成。%n%n某些元素无法删除。这些可以手动删除。
UninstalledAndNeedsRestart=要完成 %1 的卸载，必须重新启动您的计算机。%n%n您想现在重新启动吗？
UninstallDataQuestion=是否同时删除所有保存的用户配置文件与日志？
