##########################################################################
# Copyright 2009 Carlos Ribeiro
# Copyright 2012 fbcoder
#
# This file is part of CursedRadio
#
# Radio Tray is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 1 of the License, or
# (at your option) any later version.
#
# Radio Tray is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radio Tray.  If not, see <http://www.gnu.org/licenses/>.
#
##########################################################################
from XmlDataProvider import XmlDataProvider
from XmlConfigProvider import XmlConfigProvider
from AudioPlayerGStreamer import AudioPlayerGStreamer
from events.EventManager import EventManager
from events.EventSubscriber import EventSubscriber
import os
from shutil import move, copy2
from lib.common import APPDIRNAME, USER_CFG_PATH, CFG_NAME, OLD_USER_CFG_PATH,\
    DEFAULT_RADIO_LIST, OPTIONS_CFG_NAME, DEFAULT_CONFIG_FILE,\
   LOGFILE
import logging
from logging import handlers
import gobject

# My own imports
from MyCursesInterface import CursesThread

class RadioTray(object):

    def __init__(self):
        # load configuration
        self.loadConfiguration()
        self.logger.info('**********************')
        self.logger.info('Starting Radio Tray...')
        
        # load bookmarks data provider and initializes it
        self.provider = XmlDataProvider(self.filename)
        self.provider.loadFromFile()

        # load config data provider and initializes it
        self.cfg_provider = XmlConfigProvider(self.cfg_filename)
        self.cfg_provider.loadFromFile()

        # load default config data provider and initializes it
        self.default_cfg_provider = XmlConfigProvider(self.default_cfg_filename)
        self.default_cfg_provider.loadFromFile()

        # load Event Manager
        eventManager = EventManager()

        # load audio player
        self.audio = AudioPlayerGStreamer(self.cfg_provider, eventManager)

        # Start main loop and interface (curses) thread.
        loop = gobject.MainLoop()
        t = CursesThread(self.audio,self.provider,loop)
        eventSubscriber = EventSubscriber(eventManager)
        eventSubscriber.bind(EventManager.SONG_CHANGED, t.updateSong)
        eventSubscriber.bind(EventManager.STATE_CHANGED, t.updateState)
        eventSubscriber.bind(EventManager.BUFFER_CHANGED, t.updateBuffer)
        t.start()
                
        gobject.threads_init()
        loop.run()
        

    def loadConfiguration(self):
        if not os.path.exists(USER_CFG_PATH):
            self.logger.info("user's directory created")
            os.mkdir(USER_CFG_PATH)
            
        self.configLogging()
        self.logger.debug("Loading configuration...")
        self.filename = os.path.join(USER_CFG_PATH, CFG_NAME)
        self.cfg_filename = os.path.join(USER_CFG_PATH, OPTIONS_CFG_NAME)
        self.default_cfg_filename = DEFAULT_CONFIG_FILE

        if not os.access(self.filename, os.F_OK): # If bookmarks file doesn't exist
            self.logger.warn('bookmarks file could not be found. Using default...')
            #check if it exists an old bookmark file, and then move it to the new location
            oldfilename = os.path.join(OLD_USER_CFG_PATH, CFG_NAME)
            if os.access(oldfilename, os.R_OK|os.W_OK):
                self.logger.info('Found old bookmark configuration and moved it to new location: %s', USER_CFG_PATH)
                move(oldfilename, self.filename)
                os.rmdir(OLD_USER_CFG_PATH)
            else:
                self.logger.info('Copying default bookmarks file to user directory')
                copy2(DEFAULT_RADIO_LIST, self.filename)

        if not os.access(self.cfg_filename, os.R_OK|os.W_OK):
            self.logger.warn('Configuration file not found. Copying default configuration file to user directory')
            copy2(DEFAULT_CONFIG_FILE, self.cfg_filename)


    def configLogging(self):
        # config general logging
        self.logger = logging.getLogger('radiotray')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler(LOGFILE, maxBytes=2000000, backupCount=1)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        #config curses logging:
        self.cursesLogger = logging.getLogger('curses')
        self.cursesLogger.setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler(os.path.join(USER_CFG_PATH,'curses.log'), maxBytes=2000000, backupCount=1)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.cursesLogger.addHandler(handler)
        self.cursesLogger.info('******************')
        self.cursesLogger.info('**  Curses Log  **')
        self.cursesLogger.info('******************')


if __name__ == "__main__":
        radio = RadioTray()
