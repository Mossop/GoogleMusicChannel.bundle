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

import music

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

music.bugfix_album(AlbumObject)

def url_or_default(url, default):
    if url is not None:
        return url
    return default

def refresh():
    data = music.refresh()
    Data.SaveObject(DB_NAME, data)

    Thread.CreateTimer(60 * 10, refresh)

def login():
    music.set_credentials(Prefs["username"], Prefs["password"])

def Start():
    logger.debug("Start called for %s" % (Prefs["username"]))
    if Data.Exists(DB_NAME):
        try:
            data = Data.LoadObject(DB_NAME)
            music.load_from(data)
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
        key = Callback(Library, lid=0),
        title = L("library"),
        thumb = R("album.png")
    ))

    return oc

@route(PREFIX + "/library/{lid}")
def Library(lid):
    oc = ObjectContainer(content=ContainerContent.Mixed, title2=L("library"))

    oc.add(DirectoryObject(
        key = Callback(LibraryArtists, lid=lid),
        title = L("library_artists"),
        thumb = R("artist.png")
    ))

    oc.add(DirectoryObject(
        key = Callback(LibraryAlbums, lid=lid),
        title = L("library_albums"),
        thumb = R("album.png")
    ))

    oc.add(DirectoryObject(
        key = Callback(LibrarySongs, lid=lid),
        title = L("library_songs"),
        thumb = R("playlist.png")
    ))

    oc.add(DirectoryObject(
        key = Callback(LibraryGenres, lid=lid),
        title = L("library_genres"),
        thumb = R("playlist.png")
    ))

    return oc


@route(PREFIX + "/library/{lid}/artists")
def LibraryArtists(lid):
    library = music.get_library(lid)

    oc = ObjectContainer(
        title2=L("library_artists"),
        content=ContainerContent.Artists,
        view_group="artist_list",
    )

    artists = library.get_artists()
    for artist in smart_sort(artists):
        oc.add(ArtistObject(
            key = Callback(LibraryArtist, lid=lid, artistId=artist.id),
            rating_key = "ARTIST_%s" % artist.id, # Necessary because Various Artists has an empty id
            title = artist.name,
            thumb = url_or_default(artist.thumb, R("playlist.png"))
        ))

    return oc

def track_object(track):
    return TrackObject(
        url = track.url,
        title = track.title,
        artist = track.artist.name,
        album = track.album.name,
        duration = track.duration,
        thumb = url_or_default(track.thumb, R("track.png"))
    )

@route(PREFIX + "/library/{lid}/albums")
def LibraryAlbums(lid):
    library = music.get_library(lid)

    oc = ObjectContainer(
        title2=L("library_albums"),
        content=ContainerContent.Playlists,
        view_group="album_list"
    )

    albums = library.get_albums()
    for album in smart_sort(albums):
        oc.add(AlbumObject(
            key = Callback(LibraryAlbum, lid=library.id, albumId=album.id),
            rating_key = album.id,
            title = album.name,
            thumb = url_or_default(album.thumb, R("album.png")),
            artist = album.artist.name
        ))

    return oc

@route(PREFIX + "/library/{lid}/songs")
def LibrarySongs(lid):
    library = music.get_library(lid)

    oc = ObjectContainer(
        title2=L("library_songs"),
        content=ContainerContent.Tracks,
        view_group="track_list"
    )

    tracks = library.get_tracks()
    for track in tracks:
        oc.add(track_object(track))

    return oc

@route(PREFIX + "/library/{lid}/genres")
def LibraryGenres(lid):
    library = music.get_library(lid)

    oc = ObjectContainer(
        title2=L("library_genres"),
        content=ContainerContent.Genres
    )

    genres = library.get_genres()
    for genre in genres:
        oc.add(DirectoryObject(
            key = Callback(LibraryGenreTracks, genreName = genre.name, lid = lid),
            title = genre.name,
            thumb = genre.thumb
        ))

    return oc

@route(PREFIX + "/library/{lid}/genre/{genreName}")
def LibraryGenreTracks(lid, genreName):
    library = music.get_library(lid)
    genre = music.get_genre(genreName)

    oc = ObjectContainer(
        title2=genre.name,
        content=ContainerContent.Tracks,
    )

    tracks = library.get_tracks_in_genre(genre)
    for track in tracks:
        oc.add(track_object(track))

    return oc

@route(PREFIX + "/library/{lid}/artist/{artistId}")
def LibraryArtist(lid, artistId):
    # Plex ignores empty strings
    if artistId is None:
        artistId = ""

    library = music.get_library(lid)
    artist = music.get_artist(artistId)
    albums = library.get_albums_by_artist(artist)

    oc = ObjectContainer(
        title2=artist.name,
        content=ContainerContent.Albums,
        view_group="album_list"
    )

    for album in albums:
        oc.add(AlbumObject(
            key = Callback(LibraryAlbum, lid=library.id, albumId=album.id),
            rating_key = album.id,
            title = album.name,
            thumb = url_or_default(album.thumb, R("album.png")),
            artist = album.artist.name
        ))

    return oc

@route(PREFIX + "/library/{lid}/album/{albumId}")
def LibraryAlbum(lid, albumId):
    library = music.get_library(lid)
    album = music.get_album(albumId)
    tracks = library.get_tracks_in_album(album)

    oc = ObjectContainer(
        title2=album.name,
        content=ContainerContent.Tracks,
        view_group="track_list",
    )

    for track in tracks:
        oc.add(track_object(track))

    logger.debug(XML.StringFromElement(music.to_xml(oc)))
    return oc
