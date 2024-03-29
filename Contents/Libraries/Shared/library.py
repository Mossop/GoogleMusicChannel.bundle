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
from album import LibraryAlbum
from station import Station
from utils import get_art_for_data, get_thumb_for_data

from gmusicapi import Mobileclient

logger = logging.getLogger("googlemusicchannel.library")


# We need at least one Library in order to have a valid client
class Library(object):
    id = None

    username = None
    password = None

    client = None

    situations = None

    # These are all the tracks in the user's library. The key is the track's
    # library ID, not the store ID
    track_by_id = None

    playlist_by_id = None

    station_by_id = None

    def __init__(self, username, password):
        self.id = 0
        libraries[self.id] = self

        self.username = username
        self.password = password

        self.clear()

        self.client = Mobileclient(False, False, True)

    # Because of threading shenanigans we have to manually pickle classes
    def pickle(self):
        return {
            "username": self.username,
            "password": self.password,
            "tracks": self.track_by_id,
            "playlists": map(lambda p: p.pickle(), self.playlist_by_id.values()),
            "stations": map(lambda s: s.pickle(), self.station_by_id.values())
        }

    @classmethod
    def unpickle(cls, data):
        try:
            library = cls(data["username"], data["password"])

            library.clear()

            library.track_by_id = data["tracks"]
            for playlist_data in data["playlists"]:
                Playlist.unpickle(library, playlist_data)

            for station_data in data["stations"]:
                Station.unpickle(library, station_data)
        except:
            logger.exception("Failed to load data.")
            return None

    def get_library_client(self):
        if self.client.is_authenticated():
            return self.client

        logger.info("Logging in '%s' with MAC address." % (self.username))
        self.client.login(self.username, self.password, Mobileclient.FROM_MAC_ADDRESS)

        if not self.client.is_authenticated():
            raise Exception("Client couldn't log in.")

        return self.client

    def get_stream_client(self):
        device_id = self.get_device_id()
        client = Mobileclient(False, False, True)
        logger.info("Logging in '%s' with device id '%s'." % (self.username, device_id))
        client.login(self.username, self.password, device_id)

        if not client.is_authenticated():
            raise Exception("Client couldn't log in.")

        return client

    def logout(self):
        if self.client.is_authenticated():
            self.client.logout()

    def get_device_id(self):
        devices = self.get_library_client().get_registered_devices()
        for device in devices:
            if device["type"] == "ANDROID":
                return device["id"][2:]
            if device["type"] == "IOS":
                return device["id"]

        raise Exception("Unable to find a valid device ID")

    def clear(self):
        self.track_by_id = {}
        self.playlist_by_id = {}
        self.station_by_id = {}

    def update(self):
        logger.info("Starting library update.")

        try:
            client = self.get_library_client()
        except:
            logger.exception("Failed to log in to library.")
            self.clear()
            return

        try:
            data = client.get_all_songs(False, False)
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

            seenlists = set()

            def add_playlist(playlist_data, entries):
                playlist = Playlist(self, playlist_data)
                seenlists.add(playlist.id)

                for entry in entries:
                    trackId = entry["trackId"]
                    if trackId in self.track_by_id:
                        trackId = self.track_by_id[trackId]
                    if trackId in track_by_id:
                        playlist.track_ids.append(track_by_id[trackId].id)
                        continue
                    track_data = client.get_track_info(trackId)
                    playlist.track_ids.append(get_track_for_data(self, track_data).id)

            playlists = client.get_all_user_playlist_contents()
            for playlist in playlists:
                if playlist["deleted"]:
                    continue
                add_playlist(playlist, playlist["tracks"])

            all_playlists = client.get_all_playlists(False, False)
            for playlist in all_playlists:
                if playlist.get("type") != "USER_GENERATED":
                    entries = client.get_shared_playlist_contents(playlist["shareToken"])
                    add_playlist(playlist, entries)

            gonelists = set(self.playlist_by_id.keys()) - seenlists
            for listid in gonelists:
                del self.playlist_by_id[listid]

            logger.info("Library has %d playlists." % (len(self.playlist_by_id)))

            current_stations = set()
            stations = client.get_all_stations()
            for station_data in stations:
                if not station_data["inLibrary"]:
                    continue
                station = Station(self, station_data)
                current_stations.add(station.id)

            removed = set(self.station_by_id.keys()) - current_stations
            for rem in removed:
                del self.station_by_id[rem]

            logger.info("Library has %d stations." % (len(self.station_by_id)))

            self.situations = self.load_listen_situations()
        except:
            logger.exception("Failed to update library.")

    def get_artists(self):
        return set(map(lambda t: t.artist, self.get_tracks()))

    def get_albums(self):
        return map(lambda a: LibraryAlbum(self, a), set(map(lambda t: t.album, self.get_tracks())))

    def get_albums_by_artist(self, artist):
        return set(map(lambda t: LibraryAlbum(self, t.album),
                       filter(lambda t: t.artist == artist, self.get_tracks())))

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

    def get_stations(self):
        return self.station_by_id.values()

    def get_station(self, id):
        return self.station_by_id[id]

    def get_station_id(self, name, **kwargs):
        return self.get_library_client().create_station(name, **kwargs)

    def get_station_tracks(self, stationId, num_tracks=25):
        tracks = self.get_library_client().get_station_tracks(stationId, num_tracks)
        return map(lambda t: get_track_for_data(self, t, False), tracks)

    def load_listen_situations(self):
        situations = self.get_library_client().get_listen_now_situations()
        logger.info("Found %d situations" % len(situations))

        def build_situation(data):
            sit = {}

            for prop in ["title", "imageUrl", "wideImageUrl"]:
                sit[prop] = data[prop]

            if "stations" in data:
                sit["stations"] = []

                for station in data["stations"]:
                    sit["stations"].append({
                        "id": station["seed"]["curatedStationId"],
                        "name": station["name"],
                        "thumb": get_thumb_for_data(station),
                        "art": get_art_for_data(station)
                    })
            elif "situations" in data:
                sit["situations"] = [build_situation(d) for d in data["situations"]]
            else:
                logger.error("Unexpected keys in situation: %s", repr(data.keys()))
                return None

            return sit

        return filter(lambda s: s is not None, [build_situation(d) for d in situations])

    def get_listen_situations(self):
        if self.situations is None:
            self.situations = self.load_listen_situations()
        return self.situations

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
