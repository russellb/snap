#!/usr/bin/python
#
# Postgresql service backup/restoration adapter
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
import re
import tempfile
import subprocess

from snap.backends.services.dispatcher import Dispatcher

# TODO at some point use the postgresql-python api to
# implement something akin to pg_dump / pg_dumpall
#import psycopg2

# TODO because user may have restricted postgres user access
#  in pg_hba.conf, we switch to the postgres system user before 
#  running the command, should retrieve postgres credentials
#  from a the snap services configuration directory
import pwd

import snap

class Postgresql:

    current_os = snap.osregistry.OS.lookup()
    if current_os == 'fedora' or current_os == 'rhel' or current_os == 'centos':
        DATADIR='/var/lib/pgsql/data'

    elif current_os == 'debian' or current_os == 'ubuntu':
        VERSION=os.listdir('/var/lib/postgresql')[0]
        DATADIR='/var/lib/postgresql/'+VERSION+'/main'

    DAEMON='postgresql'


    def db_exists(dbname):
        '''helper to return boolean indicating if the db w/ the specified name exists'''
        null=open('/dev/null', 'w')

        # switch to the postgres user
        current_euid = os.geteuid()
        os.seteuid(pwd.getpwnam('postgres').pw_uid)

        # retrieve list of db names from postgres
        t = tempfile.TemporaryFile()
        popen = subprocess.Popen(["psql", "-t", "-c", "select datname from pg_database"], stdout=t, stderr=null)
        popen.wait()

        # determine if the specified one is among them
        t.seek(0)
        c = t.read()
        has_db = len(re.findall(dbname, c))

        # switch back to the original user
        os.seteuid(current_euid)

        return has_db
    db_exists=staticmethod(db_exists)

    def set_postgres_user():
        '''helper to set the current user to the postgres system user

        @return current user and homedir'''
        current_euid = os.geteuid()
        current_dir  = os.getcwd()
        pg_user = pwd.getpwnam('postgres')
        os.chdir(pg_user.pw_dir)
        os.seteuid(pg_user.pw_uid)
        return (current_euid, current_dir)
    set_postgres_user=staticmethod(set_postgres_user)

    def restore_user(current_euid, current_dir):
        '''helper to restore the current user / directory after changing w/ set_postgres_user

        @return current user and homedir'''
        os.seteuid(current_euid)
        os.chdir(current_dir)
    restore_user=staticmethod(restore_user)

    def create_db(dbname):
        '''helper to create the specified database'''
        null=open('/dev/null', 'w')

        # switch to the postgres user
        current_euid, current_dir = Postgresql.set_postgres_user()

        # create the db
        popen = subprocess.Popen(["psql", "-c", "CREATE DATABASE " + dbname], stdout=null, stderr=null)
        popen.wait()

        # switch back to the original user
        Postgresql.restore_user(current_euid, current_dir)
    create_db=staticmethod(create_db)

    def drop_db(dbname):
        '''helper to drop the specified database'''
        null=open('/dev/null', 'w')

        # switch to the postgres user
        current_euid, current_dir = Postgresql.set_postgres_user()

        # destroy the db
        popen = subprocess.Popen(["psql", "-c", "DROP DATABASE " + dbname], stdout=null, stderr=null)
        popen.wait()

        # switch back to the original user
        Postgresql.restore_user(current_euid, current_dir)
    drop_db=staticmethod(drop_db)

    def init_db(data_dir=DATADIR):
        '''helper to initialize the database server'''

        # db already initialized, just return
        if os.path.isdir(data_dir) and len(os.listdir(data_dir)) > 0:
            return

        # no need to do this on debian / ubuntu as its already taken care of
        if os == 'debian' or os == 'ubuntu':
            return

        # if the datadir already exists, just return
        if os.path.isdir(data_dir):
            return

        null=open('/dev/null', 'w')

        # FIXME should run initdb manually
        popen = subprocess.Popen(["service", "postgresql", "initdb"], stdout=null)
        popen.wait()
    init_db=staticmethod(init_db)

    def backup(self, basedir):
        # check to see if service is running
        already_running = Dispatcher.service_running(Postgresql.DAEMON)

        # start the postgresql server
        Dispatcher.start_service(Postgresql.DAEMON)

        # switch to the postgres user
        current_euid, current_dir = Postgresql.set_postgres_user()

        # use a pipe to invoke pg_dumpall and capture output
        # FIXME it seems merely switching user id doesn't suffice, need to su to postgres
        outfile = file(basedir + "/dump.psql", "w")
        pipe = subprocess.Popen(["su", "postgres", "-c", "pg_dumpall"], stdout=outfile)
        pipe.wait()

        # switch back to the original user
        Postgresql.restore_user(current_euid, current_dir)

        # if postgresql was running b4hand, start up again
        if not already_running:
            Dispatcher.stop_service(Postgresql.DAEMON)

    def restore(self, basedir):
        null=open('/dev/null', 'w')

        # init the postgresql db
        Postgresql.init_db()

        # start the postgresql service
        Dispatcher.start_service(Postgresql.DAEMON)

        # switch to the postgres user
        current_euid, current_dir = Postgresql.set_postgres_user()

        # use pipe to invoke postgres, restoring database
        infile = file(basedir + "/dump.psql", "r")
        popen = subprocess.Popen("psql", stdin=infile, stdout=null, stderr=null)
        popen.wait()

        # switch back to the original user
        Postgresql.restore_user(current_euid, current_dir)