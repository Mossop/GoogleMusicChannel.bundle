PREFIX = '/music/gmusic'

def Start():
    Log.Info("Start called for %s" % Prefs["username"])

def ValidatePrefs():
    Log.Info("Validate called for %s" % Prefs["username"])

@handler(PREFIX, L("title"), thumb="googlemusic.png")
def Main():
    oc = ObjectContainer(title1=L("title"), content=ContainerContent.Mixed)
    return oc
