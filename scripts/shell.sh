#! /bin/sh

cd `dirname $0`/..

arch=`python -c "import sys; import platform; print(\"%s-%s\" % (sys.platform, platform.architecture()[0]))"`
export PYTHONPATH=`pwd`/Contents/Libraries/Shared
python
