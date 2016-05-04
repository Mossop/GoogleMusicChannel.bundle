from gmusicapi import Mobileclient

PREFIX = '/music/gmusic'

client = Mobileclient()

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
