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
from base64 import b64encode
import logging
logger = logging.getLogger("googlemusicchannel.utils")

def urlize(string):
    return re.sub(r'[\W-]+', "_", string)

def hash(data):
    return b64encode(hashlib.sha256(data).digest())

def get_album_hash(artist, name):
    # We use this has as the ID as it should be reasonably unique and freely
    # available in both track and album data
    return hash("%s:%s" % (artist, name))
