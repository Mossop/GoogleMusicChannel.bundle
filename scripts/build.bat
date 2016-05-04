@echo off

set DISTUTILS_USE_SDK=1
set MSSdk=1

cd %~dp0\..

rmdir /s /q Contents\Libraries
mkdir Contents\Libraries\Shared\lib2to3

REM Override the system lib2to3. See ../resources/README.md
xcopy /s resources\lib2to3 Contents\Libraries\Shared\lib2to3

REM Plex's Python instance is built with a different compiler than the default
REM so we have to rebuild everything from source to match. I know.
set LIB=%~dp0\..\resources\openssl-win32-2015\lib;%LIB%
set INCLUDE=%~dp0\..\resources\openssl-win32-2015\include;%INCLUDE%
python -m pip install --no-binary :all: -t Contents\Libraries\Shared -r requirements.txt

REM For some reason without this protobuf is broken as a module
echo "" >Contents\Libraries\Shared\google\__init__.py
