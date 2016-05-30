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
logger = logging.getLogger("googlemusicchannel.track")

from utils import hash, urlize
from album import get_album_for_track
from globals import *
from genre import FakeGenre

class Track(object):
    data = None
    albumId = None

    def __init__(self, data):
        self.data = data
        track_by_id[self.id] = self

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
            "albumId": self.albumId
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
        return self.data["nid"]

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
    def thumb(self):
        return self.album.thumb

    @property
    def duration(self):
        return int(self.data["durationMillis"])

    @property
    def url(self):
        param = urlize("%s - %s" % (self.title, self.artist.name))

        return "%s%s?t=%s" % (base_path, self.id, param)

    def get_stream_url(self, quality):
        device_id = self.library.get_device_id()
        return self.library.client.get_stream_url(self.id, device_id, quality)

def get_track_for_data(client, track_data):
    del track_data["id"]

    if not "nid" in track_data:
        track_data["nid"] = "FT%s" % hash("%s:%s:%s" % (track_data["title"], track_data["album"], track_data["albumArtist"]))

    if track_data["nid"] in track_by_id:
        return track_by_id[track_data["nid"]]

    track = Track(track_data)
    album = get_album_for_track(client, track_data)
    track.albumId = album.id

    return track
