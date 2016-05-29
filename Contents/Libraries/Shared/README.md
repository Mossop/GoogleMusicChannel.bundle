lib2to3 is a clone of the default lib2to3 python module included in Plex's
python installation. Because that install is inside a zip file it suffers from
https://bugs.python.org/issue24960 and so we override it with a version in
a real filesystem.
