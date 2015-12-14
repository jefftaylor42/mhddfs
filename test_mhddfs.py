#!/usr/bin/env python3
import pytest

def sh(cmd):
    import subprocess
    subprocess.check_call(cmd, shell=True)

def test_readdir():
    import os, shutil, subprocess
    import time
    # Create directories
    sh("rm -rf test1 test2 mnt")
    os.mkdir("test1")
    os.mkdir("test2")
    os.mkdir("mnt")

    subprocess.Popen("valgrind --xml=yes --xml-file=valgrind-out.xml "
                    "./mhddfs_noxattr_glib test1,test2 mnt",
                    shell=True)
    time.sleep(1) # Apparantly mhddfs takes some time to start.

    # Touch some files.
    sh("touch test1/1")
    sh("touch test1/2")
    sh("touch test1/3")
    sh("touch test2/4")
    sh("touch test2/5")
    sh("touch test2/6")

    # Do some ls-ing
    assert set(os.listdir("mnt")) == {'1', '2', '3', '4', '5', '6'}
    sh("fusermount -u mnt")

    # valgrind XML is invalid due to fork() in mhddfs (valgrind bug)
    ret = subprocess.call("grep -q '<error>' valgrind-out.xml", shell=True)
    if ret == 0:
        # grep found a match
        raise AssertionError("Memory errors in tested program")

@pytest.fixture
def cleanup(request):
    request.addfinalizer(lambda: subprocess.call("fusermount -uz mnt"))

