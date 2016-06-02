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

from globals import *
from track import get_track_for_data

from gmusicapi import Mobileclient

logger = logging.getLogger("googlemusicchannel.library")


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

    playlist_by_id = None

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
            "tracks": self.track_by_id,
            "playlists": map(lambda p: p.pickle(), self.playlist_by_id.values())
        }

    @classmethod
    def unpickle(cls, data):
        try:
            library = cls(data["username"], data["password"])
            library.device_id = data["device_id"]

            library.clear()

            library.track_by_id = data["tracks"]
            for playlist_data in data["playlists"]:
                Playlist.unpickle(library, playlist_data)
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
        self.playlist_by_id = {}

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

            logger.info("Adding %d new tracks and updating %d existing tracks." %
                        (len(addedset), len(modifiedset)))

            def add_track(track_data):
                lid = track_data["id"]

                track = get_track_for_data(self, track_data)
                self.track_by_id[lid] = track.id

            for track_data in filter(lambda d: "nid" in d, data):
                add_track(track_data)

            for track_data in filter(lambda d: "nid" not in d, data):
                add_track(track_data)

            logger.info("Removing %d old tracks." % (len(deletedset)))

            for id in deletedset:
                if id in self.track_by_id:
                    del self.track_by_id[id]

            logger.info("Track update complete, library has %d tracks." % (len(self.track_by_id)))

            def add_playlist(playlist_data, entries):
                playlist = Playlist(self, playlist_data)

                for entry in entries:
                    trackId = entry["trackId"]
                    if trackId in self.track_by_id:
                        trackId = self.track_by_id[trackId]
                    if trackId in track_by_id:
                        playlist.track_ids.append(track_by_id[trackId].id)
                        continue
                    track_data = self.client.get_track_info(trackId)
                    playlist.track_ids.append(get_track_for_data(self, track_data).id)

            playlists = self.client.get_all_user_playlist_contents()
            for playlist in playlists:
                add_playlist(playlist, playlist["tracks"])

            all_playlists = self.client.get_all_playlists()
            for playlist in all_playlists:
                if playlist.get("type") == "SHARED":
                    entries = self.client.get_shared_playlist_contents(playlist["shareToken"])
                    add_playlist(playlist, entries)
        except:
            logger.exception("Failed to update library.")

    def get_artists(self):
        return set(map(lambda t: t.artist, self.get_tracks()))

    def get_albums(self):
        return set(map(lambda t: t.album, self.get_tracks()))

    def get_albums_by_artist(self, artist):
        return set(map(lambda t: t.album, filter(lambda t: t.artist == artist, self.get_tracks())))

    def get_tracks(self):
        return map(lambda id: track_by_id[id], self.track_by_id.values())

    def get_tracks_in_album(self, album):
        return sorted(filter(lambda t: t.album == album, self.get_tracks()))

    def get_tracks_in_genre(self, genre):
        return filter(lambda t: t.genre == genre, self.get_tracks())

    def get_genres(self):
        return set(map(lambda t: t.genre, self.get_tracks()))

    def get_track(self, trackId):
        return self.track_by_id[trackId]

    def get_playlist(self, playlistId):
        return self.playlist_by_id[playlistId]

    def get_playlists(self):
        return self.playlist_by_id.values()


class Playlist(object):
    data = None
    track_ids = None

    def __init__(self, library, data):
        self.data = data
        self.track_ids = []
        library.playlist_by_id[self.id] = self

    def pickle(self):
        return {
            "data": self.data,
            "tracks": self.track_ids
        }

    @classmethod
    def unpickle(cls, library, data):
        playlist = cls(library, data["data"])
        playlist.track_ids = data["tracks"]

    @property
    def id(self):
        return self.data["id"]

    @property
    def name(self):
        return self.data["name"]

    @property
    def tracks(self):
        return map(lambda id: track_by_id[id], self.track_ids)
