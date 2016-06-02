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

from utils import hash, urlize
from album import get_album_for_track
from globals import *
from genre import FakeGenre

logger = logging.getLogger("googlemusicchannel.track")


class Track(object):
    data = None
    albumId = None
    libraryId = None

    def __init__(self, data, libraryId = None):
        self.data = data
        self.libraryId = libraryId
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
        track.libraryId = data["libraryId"]
        return track

    def pickle(self):
        return {
            "data": self.data,
            "albumId": self.albumId,
            "libraryId": self.libraryId
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

        url = "%s%s?t=%s" % (base_path, self.id, param)
        if self.libraryId is not None:
            url = "%s&u=%d" % (url, self.libraryId)
        return url

    def get_stream_url(self, quality, client = None, device_id = None):
        pid = self.id
        if client is None:
            if self.libraryId is not None:
                library = libraries[self.libraryId]
                for (lid, id) in library.track_by_id.iteritems():
                    if id == self.id:
                        pid = lid
            else:
                library = libraries[0]
            client = library.client
            device_id = library.get_device_id()

        return client.get_stream_url(pid, device_id, quality)


def get_track_for_data(library, track_data):
    if "id" in track_data:
        del track_data["id"]

    libraryId = None
    if "nid" not in track_data:
        libraryId = library.id
        id = hash("%s:%s:%s" %
                  (track_data["title"], track_data["album"], track_data["albumArtist"]))
        track_data["nid"] = "FT%s" % id

    if track_data["nid"] in track_by_id:
        return track_by_id[track_data["nid"]]

    track = Track(track_data, libraryId)
    album = get_album_for_track(library.client, track_data)
    track.albumId = album.id

    return track
