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
from utils import hash, urlize

logger = logging.getLogger("googlemusicchannel.artist")


class Artist(object):
    data = None

    def __init__(self, data):
        self.data = data
        artist_by_id[self.id] = self

    @classmethod
    def unpickle(cls, data):
        artist = cls(data["data"])
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

        return "%s%s?t=%s" % (base_path, self.id, param)

various_artists = Artist({
    "artistId": "FA" + hash("Various Artists"),
    "name": "Various Artists"
})


# Called when there is no real album for a track
def get_artist_for_track(client, track_data):
    artistId = "FA%s" % hash(track_data["albumArtist"])
    if artistId in artist_by_id:
        return artist_by_id[artistId]

    artist_data = {
        "artistId": artistId,
        "name": track_data["albumArtist"],
    }

    if "artistArtRef" in track_data:
        artist_data["artistArtRef"] = track_data["artistArtRef"][0]["url"]
    elif "albumArtRef" in track_data:
        artist_data["artistArtRef"] = track_data["albumArtRef"][0]["url"]
    else:
        artist_data["artistArtRef"] = None

    return Artist(artist_data)


# Called when we should expect a real artist to exist
def get_artist_for_album(client, album_data, track_data):
    if album_data["artistId"][0] in artist_by_id:
        artist = artist_by_id[album_data["artistId"][0]]
    elif album_data["artistId"][0] == "":
        artist = various_artists
    else:
        artist_data = client.get_artist_info(album_data["artistId"][0], False, 0, 0)
        artist = Artist(artist_data)

    if artist.name != album_data["artist"]:
        logger.warn("Invalid album returned for %s." % album_data["artist"])
        return get_artist_for_track(client, track_data)

    return artist
