@echo off

cd %~dp0\..
setlocal

set PYTHONPATH=%~dp0\..\Contents\Libraries\Shared
"C:\Program Files (x86)\Plex\Plex Media Server\PlexScriptHost.exe"
