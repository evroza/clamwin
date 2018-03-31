rem @echo off
set CYGWINDIR=C:\cygwin64
set THISDIR=F:\Dev\code\clamwin-code
set ISTOOLDIR=C:\Program Files (x86)\Inno Setup 5
set SEVENZIP=C:\Program Files\7-Zip\7z.exe
set UPX_UTIL=E:\IDMDownloads\upx394w\upx.exe

set VCINSTALLDIR=C:\Program Files (x86)\Microsoft Visual Studio 8\VC

set MSSDKDIR=C:\Program Files\Microsoft Platform SDK
set PYTHONDIR=C:\Python23

set WGET_UTIL=E:\ProgramFilesMpya\GnuWin32\bin\wget.exe
set DB_MIRROR=db.au.clamav.net

set BASEVARSSET=1

rem build pyclamav
cd ..\addons\pyc
del /F /Q build\lib.win32-2.3\*
rmdir  build\lib.win32-2.3
del /F /Q build\temp.win32-2.3\Release\*
rmdir build\temp.win32-2.3\Release
rmdir build\temp.win32-2.3
rmdir build

call build.bat release
if not "%ERRORLEVEL%"=="0" goto ERROR
copy .\build\lib.win32-2.3\pyc.pyd "%THISDIR%\py"
if not "%ERRORLEVEL%"=="0" goto ERROR

rem build ExplorerShell
cd %THISDIR%\cpp
call build.bat release
if not "%ERRORLEVEL%"=="0" goto ERROR
cd ..\
rem build BalloonTip.pyd
cd py\BalloonTip
call build.bat
if not "%ERRORLEVEL%"=="0" goto ERROR

rem build py2exe binaries
cd %THISDIR%\setup\py2exe
rd dist /s /q 
call "%PYTHONDIR%\python" setup_all.py
if not "%ERRORLEVEL%"=="0" goto ERROR

rem recompress library with max compression
rem cd dist\lib
rem call "%SEVENZIP%" -aoa x clamwin.zip -olibrary\ 
rem del clamwin.zip
rem cd library
rem call "%SEVENZIP%" a -tzip -mx9 ..\clamwin.zip -r
rem cd ..
rem rd library /s /q 

rem upx all files now
rem call "%UPX_UTIL%" -9 *.* 
rem cd ..\bin
rem call "%UPX_UTIL%" -9 *.* 

rem cd ..\..\..\..\


rem get the latest db files
::call %WGET_UTIL% http://%DB_MIRROR%/main.cvd -N -O "%THISDIR%\Setup\cvd\main.cvd"
::if not "%ERRORLEVEL%"=="0" goto ERROR
::call %WGET_UTIL% http://%DB_MIRROR%/daily.cvd -N -O "%THISDIR%\Setup\cvd\daily.cvd"
::if not "%ERRORLEVEL%"=="0" goto ERROR
::call %WGET_UTIL% http://%DB_MIRROR%/bytecode.cvd -N -O "%THISDIR%\Setup\cvd\bytecode.cvd"
::if not "%ERRORLEVEL%"=="0" goto ERROR


call "%ISTOOLDIR%\Compil32.exe" /cc "%THISDIR%\Setup\Setup-nodb.iss"
if not "%ERRORLEVEL%"=="0" goto ERROR
rem move nodb setup to -nodb file
del "%THISDIR%\Setup\Output\Setup-nodb.exe"
move "%THISDIR%\Setup\Output\mysetup.exe" "%THISDIR%\Setup\Output\Setup-nodb.exe"
if not "%ERRORLEVEL%"=="0" goto ERROR


call "%ISTOOLDIR%\Compil32.exe" /cc "%THISDIR%\Setup\Setup.iss"
if not "%ERRORLEVEL%"=="0" goto ERROR

goto END

:ERROR
@echo an error occured
pause

:end


