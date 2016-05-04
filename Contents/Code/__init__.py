# Copyright 2016 Dave Townsend
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from gmusicapi import Mobileclient

PREFIX = '/music/gmusic'

class LogHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        self.format(record)

        message = record["message"]

        if record["levelname"] == "DEBUG":
            Log.Debug(message)
        if record["levelname"] == "INFO":
            Log.Info(message)
        if record["levelname"] == "WARNING":
            Log.Warn(message)
        if record["levelname"] == "ERROR":
            Log.Error(message)
        if record["levelname"] == "CRITICAL":
            Log.Critical(message)


logger = logging.getLogger("gmusicapi")
logger.addHandler(LogHandler())

client = Mobileclient(False, False, True)

def login():
    if Prefs["username"] is None or Prefs["password"] is None:
        return
    if not client.login(Prefs["username"], Prefs["password"], Mobileclient.FROM_MAC_ADDRESS):
        Log.Error("Failed to log in.")
    login()

def Start():
    Log.Debug("Start called for %s" % Prefs["username"])

def ValidatePrefs():
    Log.Debug("Validate called for %s" % Prefs["username"])
    if client.is_authenticated():
        client.logout()
    login()

@handler(PREFIX, L("title"), thumb="googlemusic.png")
def Main():
    oc = ObjectContainer(title1=L("title"), content=ContainerContent.Mixed)
    return oc
