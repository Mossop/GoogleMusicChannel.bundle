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
