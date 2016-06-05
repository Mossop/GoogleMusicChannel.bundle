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

logger = logging.getLogger("googlemusicchannel.library")


class Station(object):
    library = None
    data = None

    def __init__(self, library, data):
        self.library = library
        self.data = data
        library.station_by_id[self.id] = self

    def pickle(self):
        return self.data

    def get_tracks(self):
        tracks = self.library.client.get_station_tracks(self.id)
        return map(lambda t: get_track_for_data(self.library, t), tracks)

    @classmethod
    def unpickle(cls, library, data):
        return cls(library, data)

    @property
    def id(self):
        return self.data["id"]

    @property
    def name(self):
        return "%s Radio" % self.data["name"]

    @property
    def art(self):
        if "compositeArtRefs" in self.data:
            arts = filter(lambda a: float(a["aspectRatio"]) > 1, self.data["compositeArtRefs"])
            if len(arts) == 0:
                return self.thumb
            return arts[0]["url"]
        return None

    @property
    def thumb(self):
        if "compositeArtRefs" in self.data:
            thumbs = filter(lambda a: float(a["aspectRatio"]) == 1, self.data["compositeArtRefs"])
            if len(thumbs) == 0:
                return None
            return thumbs[0]["url"]
        return None
