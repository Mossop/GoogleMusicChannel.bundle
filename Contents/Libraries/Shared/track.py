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

from utils import urlize
from album import get_album_for_track
from globals import *
from genre import FakeGenre

logger = logging.getLogger("googlemusicchannel.track")


class Track(object):
    data = None
    albumId = None

    def __init__(self, data):
        self.data = data
        track_by_id[self.id] = self

        if "genre" in data:
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
    def unpickle(cls, data):
        if data["albumId"] not in album_by_id:
            logger.error("Refusing to unpickle track with no valid album (%s by %d)." %
                         (data["title"], data["albumArtist"]))
            return

        track = cls(data["data"])
        track.albumId = data["albumId"]
        return track

    def pickle(self):
        return {
            "data": self.data,
            "albumId": self.albumId,
        }

    def __cmp__(self, other):
        if not isinstance(other, Track):
            raise Exception("Cannot compare a Track to %s" % repr(other))

        if self.data["discNumber"] != other.data["discNumber"]:
            return self.data["discNumber"] - other.data["discNumber"]
        return self.data["trackNumber"] - other.data["trackNumber"]

    # Public API
    @property
    def id(self):
        return self.data["id"]

    @property
    def artist(self):
        return self.album.artist

    @property
    def album(self):
        return album_by_id[self.albumId]

    @property
    def genre(self):
        return genre_by_name[self.data["genre"]]

    @property
    def title(self):
        return self.data["title"]

    @property
    def name(self):
        return self.data["title"]

    @property
    def art(self):
        return self.album.art

    @property
    def thumb(self):
        return self.album.thumb

    @property
    def duration(self):
        return int(self.data["durationMillis"])

    def get_url(self, library):
        param = urlize("%s - %s" % (self.title, self.artist.name))

        return "%s%s?t=%s&u=%d" % (base_path, self.id, param, library.id)

    def get_stream_url(self, library, quality):
        client = library.get_stream_client()
        url = client.get_stream_url(self.id, None, quality)
        client.logout()

        return url

def get_track_for_data(library, track_data, lookups=True):
    if "nid" in track_data:
        track_data["id"] = track_data["nid"]

    if track_data["id"] in track_by_id:
        return track_by_id[track_data["id"]]

    track = Track(track_data)
    album = get_album_for_track(library.get_library_client(), track_data, lookups)
    track.albumId = album.id

    return track
