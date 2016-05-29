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
logger = logging.getLogger("googlemusicchannel.album")

from globals import *
from artist import get_artist_for_album, get_artist_for_track

class Album(object):
    data = None
    artistId = None

    def __init__(self, data):
        self.data = data
        album_by_id[self.id] = self

    @classmethod
    def unpickle(cls, data):
        album = cls(data["data"])
        album.artistId = data["artistId"]
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
            return artist_by_id[self.artistId]
        return None
    
    @property
    def thumb(self):
        return self.data["albumArtRef"]

    @property
    def url(self):
        param = urlize("%s - %s" % (self.name, self.artist.name))

        return "https://play.google.com/music/m/%s?t=%s" % (self.id, param)

def get_fake_album_for_track(client, track_data):
    # This is a fake track ID, make up an album if necessary
    albumId = "FB%s" % hash("%s:%s" % (track_data["album"], track_data["albumArtist"]))

    if albumId in album_by_id:
        return album_by_id[albumId]

    album_data = {
        "albumId": albumId,
        "name": track_data["album"]
    }

    if "albumArtRef" in track_data:
        album_data["albumArtRef"] = track_data["artistArtRef"][0]["url"]
    elif "artistArtRef" in track_data:
        album_data["albumArtRef"] = track_data["albumArtRef"][0]["url"]
    else:
        album_data["albumArtRef"] = None

    album = Album(album_data)
    artist = get_artist_for_track(client, track_data)

    album.artistId = artist.id
    return album

def get_real_album_for_track(client, track_data):
    # This is a real track ID, look up the album with the client
    albumId = track_data["albumId"]

    if track_data["albumId"] in album_by_id:
        album = album_by_id[track_data["albumId"]]
    else:
        album_data = client.get_album_info(track_data["albumId"], False)
        album = Album(album_data)

    if album.name != track_data["album"]:
        logger.warn("Invalid album returned for %s." % track_data["album"])
        return get_fake_album_for_track(client, track_data)

    artist = get_artist_for_album(client, album_data, track_data)

    album.artistId = artist.id
    return album

def get_album_for_track(client, track_data):
    if track_data["nid"][0] == "F":
        return get_fake_album_for_track(client, track_data)
    else:
        return get_real_album_for_track(client, track_data)
