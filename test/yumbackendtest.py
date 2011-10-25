#!/usr/bin/python
#
# test/sfilemetadatatest.py unit test suite for snap.metadata.sfile
#
# (C) Copyright 2011 Mo Morsi (mo@morsi.org)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License, Version 3,
# as published by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import os
import shutil
import unittest

import yum

import snap
import snap.backends.files.syum
import snap.backends.repos.syum
import snap.backends.packages.syum

from snap.metadata.sfile   import FilesRecordFile
from snap.metadata.package import PackagesRecordFile

class YumBackendTest(unittest.TestCase):
    def setUp(self):
        self.fs_root = os.path.join(os.path.dirname(__file__), "data/fs_root")
        os.mkdir(self.fs_root)

        self.basedir = os.path.join(os.path.dirname(__file__), "data/basedir")
        os.mkdir(self.basedir)

    def tearDown(self):
        shutil.rmtree(self.fs_root)
        shutil.rmtree(self.basedir)

    def testBackupRepos(self):
        snapshot_target = snap.backends.repos.syum.Syum()
        snapshot_target.backup(self.fs_root)

        self.assertTrue(os.path.exists(self.fs_root + "/etc/yum.conf"))
        for repo in os.listdir("/etc/yum.repos.d"):
            self.assertTrue(os.path.exists(self.fs_root + "/etc/yum.repos.d/" + repo))


    def testRestoreRepos(self):
        os.makedirs(self.basedir + "/etc/yum.repos.d")
        f=open(self.basedir + "/etc/yum.conf" , 'w')
        f.write("foo")
        f.close()
        f=open(self.basedir + "/etc/yum.repos.d/foo.repo" , 'w')
        f.write("bar")
        f.close()

        restore_target = snap.backends.repos.syum.Syum()
        restore_target.fs_root = self.fs_root
        restore_target.restore(self.basedir)

        self.assertTrue(os.path.exists(self.fs_root + self.basedir + "/etc/yum.conf"))
        self.assertTrue(os.path.exists(self.fs_root + self.basedir + "/etc/yum.repos.d/foo.repo"))

    def testBackupPackages(self):
        backup_target = snap.backends.packages.syum.Syum()
        backup_target.backup(self.fs_root)

        pkgs = []
        record = PackagesRecordFile(self.fs_root + "/packages.xml")
        record_packages = record.read()
        for pkg in record_packages:
            pkgs.append(pkg.name)

        # ensure all the system's packages have been recorded
        for pkg in yum.YumBase().rpmdb:
            self.assertIn(pkg.name, pkgs)

    # FIXME get this test working
    #def testRestorePackages(self):
    #    restore_target = snap.backends.packages.syum.Syum()
    #    restore_target.backup(self.fs_root)
    #    restore_target.restore(self.fs_root)

    #    record = PackagesRecordFile(self.fs_root + "packages.xml")
    #    record_packages = record.read()

    #    lyum = yum.YumBase()
    #    lyum.rpmdb.dbpath = self.fs_root + '/var/lib/rpm'
    #    
    #    for pkg in record_packages:
    #        self.assertIn(pkg, lyum.rpmdb)

    def testBackupFiles(self):
        f=open(self.fs_root + "/foo" , 'w')
        f.write("foo")
        f.close()

        backup_target = snap.backends.files.syum.Syum()
        backup_target.backup(self.basedir, include=[self.fs_root])

        self.assertTrue(os.path.exists(self.basedir + self.fs_root + "/foo"))

        record = FilesRecordFile(self.basedir + "/files.xml")
        files = record.read()
        file_names = []
        for sfile in files:
            file_names.append(sfile.name)
        self.assertIn("foo", file_names)
        self.assertEqual(1, len(files))

    def testRestoreFiles(self):
        f=open(self.fs_root + "/foo" , 'w')
        f.write("foo")
        f.close()

        backup_target = snap.backends.files.syum.Syum()
        backup_target.backup(self.basedir, include=[self.fs_root])

        shutil.rmtree(self.fs_root)
        os.mkdir(self.fs_root)

        restore_target = snap.backends.files.syum.Syum()
        restore_target.fs_root = self.fs_root
        restore_target.restore(self.basedir)

        self.assertTrue(os.path.exists(self.fs_root + self.fs_root + "/foo"))