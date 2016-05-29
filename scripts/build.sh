#! /bin/sh

cd `dirname $0`/..

arch=`python -c "import sys; import platform; print(\"%s-%s\" % (sys.platform, platform.architecture()[0]))"`

rm -rf Contents/Libraries/Shared/${arch}
mkdir Contents/Libraries/Shared/${arch}
rm -rf Contents/Libraries/Shared/shared
mkdir Contents/Libraries/Shared/shared

pip install --no-deps -t Contents/Libraries/Shared/${arch} -r platform_requirements.txt
pip install --no-deps -t Contents/Libraries/Shared/shared -r requirements.txt

# For some reason without this protobuf is broken as a module
echo "" >Contents/Libraries/Shared/shared/google/__init__.py
