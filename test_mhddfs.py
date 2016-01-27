#!/usr/bin/env python3
import pytest
import os, shutil, subprocess
import time
import random
import string
import multiprocessing

def sh(cmd):
    import subprocess
    subprocess.check_call(cmd, shell=True)

def test_readdir(mhddfs):
    """Simple test that readdir() is working.  Previously, this test would
        trigger memory errors detectable by valgrind."""
    # Touch some files.
    sh("touch test1/1")
    sh("touch test1/2")
    sh("touch test1/3")
    sh("touch test2/4")
    sh("touch test2/5")
    sh("touch test2/6")

    # ls the aggregated directory to show they're all there.
    assert set(os.listdir("mnt")) == {'1', '2', '3', '4', '5', '6'}

def rewrite_and_rename(i):
    file = "mnt/testfile"

    with open(file) as f:
        text = f.read()
    tmp_file = file + '.tmp.' + ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
    with open(tmp_file, 'w') as f:
        f.write(text)
    os.rename(tmp_file, file)

def test_parallel_rename(mhddfs):
    """Create a file with some text, and then have some threads constantly copy
        and rename over it.  If the rename() operation is atomic, we should
        never see a "File does not exist" error.
    """
    str = "hello, world"
    file = "mnt/testfile"

    # Create an empty file
    with open(file, 'w') as f:
        f.write(str)

    # Try doing lots of writes in parallel.
    pool = multiprocessing.Pool(5)
    num = 1000
    for _ in range(10):
        rewrite_and_rename(0)
    for _ in pool.imap_unordered(rewrite_and_rename, range(num)):
        pass

    with open(file, 'r') as f:
        assert f.read() == str

def assert_valgrind():
    """Check that valgrind hasn't detected errors."""
    # valgrind XML is invalid due to fork() in mhddfs (valgrind bug)
    ret = subprocess.call("grep -q '<error>' valgrind-out.xml", shell=True)
    if ret == 0:
        # grep found a match
        raise AssertionError("Memory errors in tested program")

@pytest.fixture
def nomhddfs(request):
    os.mkdir("mnt")

    def cleanup():
        sh("rm -rf mnt")

    request.addfinalizer(cleanup)

@pytest.fixture
def mhddfs(request):
    sh("rm -rf test1 test2 mnt")
    os.mkdir("test1")
    os.mkdir("test2")
    os.mkdir("mnt")

    valgrind = True
    if valgrind:
        prefix = "valgrind --xml=yes --xml-file=valgrind-out.xml "
    else:
        prefix = ""

    subprocess.Popen(prefix + "./mhddfs test1,test2 mnt",
                    shell=True)
    time.sleep(1) # Apparantly mhddfs takes some time to start.

    def cleanup():
        sh("fusermount -u mnt")
        subprocess.call("fusermount -uz mnt", shell=True)
        sh("rm -rf test1 test2 mnt")
        if valgrind:
            assert_valgrind()

    request.addfinalizer(cleanup)

