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
import json
from base64 import b64encode
from uuid import uuid4

from gmusicapi import Mobileclient

DB_PREFIX = "gmdb-"
DB_SCHEMA = 1

def hash(data):
    return b64encode(hashlib.sha256(data).digest())

def get_album_hash(artist, name):
    # We use this has as the ID as it should be reasonably unique and freely
    # available in both track and album data
    return hash("%s:%s" % (artist, name))

def locked(func):
    def inner(*args, **kwargs):
        Thread.AcquireLock("library-lock")
        try:
            return func(*args, **kwargs)
        finally:
            Thread.ReleaseLock("library-lock")
    return inner

class InternalLibrary(object):
    client = None
    device_id = None

    # These are all the artists we know of mapped by the artist name
    artists = None

    # These are all the albums in the user's library. The key is a hash of the
    # album and artist names
    albums = None

    # These are all the tracks in the user's library. The key is the track's library ID
    tracks = None

    def __init__(self, username, password):
        self.username = username
        self.dbname = DB_PREFIX + hash(username)

        self.clear()
        self.load()

        self.client = Mobileclient(False, False, True)

        device_id = self.device_id
        if device_id is None:
            device_id = Mobileclient.FROM_MAC_ADDRESS

        try:
            self.client.login(username, password, device_id)
        except:
            Log.Exception("Client couldn't log in.")

    # Because of threading shenanigans we have to manually pickle classes
    @locked
    def save(self):
        artists = set(map(lambda a: a.artist, self.albums.values()))
        pickle = {
            "schema": DB_SCHEMA,
            "device_id": self.device_id,
            "artists": map(lambda a: a.pickle(), artists)
        }

        Data.Save(self.dbname, json.dumps(pickle))

    def logout(self):
        self.client.logout()

    def load(self):
        try:
            data = json.loads(Data.Load(self.dbname))
            if data["schema"] != DB_SCHEMA:
                return

            self.clear()
            self.device_id = data["device_id"]
            for artist_data in data["artists"]:
                Artist.unpickle(self, artist_data)

            Log.Info("Loaded a library with %d artists, %d albums and %d tracks." %
                     (len(self.artists), len(self.albums), len(self.tracks)))
        except:
            Log.Exception("Failed to load data.")

    def add_track(self, track_data):
        track = Track(self, track_data)

        album_hash = get_album_hash(track_data["albumArtist"], track_data["album"])
        album = self.albums.get(album_hash)

        if album is None:
            album = Album(self, {
                "albumArtist": track_data["albumArtist"],
                "name": track_data["album"]
            })

            artist = self.artists.get(track_data["albumArtist"])
            if artist is None:
                artist = Artist(self, {
                    "name": track_data["albumArtist"]
                })

            album.artist = artist
            artist.albums.add(album)

        album.tracks.add(track)
        track.album = album

        # Attempt to get full album data if needed
        if "albumId" in track_data:
            album.update_id(track_data["albumId"])

        # Add whatever album art we have
        if "albumArtRef" in track_data:
            album.art.add(track_data["albumArtRef"][0]["url"])

        # If the main artist is the album artist then do the same for the
        # artist
        if track_data["albumArtist"] == track_data["artist"]:
            if "artistId" in track_data and len(track_data["artistId"]) > 0:
                album.artist.update_id(track_data["artistId"][0])

            if "artistArtRef" in track_data:
                album.artist.art.add(track_data["artistArtRef"][0]["url"])

    @locked
    def remove_track(self, id):
        track = self.tracks[id]
        del self.tracks[id]

        album = track.album
        album.tracks.remove(track)

        if len(album.tracks) == 0:
            del self.albums[album.id]

            artist = album.artist
            artist.albums.remove(album)

            if len(artist.albums) == 0:
                del self.artists[artist.id]

    @locked
    def clear(self):
        self.artists = {}
        self.albums = {}
        self.tracks = {}

    def update(self):
        Log.Info("Starting library update.")

        try:
            if not self.client.is_authenticated:
                Log.Error("Client isn't authenticated.")
                return

            data = self.client.get_all_songs(False, False)
            Log.Info("Found %d tracks in the cloud library." % (len(data)))

            # Convert to a dict with id as key
            tracks = dict(map(lambda s: (s["id"], s), data))

            currentset = set(self.tracks.keys())
            newset = set(tracks.keys())

            deletedset = currentset - newset
            addedset = newset - currentset
            modifiedset = currentset & newset

            Log.Info("Adding %d new tracks." % (len(addedset)))

            for id in addedset:
                self.add_track(tracks[id])

            Log.Info("Removing %d old tracks." % (len(deletedset)))

            for id in deletedset:
                self.remove_track(id)

            Log.Info("Updating %d existing tracks." % (len(modifiedset)))

            for id in modifiedset:
                current = self.tracks[id]
                new = tracks[id]

                if (current.raw["album"] != new["album"] or
                    current.raw["albumArtist"] != new["albumArtist"]):
                    # The track has changed so much that we just consider it a new
                    # track for now
                    self.remove_track(id)
                    self.add_track(new)
                else:
                    current.raw = new

            Log.Info("Update complete, library has %d artists, %d albums and %d tracks." %
                     (len(self.artists), len(self.albums), len(self.tracks)))

            self.save()
        except:
            Log.Exception("Failed to update library.")

class Artist(object):
    library = None
    id = None
    albums = None
    raw = None
    art = None

    @classmethod
    def unpickle(cls, library, data):
        artist = cls(library, data["raw"])

        for album_data in data["albums"]:
            album = Album.unpickle(library, album_data)
            album.artist = artist
            artist.albums.add(album)

        artist.art.update(data["art"])

        return artist

    @locked
    def __init__(self, library, data):
        self.library = library
        self.id = data["name"]
        self.raw = data

        self.albums = set()
        self.art = set()

        library.artists[self.id] = self

    def pickle(self):
        return {
            "raw": self.raw,
            "albums": map(lambda a: a.pickle(), self.albums),
            "art": list(self.art)
        }

    def update_id(self, artistId):
        # If we already have an id then just ignore this
        if "artistId" in self.raw:
            return

        # Ignore blank IDs
        if artistId == "":
            return

        try:
            artist_data = self.library.client.get_artist_info(artistId, False, 0, 0)

            # Sanity check
            if artist_data["name"] != self.raw["name"]:
                return

            self.raw = artist_data
            if "artistArtRef" in artist_data:
                self.art.add(artist_data["artistArtRef"])
            if "artistArtRefs" in artist_data:
                for art in artist_data["artistArtRefs"]:
                    self.art.add(art["url"])
        except:
            # Ignore bad IDs
            pass

    # Public API
    @property
    def name(self):
        return self.raw["name"]

    @property
    def thumb(self):
        if len(self.art) > 0:
            return list(self.art)[0]
        return R("googlemusic.png")

class Album(object):
    library = None
    id = None
    artist = None
    tracks = None
    raw = None
    art = None

    @classmethod
    def unpickle(cls, library, data):
        album = cls(library, data["raw"])

        for track_data in data["tracks"]:
            track = Track.unpickle(library, track_data)
            track.album = album
            album.tracks.add(track)

        album.art.update(data["art"])

        return album

    @locked
    def __init__(self, library, data):
        self.library = library
        self.id = get_album_hash(data["albumArtist"], data["name"])
        self.raw = data

        self.tracks = set()
        self.art = set()

        library.albums[self.id] = self

    def pickle(self):
        return {
            "raw": self.raw,
            "tracks": map(lambda t: t.pickle(), self.tracks),
            "art": list(self.art)
        }

    def update_id(self, albumId):
        # If we already have an id then just ignore this
        if "albumId" in self.raw:
            return

        # Ignore blank IDs
        if albumId == "":
            return

        try:
            album_data = self.library.client.get_album_info(albumId, False)

            # Sometimes album IDs return incorrect data
            if (album_data["name"] != self.raw["name"] or
                album_data["albumArtist"] != self.raw["albumArtist"]):
                return

            self.raw = album_data
            if "albumArtRef" in album_data:
                self.art.add(album_data["albumArtRef"])

            # If we have one pass along the artist ID
            if "artistId" in album_data:
                self.artist.update_id(album_data["artistId"][0])
        except:
            # Ignore bad IDs
            pass

    # Public API
    @property
    def name(self):
        return self.raw["name"]

    @property
    def thumb(self):
        if len(self.art) > 0:
            return list(self.art)[0]
        return R("googlemusic.png")

    @property
    def url(self):
        if "albumId" in self.raw:
            return "https://play.google.com/music/m/" + self.raw["albumId"]
        return "https://play.google.com/music/m/" + self.id

class Track(object):
    library = None
    id = None
    album = None
    raw = None

    @classmethod
    def unpickle(cls, library, data):
        return cls(library, data["raw"])

    @locked
    def __init__(self, library, data):
        self.library = library
        self.id = data["id"]
        self.raw = data

        library.tracks[self.id] = self

    def pickle(self):
        return {
            "raw": self.raw
        }


    # Public API
    @property
    def title(self):
        return self.raw["title"]

    @property
    def thumb(self):
        return self.album.thumb

    @property
    def url(self):
        if len(self.art) > 0:
            return list(self.art)[0]
        return R("googlemusic.png")

internal = None

def set_credentials(username, password):
    global internal

    if internal is not None:
        internal.logout()
        internal = None

    if username is None or password is None:
        return

    internal = InternalLibrary(username, password)

def refresh():
    internal.update()

@locked
def get_artists():
    return set(map(lambda a: a.artist, internal.albums.values()))

@locked
def get_artist(id):
    return internal.artists[id]

@locked
def get_albums():
    return internal.albums.values()

@locked
def get_album(id):
    return internal.albums[id]

@locked
def get_songs():
    return internal.songs.values()
