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

logger = logging.getLogger("googlemusicchannel.genre")


class FakeGenre(object):
    name = None
    examples = None

    def __init__(self, name):
        self.name = name
        self.examples = []

    def pickle(self):
        return {
            "name": self.name
        }

    @property
    def thumb(self):
        tracks = filter(lambda t: t.album.thumb is not None, self.examples)
        if len(tracks) == 0:
            return None
        return tracks[0].album.thumb


class Genre(object):
    data = None
    children = None

    def __init__(self, data):
        self.data = data
        self.children = []

    @classmethod
    def unpickle(cls, data):
        if "data" in data:
            genre = cls(data["data"])
            genre.children = map(lambda d: Genre.unpickle(d), data["children"])
            genre_by_id[genre.id] = genre
        else:
            genre = FakeGenre(data["name"])
        root_genres.append(genre)
        genre_by_name[genre.name] = genre

        return genre

    def pickle(self):
        return {
            "data": self.data,
            "children": map(lambda g: g.pickle(), self.children)
        }

    # Public API
    @property
    def id(self):
        return self.data["id"]

    @property
    def name(self):
        return self.data["name"]

    @property
    def thumb(self):
        if "images" in self.data and len(self.data["images"]) > 0:
            return self.data["images"][0]["url"]
        return None
