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
logger = logging.getLogger("googlemusicchannel.library")

from globals import *
from track import get_track_for_data
from utils import urlize

from gmusicapi import Mobileclient

class LibraryTrack(object):
    library = None
    id = None
    track = None
    isfake = False

    def __init__(self, library, id, track):
        self.library = library
        self.id = id
        self.track = track
        self.isfake = self.track.id[0] == "F"
        library.track_by_id[id] = self

    def pickle(self):
        return {
            "id": self.id,
            "nid": self.track.id
        }

    @classmethod
    def unpickle(cls, library, data):
        if data["nid"] not in track_by_id:
            logger.error("Refusing to unpickle library track with no valid track (%s)." % data["nid"])
            return

        track = track_by_id[data["nid"]]
        return LibraryTrack(library, data["id"], track)

    def __cmp__(self, other):
        if isinstance(other, LibraryTrack):
            other = other.track
        return self.track.__cmp__(other)

    def get_stream_url(self, quality):
        device_id = self.library.get_device_id()
        return self.library.client.get_stream_url(self.id, device_id, quality)

    @property
    def artist(self):
        return self.track.artist

    @property
    def album(self):
        return self.track.album

    @property
    def genre(self):
        return self.track.genre

    @property
    def title(self):
        return self.track.title

    @property
    def thumb(self):
        return self.track.thumb

    @property
    def duration(self):
        return self.track.duration

    @property
    def url(self):
        param = urlize("%s - %s" % (self.title, self.artist.name))

        return "%s%s?t=%s" % (base_path, self.id, param)

# We need at least one Library in order to have a valid client
class Library(object):
    id = None

    username = None
    password = None

    client = None
    device_id = None

    # These are all the tracks in the user's library. The key is the track's
    # library ID, not the store ID
    track_by_id = None

    def __init__(self, username, password):
        self.id = 0
        libraries[self.id] = self

        self.username = username
        self.password = password

        self.clear()

        self.client = Mobileclient(False, False, True)

        try:
            self.client.login(username, password, Mobileclient.FROM_MAC_ADDRESS)
        except:
            logger.exception("Client couldn't log in.")

    # Because of threading shenanigans we have to manually pickle classes
    def pickle(self):
        return {
            "username": self.username,
            "password": self.password,
            "device_id": self.device_id,
            "tracks": map(lambda t: t.pickle(), self.track_by_id.values())
        }

    @classmethod
    def unpickle(cls, data):
        try:
            library = cls(data["username"], data["password"])
            library.device_id = data["device_id"]

            library.clear()

            for d in data["tracks"]:
                LibraryTrack.unpickle(library, d)
        except:
            logger.exception("Failed to load data.")
            return None

    def logout(self):
        self.client.logout()

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

    def clear(self):
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

            def add_track(track_data):
                lid = track_data["id"]

                track = get_track_for_data(self.client, track_data)
                LibraryTrack(self, lid, track)

            for track_data in filter(lambda d: "nid" in d, data):
                add_track(track_data)

            for track_data in filter(lambda d: "nid" not in d, data):
                add_track(track_data)

            logger.info("Removing %d old tracks." % (len(deletedset)))

            for id in deletedset:
                if id in self.track_by_id:
                    del self.track_by_id[id]

            logger.info("Update complete, library has %d tracks." % (len(self.track_by_id)))
        except:
            logger.exception("Failed to update library.")

    def get_artists(self):
        return set(map(lambda t: t.artist, self.get_tracks()))

    def get_albums(self):
        return set(map(lambda t: t.album, self.get_tracks()))

    def get_albums_by_artist(self, artist):
        return set(map(lambda t: t.album, filter(lambda t: t.artist == artist, self.get_tracks())))

    def get_tracks(self):
        return self.track_by_id.values()

    def get_tracks_in_album(self, album):
        return sorted(filter(lambda t: t.album == album, self.get_tracks()))

    def get_tracks_in_genre(self, genre):
        return filter(lambda t: t.genre == genre, self.get_tracks())

    def get_genres(self):
        return set(map(lambda t: t.genre, self.get_tracks()))

    def get_track(self, trackId):
        return self.track_by_id[trackId]
