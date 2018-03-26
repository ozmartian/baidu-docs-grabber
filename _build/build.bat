@echo off

setlocal

REM ......................setup variables......................

if [%1]==[] (
    goto :usage
) else (
    SET PASS=%1
)

SET ARCH=64
SET BINARCH=x64
SET PYPATH=C:\Python36-x64
SET APPVER=1.0.0

REM ......................cleanup previous build scraps......................

rd /s /q build
rd /s /q dist

REM ......................run pyinstaller......................

"%PYPATH%\scripts\pyinstaller.exe" --clean windows.spec

if exist "dist\baidu-grabber.exe" (
    REM ......................add metadata to built Windows binary......................
    .\verpatch.exe dist\baidu-grabber.exe /va %APPVER%.0 /pv %APPVER%.0 /s desc "Baidu Docs Grabber" /s name "BaiduGrabber" /s copyright "(c) 2018 Pete Alexandrou" /s product "BaiduGrabber %BINARCH%" /s company "ozmartians.com"

    REM ................sign frozen EXE with self-signed certificate..........
    SignTool.exe sign /f codesign.pfx /t http://timestamp.comodoca.com/authenticode /p %PASS% dist\baidu-grabber.exe

    REM ......................call Inno Setup installer build script......................
    cd InnoSetup
    call "C:\Program Files (x86)\Inno Setup 5\iscc.exe" installer.iss

    REM ................sign final redistributable EXE with self-signed certificate..........
    SignTool.exe sign /f ..\codesign.pfx /t http://timestamp.comodoca.com/authenticode /p %PASS% output\BaiduGrabber-Setup.exe
)

goto :eof

:usage
    echo.
    echo Usage:
    echo. 
    echo   build [pfxpass]
    echo. 
    goto :eof

:eof
    endlocal
    exit /b
