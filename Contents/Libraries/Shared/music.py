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

DB_SCHEMA = 1

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

    # These are all the tracks in the user's library. The key is the track's
    # library ID, not the store ID
    track_by_id = None

    def __init__(self, username, password):
        self.id = 0

        self.username = username
        self.password = password

        self.clear()

        self.artist_by_id[""] = Artist(self, {
            "name": "Various Artists",
            "artistId": ""
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
            "tracks": map(lambda t: t.pickle(), self.track_by_id.values()),
            "albums": map(lambda a: a.pickle(), self.album_by_id.values()),
            "artists": map(lambda a: a.pickle(), self.artist_by_id.values())
        }

    def logout(self):
        self.client.logout()

    @classmethod
    def unpickle(cls, data):
        try:
            library = cls(data["username"], data["password"])
            library.device_id = data["device_id"]

            library.clear()

            for d in data["tracks"]:
                Track.unpickle(library, d)
            for d in data["albums"]:
                Album.unpickle(library, d)
            for d in data["artists"]:
                Artist.unpickle(library, d)

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

    def add_fake_artist(self, track_data):
        artist = self.get_artist_by_name(track_data["albumArtist"])
        if artist is None:
            artist_data = {
                "artistId": "FA%s" % hash(track_data["albumArtist"]),
                "name": track_data["albumArtist"],
            }

            if "artistArtRef" in track_data:
                artist_data["artistArtRef"] = track_data["artistArtRef"][0]["url"]
            elif "albumArtRef" in track_data:
                artist_data["artistArtRef"] = track_data["albumArtRef"][0]["url"]
            else:
                artist_data["artistArtRef"] = None

            artist = Artist(self, artist_data)
            self.artist_by_id[artist.id] = artist

        return artist

    def find_artist(self, artistId, expectedName):
        if artistId in self.artist_by_id:
            artist = self.artist_by_id[artistId]
        else:
            artist_data = self.client.get_artist_info(artistId, False, 0, 0)
            artist = Artist(self, artist_data)
            self.artist_by_id[artist.id] = artist

        if artist.name == expectedName:
            return artist
        return None

    def add_fake_album(self, track_data):
        album = self.get_album_by_name(track_data["album"])
        if album is None:
            album_data = {
                "albumId": "FB%s" % hash(track_data["album"]),
                "name": track_data["album"]
            }

            if "albumArtRef" in track_data:
                album_data["albumArtRef"] = track_data["artistArtRef"][0]["url"]
            elif "artistArtRef" in track_data:
                album_data["albumArtRef"] = track_data["albumArtRef"][0]["url"]
            else:
                album_data["albumArtRef"] = None

            album = Album(self, album_data)
            self.album_by_id[album.id] = album

            artist = self.add_fake_artist(track_data)

            album.artistId = artist.id

        return album


    def find_album(self, track_data):
        if track_data["albumId"] in self.album_by_id:
            album = self.album_by_id[track_data["albumId"]]
        else:
            album_data = self.client.get_album_info(track_data["albumId"], False)
            album = Album(self, album_data)
            self.album_by_id[album.id] = album

            for artistId in album_data["artistId"]:
                artist = self.find_artist(artistId, album_data["albumArtist"])
                if artist is not None:
                    album.artistId = artistId
                    break

            if album.artistId is None:
                logger.warn("Couldn't find an artist %s for %s" % (album_data["albumArtist"], album.name))
                artist = self.add_fake_artist(track_data)
                album.artistId = artist.id

        if album.name != track_data["album"]:
            logger.warning("Failed to find correct album %s" % (track_data["album"]))
            return None

        return album

    # For tracks that were uploaded to google play. Album and artist IDs are
    # sane. nid field is always present
    def add_track(self, track_data):
        id = track_data["id"]

        if id in self.track_by_id:
            old_track = self.track_by_id[id]
            if old_track.nid is not None:
                del self.track_by_nid[old_track.nid]

        if track_data["nid"] in self.track_by_nid:
            track = self.track_by_nid[track_data["nid"]]
        else:
            track = Track(self, track_data)
            self.track_by_nid[track_data["nid"]] = track

        album = self.find_album(track_data)

        if album is None:
            album = self.add_fake_album(track_data)

        track.albumId = album.id
        self.track_by_id[id] = track

    # For tracks that were uploaded to google play. Album and artist IDs cannot
    # be trusted. nid field is never present
    def add_fake_track(self, track_data):
        id = track_data["id"]

        if id in self.track_by_id:
            old_track = self.track_by_id[id]
            if old_track.nid is not None:
                del self.track_by_nid[old_track.nid]

        track = Track(self, track_data)
        album = self.add_fake_album(track_data)

        track.albumId = album.id
        self.track_by_id[id] = track

    def remove_track(self, id):
        del self.tracks[id]

    def clear(self):
        self.artist_by_id = {}
        self.album_by_id = {}
        self.track_by_nid = {}
        
        self.track_by_id = {}

    def update(self):
        logger.info("Starting library update.")

        try:
            if not self.client.is_authenticated:
                logger.error("Client isn't authenticated.")
                return

            data = self.client.get_all_songs(False, False)
            logger.info("Found %d tracks in the cloud library." % (len(data)))

            track_ids = set(map(lambda s: s["id"], data))

            currentset = set(self.track_by_id.keys())

            deletedset = currentset - track_ids
            addedset = track_ids - currentset
            modifiedset = currentset & track_ids

            logger.info("Adding %d new tracks and updating %d existing tracks." % (len(addedset), len(modifiedset)))

            for track_data in filter(lambda d: "nid" in d, data):
                self.add_track(track_data)

            for track_data in filter(lambda d: "nid" not in d, data):
                self.add_fake_track(track_data)

            logger.info("Removing %d old tracks." % (len(deletedset)))

            for id in deletedset:
                self.remove_track(id)

            albumIds = set(map(lambda t: t.albumId, self.track_by_id.values()))
            removed_albums = set(self.album_by_id.keys()) - albumIds
            for albumId in removed_albums:
                del self.album_by_id[albumId]

            artistIds = set(map(lambda t: t.artistId, self.album_by_id.values()))
            removed_artists = set(self.artist_by_id.keys()) - artistIds
            for artistId in removed_artists:
                del self.artist_by_id[artistId]

            albums = set(map(lambda t: t.album, self.track_by_id.values()))
            artists = set(map(lambda a: a.artist, albums))

            logger.info("Update complete, library has %d artists, %d albums and %d tracks." %
                     (len(artists), len(albums), len(self.track_by_id)))
        except:
            logger.exception("Failed to update library.")

    def get_item(self, id):
        if id[0] == "A":
            return self.get_artist(id)
        if id[0] == "B":
            return self.get_album(id)
        if id[0] == "F":
            if id[1] == "A":
                return self.get_artist(id[2:])
            if id[1] == "B":
                return self.get_album(id[2:])
            return None
        return self.get_track(id)

    def get_artists(self):
        return set(map(lambda t: t.album.artist, self.get_tracks()))

    def get_artist(self, id):
        return self.artist_by_id[id]

    def get_artist_by_name(self, name):
        artists = filter(lambda a: a.name == name, self.get_artists())
        if len(artists) > 0:
            return artists[0]
        return None

    def get_albums(self):
        return set(map(lambda t: t.album, self.get_tracks()))

    def get_album(self, id):
        return self.album_by_id[id]

    def get_album_by_name(self, name):
        albums = filter(lambda a: a.name == name, self.get_albums())
        if len(albums) > 0:
            return albums[0]
        return None

    def get_albums_by_artist(self, artist):
        return filter(lambda a: a.artist == artist, self.get_albums())

    def get_tracks(self):
        return self.track_by_id.values()

    def get_tracks_in_album(self, album):
        return filter(lambda t: t.album == album, self.get_tracks())

    def get_tracks_in_genre(self, genre):
        return filter(lambda t: t.genre == genre, self.get_tracks())

    def get_track(self, any_id):
        if any_id in self.track_by_nid:
            return self.track_by_nid[any_id]
        if any_id in self.track_by_id:
            return self.track_by_id[any_id]
        return None

    def get_genres(self):
        return set(map(lambda t: t.genre, self.get_tracks()))

class FakeGenre(object):
    name = None
    examples = None

    def __init__(self, name):
        self.name = name
        self.examples = []

    def pickle(self):
        return {
            "name": self.name
        }

    @property
    def thumb(self):
        tracks = filter(lambda t: t.album.thumb is not None, self.examples)
        if len(tracks) == 0:
            return None
        return tracks[0].album.thumb

class Genre(object):
    data = None
    children = None

    def __init__(self, data):
        self.data = data
        self.children = []

    @classmethod
    def unpickle(cls, data):
        if "data" in data:
            genre = cls(data["data"])
            genre.children = map(lambda d: Genre.unpickle(d), data["children"])
            genre_by_id[genre.id] = genre
        else:
            genre = FakeGenre(data["name"])
        genre_by_name[genre.name] = genre

        return genre

    def pickle(self):
        return {
            "data": self.data,
            "children": map(lambda g: g.pickle(), self.children)
        }

    # Public API
    @property
    def id(self):
        return self.data["id"]

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

    @classmethod
    def unpickle(cls, library, data):
        artist = cls(library, data["data"])
        library.artist_by_id[artist.id] = artist
        return artist

    def pickle(self):
        return {
            "data": self.data
        }

    # Public API
    @property
    def id(self):
        return self.data["artistId"]

    @property
    def name(self):
        return self.data["name"]

    @property
    def thumb(self):
        if "artistArtRef" in self.data:
            return self.data["artistArtRef"]
        return None

    @property
    def url(self):
        param = urlize("%s" % (self.name))

        return "https://play.google.com/music/m/%s?t=%s&u=%d" % (self.id, param, self.library.id)

class Album(object):
    library = None
    data = None
    artistId = None

    def __init__(self, library, data):
        self.library = library
        self.data = data

    @classmethod
    def unpickle(cls, library, data):
        album = cls(library, data["data"])
        album.artistId = data["artistId"]
        library.album_by_id[album.id] = album
        return album

    def pickle(self):
        return {
            "data": self.data,
            "artistId": self.artistId
        }

    # Public API
    @property
    def id(self):
        return self.data["albumId"]

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

        return "https://play.google.com/music/m/%s?t=%s&u=%d" % (self.id, param, self.library.id)

class Track(object):
    library = None
    data = None
    albumId = None

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

    @classmethod
    def unpickle(cls, library, data):
        track = cls(library, data["data"])
        track.albumId = data["albumId"]
        library.track_by_id[track.lid] = track
        if track.nid is not None:
            library.track_by_nid[track.nid] = track
        return track

    def pickle(self):
        return {
            "data": self.data,
            "albumId": self.albumId
        }

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
    def artist(self):
        return self.album.artist

    @property
    def album(self):
        return self.library.album_by_id[self.albumId]

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
        param = urlize("%s - %s" % (self.title, self.artist.name))

        return "https://play.google.com/music/m/%s?t=%s&u=%d" % (self.id, param, self.library.id)

    def get_stream_url(self, quality):
        device_id = self.library.get_device_id()
        return self.library.client.get_stream_url(self.id, device_id, quality)

main = None

def load_from(data):
    global main

    if data["schema"] != DB_SCHEMA:
        return

    root_genres = map(lambda data: Genre.unpickle(data), data["genres"])
    main = Library.unpickle(data["libraries"][0])

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

    def find_genres(parent, list):
        genres = library.client.get_genres(parent)
        for data in genres:
            genre = Genre(data)
            list.append(genre)
            genre_by_id[data["id"]] = genre
            genre_by_name[genre.name] = genre

            find_genres(data["id"], genre.children)

    find_genres(None, g_root)
    root_genres = g_root

    logger.info("Found %d genres." % (len(genre_by_id)))

    main.update()

    # TODO Clear out unused genres in genre_by_id and genre_by_name

    return {
        "schema": DB_SCHEMA,
        "genres": map(lambda g: g.pickle(), root_genres),
        "libraries": [main.pickle()]
    }

def get_library(id):
    return main

def get_genre(name):
    return genre_by_name[name]
