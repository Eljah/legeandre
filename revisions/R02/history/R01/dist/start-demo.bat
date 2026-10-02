@echo off
cd /d "%~dp0"
java -jar lezhandr-desktop-demo.jar
if errorlevel 1 pause
