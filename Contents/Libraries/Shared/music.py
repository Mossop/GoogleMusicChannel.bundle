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

import hashlib
import re
from base64 import b64encode
from uuid import uuid4
import logging
import urllib
import sys
import platform
import os

arch = "%s-%s" % (sys.platform, platform.architecture()[0])
platfom_path = os.path.abspath(os.path.join(os.path.dirname(__file__), arch))
sys.path.append(platfom_path)

from gmusicapi import Mobileclient

DB_SCHEMA = 2

logger = logging.getLogger("googlemusicchannel.library")

def urlize(string):
    return re.sub(r'[\W-]+', "_", string)

def hash(data):
    return b64encode(hashlib.sha256(data).digest())

def get_album_hash(artist, name):
    # We use this has as the ID as it should be reasonably unique and freely
    # available in both track and album data
    return hash("%s:%s" % (artist, name))

def track_cmp(a, b):
    if a.data["discNumber"] != b.data["discNumber"]:
        return a.data["discNumber"] - b.data["discNumber"]
    return a.data["trackNumber"] - b.data["trackNumber"]

def locked(func):
    def inner(*args, **kwargs):
        #Thread.AcquireLock("library-lock")
        #try:
            return func(*args, **kwargs)
        #finally:
        #    Thread.ReleaseLock("library-lock")
    return inner

# These are objects that exist in the global library for all users. Objects that
# are manually uploaded/created by individuals don't appear here, look in the
# Library objects for those.

root_genres = []
genre_by_id = {}
genre_by_name = {}

def replace_genres(root, by_id, by_name):
    root_genres = root
    genre_by_id = by_id
    genre_by_name = by_name

# We need at least one Library in order to have a valid client
class Library(object):
    id = None

    username = None
    password = None

    client = None
    device_id = None

    # Real objects in the music store. These can contain more than those just
    # considered as a part of the user's library.
    artist_by_id = None
    album_by_id = None
    track_by_nid = None

    # Where there isn't a real artist object this holds fake artist entries
    artist_by_name = None

    # Where there isn't a real album object this holds fake album entries
    album_by_name = None

    # These are all the tracks in the user's library. The key is the track's
    # library ID, not the store ID
    track_by_id = None

    def __init__(self, username, password):
        self.id = 0

        self.username = username
        self.password = password

        self.clear()

        self.artist_by_id[""] = Artist(self, {
            "name": "Various Artists"
        })

        self.client = Mobileclient(False, False, True)

        if self.device_id is None:
            device_id = Mobileclient.FROM_MAC_ADDRESS
        else:
            device_id = self.device_id

        try:
            self.client.login(username, password, device_id)
        except:
            logger.exception("Client couldn't log in.")

    # Because of threading shenanigans we have to manually pickle classes
    def pickle(self):
        return {
            "username": self.username,
            "password": self.password,
            "device_id": self.device_id,
        }

    def logout(self):
        self.client.logout()

    @classmethod
    def unpickle(cls, data):
        try:
            library = cls(data["username"], data["password"])
            library.device_id = data["device_id"]

            library.clear()

            return library
        except:
            logger.exception("Failed to load data.")
            return None

    def get_device_id(self):
        if self.device_id is not None:
            return self.device_id

        devices = self.client.get_registered_devices()
        for device in devices:
            if device["type"] == "ANDROID":
                self.device_id = device["id"][2:]
                return self.device_id
            if device["type"] == "IOS":
                self.device_id = device["id"]
                return self.device_id

        raise Exception("Unable to find a valid device ID")

    def find_artist(self, artistId, expectedName):
        if artistId in self.artist_by_id:
            artist = self.artist_by_id[artistId]
        else:
            artist_data = self.client.get_artist_info(artistId, False, 0, 0)
            artist = Artist(self, artist_data)
            self.artist_by_id[artistId] = artist

        if artist.name == expectedName:
            return artist
        return None

    def find_album(self, albumId, expectedName):
        if albumId in self.album_by_id:
            album = self.album_by_id[albumId]
        else:
            album_data = self.client.get_album_info(albumId, False)
            album = Album(self, album_data)
            self.album_by_id[albumId] = album

            for artistId in album_data["artistId"]:
                artist = self.find_artist(artistId, album_data["albumArtist"])
                if artist is not None:
                    album.artistId = artistId
                    break

            if album.artistId is None:
                logger.warn("Couldn't find an artist %s for %s" % (album_data["albumArtist"], album.name))

        if album.name != expectedName:
            logger.warning("Failed to find correct album %s" % (expectedName))
            return

    def add_track(self, track_data):
        id = track_data["id"]

        if "nid" not in track_data:
            return

        if "nid" in track_data and track_data["nid"] in self.track_by_nid:
            track = self.track_by_nid[track_data["nid"]]
        else:
            track = Track(self, track_data)
            if "nid" in track_data:
                self.track_by_nid[track_data["nid"]] = track

        self.track_by_id[id] = track

        self.find_album(track_data["albumId"], track_data["album"])

#        album_hash = get_album_hash(track_data["albumArtist"], track_data["album"])
#        album = self.albums.get(album_hash)#

#        if album is None:
#            album = Album(self, {
#                "albumArtist": track_data["albumArtist"],
#                "name": track_data["album"]
#            })#

#            artist = self.artists.get(track_data["albumArtist"])
#            if artist is None:
#                artist = Artist(self, {
#                    "name": track_data["albumArtist"]
#                })#

#            album.artist = artist
#            artist.albums.add(album)#

#        album.tracks.add(track)
#        track.album = album#

#        # Attempt to get full album data if needed
#        if "albumId" in track_data:
#            album.update_id(track_data["albumId"])#

#        # Add whatever album art we have
#        if "albumArtRef" in track_data:
#            album.art.add(track_data["albumArtRef"][0]["url"])#

#        # If the main artist is the album artist then do the same for the
#        # artist
#        if track_data["albumArtist"] == track_data["artist"]:
#            if "artistId" in track_data and len(track_data["artistId"]) > 0:
#                album.artist.update_id(track_data["artistId"][0])#

#            if "artistArtRef" in track_data:
#                album.artist.art.add(track_data["artistArtRef"][0]["url"])#

    def remove_track(self, id):
        del self.tracks[id]

    def clear(self):
        self.artist_by_id = {}
        self.album_by_id = {}
        self.track_by_nid = {}
        
        self.artist_by_name = {}
        self.album_by_name = {}
        self.track_by_id = {}

    def update(self):
        logger.info("Starting library update.")

        try:
            if not self.client.is_authenticated:
                logger.error("Client isn't authenticated.")
                return

            data = self.client.get_all_songs(False, False)
            logger.info("Found %d tracks in the cloud library." % (len(data)))

            # Convert to a dict with id as key
            tracks = dict(map(lambda s: (s["id"], s), data))

            currentset = set(self.track_by_id.keys())
            newset = set(tracks.keys())

            deletedset = currentset - newset
            addedset = newset - currentset
            modifiedset = currentset & newset

            logger.info("Adding %d new tracks." % (len(addedset)))

            for id in addedset:
                self.add_track(tracks[id])

            logger.info("Removing %d old tracks." % (len(deletedset)))

            for id in deletedset:
                self.remove_track(id)

            logger.info("Updating %d existing tracks." % (len(modifiedset)))

            for id in modifiedset:
                current = self.tracks[id]
                new = tracks[id]

                self.remove_track(id)
                self.add_track(new)

            # TODO purge empty albums
            # TODO purge empty artists
            # TODO update genres

            albums = set(map(lambda t: t.album, self.track_by_id.values()))
            artists = set(map(lambda a: a.artist, albums))

            logger.info("Update complete, library has %d artists, %d albums and %d tracks." %
                     (len(artists), len(albums), len(self.track_by_id)))
        except:
            logger.exception("Failed to update library.")

    def get_item(self, id):
        if id[0] == "A":
            return self.get_artist(urllib.unquote(id[1:]))
        if id[0] == "B":
            return self.get_album(id)
        if id[0] == "F":
            return self.get_album(id[1:])
        return self.get_track(id)

    def get_artists(self):
        return set(map(lambda t: t.album.artist, self.get_tracks()))

    def get_artist(self, id):
        return self.artist_by_id[id]

    def get_albums(self):
        return set(map(lambda t: t.album, self.get_tracks()))

    def get_album(self, id):
        return self.album_by_id[id]

    def get_tracks(self):
        return self.track_by_id.values()

    def get_track(self, any_id):
        if any_id in self.track_by_nid:
            return self.track_by_nid[any_id]
        if any_id in self.track_by_id:
            return self.track_by_id[any_id]
        return None

    def get_genres(self):
        genres = set(map(lambda t: t.genre, self.get_tracks()))
        return map(lambda g: self.genre_by_name[g], genres)

    def get_genre(self, name):
        return self.genre_by_name[name]

class FakeGenre(object):
    name = None
    examples = None

    def __init__(self, name):
        self.name = name
        self.examples = []

    @property
    def thumb(self):
        tracks = filter(lambda t: t.album.thumb is not None, self.examples)
        if len(tracks) == 0:
            return None
        return tracks[0].album.thumb

class Genre(object):
    data = None
    library = None
    children = None

    def __init__(self, data):
        self.data = data
        self.children = []

    # Public API
    @property
    def name(self):
        return self.data["name"]

    @property
    def thumb(self):
        if "images" in self.data and len(self.data["images"]) > 0:
            return self.data["images"][0]["url"]
        return None

class Artist(object):
    library = None
    data = None

    def __init__(self, library, data):
        self.library = library
        self.data = data

    # Public API
    @property
    def name(self):
        return self.data["name"]

    @property
    def thumb(self):
        return None

    @property
    def url(self):
        id = "A%s" % urllib.quote(self.name)

        param = urlize("%s" % (self.name))

        return "https://play.google.com/music/m/%s?t=%s&u=%d" % (id, param, self.library.id)

class Album(object):
    library = None
    data = None
    artistId = None

    def __init__(self, library, data):
        self.library = library
        self.data = data

    # Public API
    @property
    def name(self):
        return self.data["name"]

    @property
    def artist(self):
        if self.artistId is not None:
            return self.library.artist_by_id[self.artistId]
        return None
    
    @property
    def thumb(self):
        return self.data["albumArtRef"]

    @property
    def url(self):
        param = urlize("%s - %s" % (self.name, self.artist.name))

        return "https://play.google.com/music/m/%s?t=%s&u=%d" % (self.data["albumId"], param, self.library.id)

class Track(object):
    library = None
    data = None

    def __init__(self, library, data):
        self.library = library
        self.data = data

        if data["genre"] in genre_by_name:
            genre = genre_by_name[data["genre"]]
            if isinstance(genre, FakeGenre):
                genre.examples.append(self)
        else:
            genre = FakeGenre(data["genre"])
            genre.examples.append(self)
            genre_by_name[data["genre"]] = genre
            root_genres.append(genre)

    # Public API
    @property
    def id(self):
        if "nid" in self.data:
            return self.data["nid"]
        return self.data["id"]

    @property
    def lid(self):
        if "id" in self.data:
            return self.data["id"]
        return None

    @property
    def nid(self):
        if "nid" in self.data:
            return self.data["nid"]
        return None

    @property
    def album(self):
        return self.library.album_by_id[self.data["albumId"]]

    @property
    def genre(self):
        return genre_by_name[self.data["genre"]]

    @property
    def title(self):
        return self.data["title"]

    @property
    def thumb(self):
        return self.album.thumb

    @property
    def duration(self):
        return int(self.data["durationMillis"])

    @property
    def url(self):
        if "nid" in self.data:
            id = self.data["nid"]
        else:
            id = self.data["id"]
        param = urlize("%s - %s" % (self.title, self.album.artist.name))

        return "https://play.google.com/music/m/%s?t=%s&u=%d" % (id, param, self.library.id)

main = None

def load_from(data):
    global main

    if data["schema"] != DB_SCHEMA:
        return

def set_credentials(username, password):
    global main

    if main is not None:
        if main.username == username and main.password == password:
            return

        main.logout()
        main = None

    if username is None or password is None:
        return

    main = Library(username, password)

def refresh():
    library = main

    logger.info("Updating genres.")

    g_root = []
    g_by_id = {}
    g_by_name = {}

    def find_genres(parent, list):
        genres = library.client.get_genres(parent)
        for data in genres:
            genre = Genre(data)
            list.append(genre)
            g_by_id[data["id"]] = genre
            g_by_name[genre.name] = genre

            find_genres(data["id"], genre.children)

    find_genres(None, g_root)
    replace_genres(g_root, g_by_id, g_by_name)

    logger.info("Found %d genres." % (len(g_by_id)))

    main.update()

def get_library(id):
    return main
