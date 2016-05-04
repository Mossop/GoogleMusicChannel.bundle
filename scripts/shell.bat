@echo off

cd %~dp0\..
setlocal
set PYTHONPATH=Contents\Libraries\Shared;C:\Program Files (x86)\Plex\Plex Media Server\DLLs
"C:\Program Files (x86)\Plex\Plex Media Server\PlexScriptHost.exe"
