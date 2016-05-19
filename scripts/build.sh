#! /bin/sh

cd `dirname $0`/..

arch=`python -c "import sys; import platform; print(\"%s-%s\" % (sys.platform, platform.architecture()[0]))"`

rm -rf Contents/Libraries/Shared/${arch}
mkdir Contents/Libraries/Shared/${arch}

pip install -t Contents/Libraries/Shared/${arch} -r requirements.txt

# For some reason without this protobuf is broken as a module
echo "" >Contents/Libraries/Shared/${arch}/google/__init__.py
