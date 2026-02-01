@echo off
chcp 65001

curl -g -k -L -# -o "C:\Apps\Mate-Security\_internal\Utils\clamav.zip" "https://github.com/Cisco-Talos/clamav/releases/download/clamav-1.5.1/clamav-1.5.1.win.x64.zip"

"C:\Apps\Mate-Security\_internal\Utils\7za.exe" x "C:\Apps\Mate-Security\_internal\Utils\clamav.zip" -o"C:\Apps\Mate-Security\_internal\Utils" -y
robocopy "C:\Apps\Mate-Security\_internal\Utils\clamav-1.5.1.win.x64" "C:\Apps\Mate-Security\_internal\Utils\clamav" /E /MOVE /COPY:DAT /R:0 /W:0

rd /S /Q "C:\Apps\Mate-Security\_internal\Utils\clamav-1.5.1.win.x64"
del /Q "C:\Apps\Mate-Security\_internal\Utils\clamav.zip"