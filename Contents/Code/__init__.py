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
    return Library(0)
#    oc = ObjectContainer(content=ContainerContent.Mixed)
#
#    oc.add(DirectoryObject(
#        key=Callback(Library, libraryId=0),
#        title=L("library"),
#        thumb=R("library.png")
#    ))
#
#    return oc


@route(PREFIX + "/glibrary")
def Library(libraryId):
    oc = ObjectContainer(content=ContainerContent.Mixed, title2=L("library"))

    oc.add(DirectoryObject(
        key=Callback(LibraryPlaylists, libraryId=libraryId),
        title=L("library_playlists"),
        thumb=R("playlist.png")
    ))

    oc.add(DirectoryObject(
        key=Callback(LibraryArtists, libraryId=libraryId),
        title=L("library_artists"),
        thumb=R("artist.png")
    ))

    oc.add(DirectoryObject(
        key=Callback(LibraryAlbums, libraryId=libraryId),
        title=L("library_albums"),
        thumb=R("album.png")
    ))

    oc.add(DirectoryObject(
        key=Callback(LibrarySongs, libraryId=libraryId),
        title=L("library_songs"),
        thumb=R("track.png")
    ))

    oc.add(DirectoryObject(
        key=Callback(LibraryGenres, libraryId=libraryId),
        title=L("library_genres"),
        thumb=R("genre.png")
    ))

    return oc


@route(PREFIX + "/glibrary/playlists")
def LibraryPlaylists(libraryId):
    oc = ObjectContainer(
        title2=L("library_playlists"),
        content=ContainerContent.Artists,
        view_group="artist_list",
        art=R("playlist.png")
    )

    library = music.get_library(libraryId)
    playlists = library.get_playlists()
    for playlist in smart_sort(playlists):
        oc.add(PlaylistObject(
            key=Callback(LibraryPlaylist, libraryId=libraryId, playlistId=playlist.id),
            title=playlist.name,
            thumb=R("playlist.png")
        ))

    return oc


@route(PREFIX + "/glibrary/playlist")
def LibraryPlaylist(libraryId, playlistId):
    library = music.get_library(libraryId)
    playlist = library.get_playlist(playlistId)

    oc = ObjectContainer(
        title2=playlist.name,
        content=ContainerContent.Tracks,
        view_group="track_list",
        art=R("playlist.png")
    )

    for track in playlist.tracks:
        oc.add(track_object(track))

    return oc


@route(PREFIX + "/glibrary/artists")
def LibraryArtists(libraryId):
    oc = ObjectContainer(
        title2=L("library_artists"),
        content=ContainerContent.Artists,
        view_group="artist_list",
        art=R("artist.png")
    )

    library = music.get_library(libraryId)
    artists = library.get_artists()
    for artist in smart_sort(artists):
        oc.add(ArtistObject(
            key=Callback(LibraryArtist, libraryId=libraryId, artistId=artist.id),
            rating_key=artist.id,
            title=artist.name,
            thumb=url_or_default(artist.thumb, R("artist.png"))
        ))

    return oc


@route(PREFIX + "/glibrary/albums")
def LibraryAlbums(libraryId):
    oc = ObjectContainer(
        title2=L("library_albums"),
        content=ContainerContent.Playlists,
        view_group="album_list",
        art=R("album.png")
    )

    library = music.get_library(libraryId)
    albums = library.get_albums()
    for album in smart_sort(albums):
        oc.add(AlbumObject(
            key=Callback(Album, libraryId=libraryId, albumId=album.id),
            rating_key=album.id,
            title=album.name,
            thumb=album.thumb,
            artist=album.artist.name
        ))

    return oc


@route(PREFIX + "/glibrary/songs")
def LibrarySongs(libraryId):
    oc = ObjectContainer(
        title2=L("library_songs"),
        content=ContainerContent.Tracks,
        view_group="track_list",
        art=R("track.png")
    )

    library = music.get_library(libraryId)
    tracks = library.get_tracks()
    for track in tracks:
        oc.add(track_object(track))

    return oc


@route(PREFIX + "/glibrary/genres")
def LibraryGenres(libraryId):
    oc = ObjectContainer(
        title2=L("library_genres"),
        content=ContainerContent.Genres,
        art=R("genre.png")
    )

    library = music.get_library(libraryId)
    genres = library.get_genres()
    for genre in genres:
        oc.add(DirectoryObject(
            key=Callback(GenreTracks, libraryId=libraryId, genreName=genre.name),
            title=genre.name,
            thumb=url_or_default(genre.thumb, R("genre.png"))
        ))

    return oc


@route(PREFIX + "/glibrary/genre")
def GenreTracks(libraryId, genreName):
    library = music.get_library(libraryId)
    genre = music.get_genre(genreName)

    oc = ObjectContainer(
        title2=genre.name,
        content=ContainerContent.Tracks,
        art=url_or_default(genre.thumb, R("genre.png"))
    )

    tracks = library.get_tracks_in_genre(genre)
    for track in tracks:
        oc.add(track_object(track))

    return oc


@route(PREFIX + "/glibrary/artist")
def LibraryArtist(libraryId, artistId):
    library = music.get_library(libraryId)
    artist = music.get_artist(artistId, library)

    oc = ObjectContainer(
        title2=artist.name,
        content=ContainerContent.Albums,
        view_group="album_list",
        art=url_or_default(artist.thumb, R("artist.png"))
    )

    for album in smart_sort(artist.albums):
        oc.add(AlbumObject(
            key=Callback(Album, libraryId=libraryId, albumId=album.id),
            rating_key=album.id,
            title=album.name,
            thumb=album.thumb,
            artist=album.artist.name
        ))

    return oc


@route(PREFIX + "/glibrary/album")
def Album(libraryId, albumId):
    library = music.get_library(libraryId)
    album = music.get_album(albumId, library)

    oc = ObjectContainer(
        title2=album.name,
        content=ContainerContent.Tracks,
        view_group="track_list",
        art=url_or_default(album.thumb, R("album.png"))
    )

    for track in album.tracks:
        oc.add(track_object(track))

    return oc


def track_object(track):
    return TrackObject(
        url=track.url,
        title=track.title,
        artist=track.artist.name,
        album=track.album.name,
        duration=track.duration,
        thumb=url_or_default(track.thumb, R("track.png"))
    )
