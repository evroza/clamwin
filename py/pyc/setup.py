#!/usr/bin/env python
from distutils.core import setup, Extension
from sys import platform
from os import environ

if platform == 'win32':
    CFLAGS = [] #[ '/Zi' ]
    LDFLAGS = [] #[ '/PDB:pyd.pdb' ]
    LIBS = []
    environ['DISTUTILS_USE_SDK'] = '1'
    environ['MSSdk'] = '.'
    CLAMAVDEVROOT = 'F:\Dev\code\clamav-win32' #environ.get('CLAMAV_DEVROOT')
    DEBUG = environ.get('CLAMAV_DEBUG', None)
    if DEBUG is not None:
        LIBFILE = 'contrib/msvc/Debug/Win32/libclamavd.lib'
        CFLAGS.append('-MDd')
    else:
        LIBFILE = 'contrib/msvc/Release/Win32/libclamav.lib'
        CFLAGS.append('-MD')
    CLINCLUDE = ['/'.join([CLAMAVDEVROOT, 'contrib/clamav/libclamav']), 'C:/Program Files (x86)/Microsoft Visual Studio 8/VC/include', 'C:/Program Files (x86)/Microsoft Visual Studio 8/VC/PlatformSDK/Include']
    CLLIB = ['/'.join([CLAMAVDEVROOT, LIBFILE])]
else:
    CFLAGS = [ '-Wall', '-O0', '-g3' ]
    LDFLAGS = [ '-L/usr/local/lib' ]
    LIBS = [ 'clamav' ]
    CLINCLUDE = [ '/usr/local/include', 'C:/Program Files (x86)/Microsoft Visual Studio 8/VC/include', 'C:/Program Files (x86)/Microsoft Visual Studio 8/VC/PlatformSDK/Include' ]
    CLLIB = []

pyc = Extension('pyc',
                sources = ['pyc.c'],
                libraries = LIBS,
				library_dirs = ['C:/Program Files (x86)/Microsoft Visual Studio 8/VC/lib', 'C:/Python23/libs', 'F:\Dev\code\clamav-win32\contrib\msvc\Release\Win32'],
                extra_objects = CLLIB,
                extra_link_args = LDFLAGS,
                extra_compile_args = CFLAGS)

# Build : python setup.py build
# Install : python setup.py install
# Register : python setup.py register

print("wewe")

setup (name = 'pyc',
       version = '0.98.4',
       author = 'Gianluigi Tiesi',
       author_email = 'sherpya@netfarm.it',
       license ='BSD',
       keywords="python, clamav, antivirus, scanner, virus, libclamav",
       include_dirs = CLINCLUDE,
       ext_modules = [ pyc ])
