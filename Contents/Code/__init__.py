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

import library

PREFIX = '/music/gmusic'
SOURCE = "Google Music"
DB_NAME = "pickles"

def smart_sort(list):
    def simplify(s):
        s = s.lower()
        if s[0:4] == "the ":
            return s[4:]
        return s

    return sorted(list, lambda a, b: cmp(a, b), lambda o: simplify(o.name))

class LogHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        message = self.format(record)

        if record.levelname == "DEBUG":
            Log.Debug(message)
        if record.levelname == "INFO":
            Log.Info(message)
        if record.levelname == "WARNING":
            Log.Warn(message)
        if record.levelname == "ERROR":
            Log.Error(message)
        if record.levelname == "CRITICAL":
            Log.Critical(message)

lhandler = LogHandler()
logger = logging.getLogger("gmusicapi")
logger.addHandler(lhandler)
logger.setLevel(logging.WARNING)
logger = logging.getLogger("googlemusicchannel")
logger.addHandler(lhandler)
logger.setLevel(logging.DEBUG)

logger = logging.getLogger("googlemusicchannel.channel")

def refresh():
    data = library.refresh()
    Data.SaveObject(DB_NAME, data)

    Thread.CreateTimer(60 * 10, refresh)

def login():
    library.set_credentials(Prefs["username"], Prefs["password"])

def Start():
    logger.debug("Start called for %s" % (Prefs["username"]))
    if Data.Exists(DB_NAME):
        try:
            data = Data.LoadObject(DB_NAME)
            library.load_from(data)
        except:
            logger.exception("Failed to load initial data.")

    login()

    Thread.Create(refresh)

    ObjectContainer.title1 = L("title")
    Plugin.AddViewGroup("artist_list", viewMode="InfoList", mediaType="artists", thumb=True)
    Plugin.AddViewGroup("album_list", viewMode="Albums", mediaType="albums", thumb=True)
    Plugin.AddViewGroup("track_list", viewMode="Songs", mediaType="songs", thumb=True)

def ValidatePrefs():
    logger.debug("Validate called for %s" % Prefs["username"])
    login()

@handler(PREFIX, L("title"), thumb="googlemusic.png")
def Main():
    oc = ObjectContainer(content=ContainerContent.Mixed)

    oc.add(DirectoryObject(
        key = Callback(Artists),
        title = L("artists")
    ))

    oc.add(DirectoryObject(
        key = Callback(Albums),
        title = L("albums")
    ))

    oc.add(DirectoryObject(
        key = Callback(Songs),
        title = L("songs")
    ))

    return oc

@route(PREFIX + "/artists")
def Artists():
    oc = ObjectContainer(
        title2=L("artists"),
        content=ContainerContent.Artists,
        view_group="artist_list"
    )

    artists = library.get_artists()
    for artist in smart_sort(artists):
        oc.add(ArtistObject(
            key = Callback(Artist, artistId=artist.id),
            rating_key = artist.id,
            title = artist.name,
            art = artist.art,
            thumb = artist.thumb
        ))

    return oc

def track_object(track):
    return TrackObject(
        url = track.url,
        title = track.title,
        index = track.index,
        artist = track.album.artist.name,
        album = track.album.name,
        duration = track.duration,
        thumb = track.thumb
    )

def full_album_object(album):
    return AlbumObject(
        url = album.url,
        title = album.name,
        art = album.thumb,
        thumb = album.thumb,
        artist = album.artist.name,
        track_count = len(album.tracks)
    )

def fake_album_object(album):
    return DirectoryObject(
        key = Callback(Album, albumId = album.id),
        title = album.name,
        art = album.thumb,
        thumb = album.thumb
    )

@route(PREFIX + "/albums")
def Albums():
    oc = ObjectContainer(
        title2=L("albums"),
        content=ContainerContent.Playlists,
        view_group="album_list"
    )

    albums = library.get_albums()
    for album in smart_sort(albums):
        oc.add(full_album_object(album))

    return oc

@route(PREFIX + "/songs")
def Songs():
    oc = ObjectContainer(
        title2=L("songs"),
        content=ContainerContent.Tracks,
        view_group="track_list"
    )

    tracks = library.get_tracks()
    for track in tracks:
        oc.add(track_object(track))

    return oc

@route(PREFIX + "/artist")
def Artist(artistId):
    artist = library.get_artist(artistId)

    oc = ObjectContainer(
        title2=artist.name,
        content=ContainerContent.Albums,
        view_group="album_list",
        art=artist.thumb
    )

    for album in artist.albums:
        oc.add(fake_album_object(album))

    return oc

@route(PREFIX + "/album")
def Album(albumId):
    album = library.get_album(albumId)

    oc = ObjectContainer(
        title2=album.name,
        content=ContainerContent.Tracks,
        view_group="track_list",
        art=album.thumb
    )

    for track in sorted(album.tracks, library.track_cmp):
        oc.add(track_object(track))

    return oc
