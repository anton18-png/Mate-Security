@echo off
setlocal

REM Удаляем старые сборки
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM GUI Mate Security
pyinstaller ^
  --noconfirm ^
  --clean ^
  --name "Mate-Security" ^
  --icon "icon.ico" ^
  --add-data "main.pyw;." ^
  --add-data "database;database" ^
  --add-data "Utils;Utils" ^
  --add-data "core;core" ^
  --add-data "gui;gui" ^
  main.pyw

cd dist
explorer .
