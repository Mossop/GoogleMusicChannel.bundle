#! /bin/sh

cd `dirname $0`/..

rm -rf Contents/Libraries
mkdir -p Contents/Libraries/Shared

# Override the system lib2to3. See ../resources/README.md
cp -R resources/lib2to3 Contents/Libraries/Shared

pip install -t Contents/Libraries/Shared -r requirements.txt

# For some reason without this protobuf is broken as a module
echo "" >Contents/Libraries/Shared/google/__init__.py
