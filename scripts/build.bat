@echo off

cd %~dp0\..
setlocal

set DISTUTILS_USE_SDK=1
set MSSdk=1

python -c "import sys; import platform; print(sys.platform + \"-\" + platform.architecture()[0])" >.platform
set /p arch=<.platform
del .platform

rmdir /s /q Contents\Libraries\Shared\%arch%
mkdir Contents\Libraries\Shared\%arch%
rmdir /s /q Contents\Libraries\Shared\shared
mkdir Contents\Libraries\Shared\shared

REM Plex's Python instance is built with a different compiler than the default
REM so we have to rebuild everything from source to match. I know.
set LIB=%~dp0\..\resources\openssl-win32-2015\lib;%LIB%
set INCLUDE=%~dp0\..\resources\openssl-win32-2015\include;%INCLUDE%
python -m pip install --no-deps --no-binary :all: -t Contents\Libraries\Shared\%arch% -r platform_requirements.txt
python -m pip install --no-deps --no-binary :all: -t Contents\Libraries\Shared\shared -r requirements.txt

REM For some reason without this protobuf is broken as a module
echo "" >Contents\Libraries\Shared\shared\google\__init__.py
