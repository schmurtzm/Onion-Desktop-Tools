FSUTIL DIRTY query %SystemDrive% >NUL || (
    PowerShell "Start-Process -FilePath cmd.exe -Args '/C CHDIR /D %CD% & "%0"' -Verb RunAs"
    EXIT
)

@echo off
cd /d %~dp0
md backups 2> NUL
md downloads\ODT_updates 2> NUL
copy ODT_update.ps1 ODT_update_temporary.ps1 /Y >NUL
powershell -ExecutionPolicy Bypass -File ODT_update_temporary.ps1