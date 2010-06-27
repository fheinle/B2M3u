#!/usr/bin/env python
# -*- coding:utf-8 -*-

""" export playlists from Banshee to m3u files

What this script does is read banshee playlists and copy song files
to a flat directory. Additionally, an m3u file is created to preserve
user selected ordering of playlists


Copyright (c) 2010 Florian Heinle <launchpad@planet-tiax.de>
"""

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.


from sqlalchemy import create_engine
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relation
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from urllib import unquote
from shutil import copy
from sys import getfilesystemencoding
import os

banshee_db = os.path.expanduser('~/.config/banshee-1/banshee.db')
engine = create_engine('sqlite:///%s' % banshee_db)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Track(Base):
    """Track in Banshee's database

    contains Uris instead of filenames and is referenced from
    PlaylistEntry"""
    __tablename__ = 'CoreTracks'

    TrackID = Column(Integer, primary_key=True)
    ArtistID = Column(Integer)
    Uri = Column(String)
    Title = Column(String)

    def __init__(self, **kwargs):
        for key, value in kwargs:
            setattr(self, key, value)

    def __repr__(self):
        return "<Track('%s')>" % self.Title

class Playlist(Base):
    """Playlist in Banshee's database

    contains not much more than Playlist Names and provides an ID for 
    reference by PlaylistEntry"""
    __tablename__ = 'CorePlaylists'

    PlaylistID = Column(Integer, primary_key=True)
    Name = Column(String)
    Special = Column(Integer)

    def __init__(self, **kwargs):
        for key, value in kwargs:
            setattr(self, key, value)

    def __repr__(self):
        return "<Playlist('%s', id '%s')>" % (self.Name, self.PlaylistID)

class PlaylistEntry(Base):
    """PlaylistEntry in Banshee's database

    contains TrackID/PlaylistID pairs and their ordering in playlists"""
    __tablename__ = 'CorePlaylistEntries'

    EntryID = Column(Integer, primary_key=True)
    PlaylistID = Column(Integer, ForeignKey('CorePlaylists.PlaylistID'))
    TrackID = Column(Integer, ForeignKey('CoreTracks.TrackID'))
    ViewOrder = Column(Integer)

    playlist = relation(Playlist,
                        order_by=ViewOrder,
                        backref='playlist_tracks'
                       )
    track = relation(Track,
                     order_by=ViewOrder,
                     backref='track'
                    )

    def __init__(self, **kwargs):
        for key, value in kwargs:
            setattr(self, key, value)

def get_regular_playlists():
    """return all user-created playlists, excepting play queues etc"""
    session = Session()
    playlists = session.query(Playlist).filter_by(Special=0)
    return playlists.all()

def get_song_uris_in_playlist(playlist_id):
    """read playlist contents"""
    session = Session()
    query = session.query(PlaylistEntry).filter_by(PlaylistID=playlist_id)\
                                        .order_by(PlaylistEntry.ViewOrder) 
    uris = [playlist_entry.track.Uri for playlist_entry in query.all()]
    return uris

def normalize_filename(uri):
    """convert URIs used by banshee to normal filenames"""
    # TODO: support gvfs uris
    assert uri.startswith('file:///'), 'Only local files supported'
    filename = unquote(uri.encode(getfilesystemencoding())[7:])
    return filename

def save_playlist(playlist_id, target):
    """save songs from a playlist to a directory and write m3u file"""
    if not os.path.isdir(target):
        os.makedirs(target)
    playlist = get_song_uris_in_playlist(playlist_id)
    playlist_file = open(os.path.join(target, '%s.m3u' % target), 'w')
    for track in playlist: 
        source = normalize_filename(track)
        copy(source, target)
        basename = os.path.basename(source)
        playlist_file.write(basename + '\n')
        print "Added %s" % basename
    playlist_file.close()
