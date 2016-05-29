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
logger = logging.getLogger("googlemusicchannel.music")

import pathset

import re
import urllib

from genre import Genre
from library import Library
from globals import *

DB_SCHEMA = 111

def load_from(data):
    if data["schema"] != DB_SCHEMA:
        return

    for d in data["genres"]:
        Genre.unpickle(d)
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
        genres = libraries[0].client.get_genres(parent)
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
        "libraries": map(lambda l: l.pickle(), libraries.values())
    }

def get_library(id):
    return globals.libraries[id]

def get_genre(name):
    return globals.genre_by_name[name]
