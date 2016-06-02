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

from urlparse import urlsplit, parse_qs

import pathset  # NOQA

from genre import Genre
from track import Track
from album import Album, LibraryAlbum
from artist import Artist, LibraryArtist
from library import Library
from globals import *

logger = logging.getLogger("googlemusicchannel.music")

DB_SCHEMA = 2


def load_from(data):
    if data["schema"] != DB_SCHEMA:
        return

    for d in data["genres"]:
        Genre.unpickle(d)
    for d in data["artists"]:
        Artist.unpickle(d)
    for d in data["albums"]:
        Album.unpickle(d)
    for d in data["tracks"]:
        Track.unpickle(d)
    for l in data["libraries"]:
        Library.unpickle(l)


def set_credentials(username, password):
    if len(libraries) == 1:
        lib = libraries.values()[0]

        if lib.username == username and lib.password == password:
            return

        lib.logout()
        libraries.clear()

    if username is None or password is None:
        return

    Library(username, password)


def refresh():
    logger.info("Updating genres.")

    g_root = []

    def find_genres(parent, list):
        genres = libraries.values()[0].client.get_genres(parent)
        for data in genres:
            genre = Genre(data)
            list.append(genre)
            genre_by_id[data["id"]] = genre
            genre_by_name[genre.name] = genre

            find_genres(data["id"], genre.children)

    find_genres(None, g_root)
    root_genres = g_root

    logger.info("Found %d genres." % (len(genre_by_id)))

    for library in libraries.values():
        library.update()

    # As part of the update process some unused records are created
    logger.debug("Purging unreferenced records.")
    tracks = set()
    albums = set()
    artists = set()
    for library in libraries.values():
        for track in library.get_tracks():
            tracks.add(track.track.id)
            albums.add(track.album.id)
            artists.add(track.artist.id)

    def purge(list, used, name):
        unwanted = set(list.keys()) - used
        if len(unwanted) == 0:
            return
        for item in unwanted:
            del list[item]
        logger.debug("Purged %d unreferenced %s." % (len(unwanted), name))

    purge(track_by_id, tracks, "tracks")
    purge(album_by_id, albums, "albums")
    purge(artist_by_id, artists, "artists")

    return {
        "schema": DB_SCHEMA,
        "genres": map(lambda g: g.pickle(), root_genres),
        "libraries": map(lambda l: l.pickle(), libraries.values()),
        "tracks": map(lambda t: t.pickle(), track_by_id.values()),
        "albums": map(lambda a: a.pickle(), album_by_id.values()),
        "artists": map(lambda a: a.pickle(), artist_by_id.values())
    }


def get_library(id):
    return libraries[int(id)]


def get_genre(name):
    return genre_by_name[name]


def get_artist(id, library = None):
    artist = artist_by_id[id]
    if library is not None:
        return LibraryArtist(library, artist)
    return artist


def get_album(id, library = None):
    album = album_by_id[id]
    if library is not None:
        return LibraryAlbum(library, album)
    return album


def get_item_for_url(url):
    if url[0:len(base_path)] != base_path:
        raise Exception("Failed to match url '%s'" % url)

    parts = urlsplit(url[len(base_path):])
    id = parts.path
    args = parse_qs(parts.query)

    library = None
    if "u" in args:
        lid = int(args["u"][0])
        if lid not in libraries:
            raise Exception("Couldn't find a library for id '%d'" % lid)
        library = get_library(lid)
        if id in library.track_by_id:
            return library.track_by_id[id]

    for library in libraries.values():
        if id in library.track_by_id:
            return library.track_by_id[id]

    if id in artist_by_id:
        return get_artist(id, library)
    if id in album_by_id:
        return get_album(id, library)
    if id in track_by_id:
        return track_by_id[id]

    raise Exception("ID '%s' didn't match any known item." % id)


# There is a bug in the Plex API that causes albums to return as <Object>
# instead of <Directory> which breaks many clients.
# http://forums.plex.tv/discussion/217791/albumobjects-dont-display-in-the-web-interface
def bugfix_album(cls):
    cls._model_class._template.xml_tag = "Directory"
