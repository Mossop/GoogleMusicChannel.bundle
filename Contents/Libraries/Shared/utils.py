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

import re
import hashlib
from base64 import urlsafe_b64encode
import logging

logger = logging.getLogger("googlemusicchannel.utils")


def urlize(string):
    return re.sub(r'[\W-]+', "_", string)


def hash(data):
    return urlsafe_b64encode(hashlib.sha256(data).digest())


def get_album_hash(artist, name):
    # We use this has as the ID as it should be reasonably unique and freely
    # available in both track and album data
    return hash("%s:%s" % (artist, name))


def get_images_for_data(data, filt=lambda i: True):
    images = []

    def get_image(data):
        if "aspectRatio" in data:
            data["aspectRatio"] = float(data["aspectRatio"])
        return data

    def get_images(data, key):
        if key in data:
            if isinstance(data[key], list):
                return filter(filt, [get_image(i) for i in data[key]])
            try:
                image = get_image(data[key])
                if filt(image):
                    return [image]
            except:
                logger.error("Failed to find an %s in %s" % (key, repr(data)))
        return []

    for key in ["compositeArtRef", "albumArtRef", "artistArtRef", "images", "imageUrl"]:
        images.extend(get_images(data, "%ss" % key))

        if key in data:
            image = {
                "url": data[key],
                "aspectRatio": 1
            }
            if filt(image):
                images.append(image)

    return images


def get_art_for_data(data):
    images = get_images_for_data(data, lambda i: i["aspectRatio"] > 1 and i["aspectRatio"] <= 2)

    if len(images) > 0:
        perfect = filter(lambda i: i["aspectRatio"] == 2, images)
        if len(perfect) > 0:
            return perfect[0]["url"]
        return images[0]["url"]

    logger.info("No art found for object %s", repr(data))
    return get_thumb_for_data(data)


def get_thumb_for_data(data):
    images = get_images_for_data(data, lambda i: i["aspectRatio"] == 1)
    if len(images) > 0:
        return images[0]["url"]
    logger.info("No thumb found for object %s", repr(data))
    return None
