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
from artist import get_artist_for_album, get_artist_for_track
from utils import hash, urlize, get_art_for_data, get_thumb_for_data

logger = logging.getLogger("googlemusicchannel.album")


class Album(object):
    data = None
    artistId = None

    def __init__(self, data):
        self.data = data
        album_by_id[self.id] = self

    @classmethod
    def unpickle(cls, data):
        if data["artistId"] not in artist_by_id:
            logger.error("Refusing to unpickle album with no valid artist (%s by %s)." %
                         (data["name"], data["artist"]))
            return None

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
    def art(self):
        return get_art_for_data(self.data)

    @property
    def thumb(self):
        return get_thumb_for_data(self.data)

    @property
    def url(self):
        param = urlize("%s - %s" % (self.name, self.artist.name))

        return "%s%s?t=%s" % (base_path, self.id, param)

    @property
    def tracks(self):
        # We don't know what this means yet!
        return []


# This is a special view of an Album including only the tracks that are in a
# given library.
class LibraryAlbum(object):
    library = None,
    artist = None,

    def __init__(self, library, album):
        self.library = library
        self.album = album

    @property
    def id(self):
        return self.album.id

    @property
    def name(self):
        return self.album.name

    @property
    def artist(self):
        return self.album.artist

    @property
    def art(self):
        return self.album.art

    @property
    def thumb(self):
        return self.album.thumb

    @property
    def url(self):
        return "%s&u=%d" % (self.album.url, self.library.id)

    @property
    def tracks(self):
        return self.library.get_tracks_in_album(self.album)


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
        album_data["albumArtRef"] = track_data["albumArtRef"][0]["url"]
    elif "artistArtRef" in track_data:
        album_data["albumArtRef"] = track_data["artistArtRef"][0]["url"]
    else:
        album_data["albumArtRef"] = None

    album = Album(album_data)
    artist = get_artist_for_track(client, track_data)

    album.artistId = artist.id
    return album


def get_real_album_for_track(client, track_data, lookups=True):
    # This is a real track ID, look up the album with the client
    albumId = track_data["albumId"]

    if albumId in album_by_id:
        album = album_by_id[albumId]
    else:
        album_data = client.get_album_info(albumId, False)
        album = Album(album_data)

    if album.name != track_data["album"]:
        logger.warn("Invalid album returned for %s." % track_data["album"])
        return get_fake_album_for_track(client, track_data)

    if album.artistId is None:
        artist = get_artist_for_album(client, album_data, track_data, lookups)
        album.artistId = artist.id

    return album


def get_album_for_track(client, track_data, lookups=True):
    if not lookups or "nid" not in track_data:
        return get_fake_album_for_track(client, track_data)
    else:
        return get_real_album_for_track(client, track_data)
