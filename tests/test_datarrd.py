# -*- coding: utf-8 -*-

"""Unittests for Janitoo-Roomba Server.
"""
__license__ = """
    This file is part of Janitoo.

    Janitoo is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Janitoo is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Janitoo. If not, see <http://www.gnu.org/licenses/>.

"""
__author__ = 'Sébastien GALLET aka bibi21000'
__email__ = 'bibi21000@gmail.com'
__copyright__ = "Copyright © 2013-2014-2015 Sébastien GALLET aka bibi21000"

import sys, os
import time, datetime
import unittest
import threading
import logging
from logging.config import fileConfig as logging_fileConfig
from pkg_resources import iter_entry_points
import mock

from janitoo_nosetests.server import JNTTServer, JNTTServerCommon
from janitoo_nosetests.thread import JNTTThread, JNTTThreadCommon

from janitoo.utils import json_dumps, json_loads
from janitoo.utils import HADD_SEP, HADD
from janitoo.utils import TOPIC_HEARTBEAT
from janitoo.utils import TOPIC_NODES, TOPIC_NODES_REPLY, TOPIC_NODES_REQUEST
from janitoo.utils import TOPIC_BROADCAST_REPLY, TOPIC_BROADCAST_REQUEST
from janitoo.utils import TOPIC_VALUES_USER, TOPIC_VALUES_CONFIG, TOPIC_VALUES_SYSTEM, TOPIC_VALUES_BASIC
from janitoo.runner import jnt_parse_args

from janitoo_datalog_rrd.thread import RrdThread
##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_DISCOVERY = 0x5000

assert(COMMAND_DESC[COMMAND_DISCOVERY] == 'COMMAND_DISCOVERY')
##############################################################

class TestDataRrdThread(JNTTThread, JNTTThreadCommon):
    """Test the datarrd thread
    """
    thread_name = "datarrd"
    conf_file = "tests/data/janitoo_datalog.conf"

    def test_101_thread_start_wait_long_stop(self):
        if self.conf_file is None:
            self.skipTest("No configuration file provided")
        logging_fileConfig(self.conf_file)
        self.assertFalse(self.thread_name is None)
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=%s'%self.conf_file]):
            options = vars(jnt_parse_args())
        th = self.factory[self.thread_name](options)
        th.start()
        time.sleep(60)
        self.assertFile("/tmp/janitoo_test/home/public/rrd/rrds/num_threads.rrd")
        self.assertFile("/tmp/janitoo_test/home/public/rrd/rrds/index.txt")
        th.stop()

class TestHttpThread(JNTTThread, JNTTThreadCommon):
    """Test the datarrd thread
    """
    thread_name = "http"
    conf_file = "tests/data/janitoo_datalog.conf"

    def test_101_thread_start_wait_long_stop(self):
        if self.conf_file is None:
            self.skipTest("No configuration file provided")
        logging_fileConfig(self.conf_file)
        self.assertFalse(self.thread_name is None)
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=%s'%self.conf_file]):
            options = vars(jnt_parse_args())
        th = self.factory[self.thread_name](options)
        th.start()
        time.sleep(60)
        self.assertFile("/tmp/janitoo_test/home/public/rrd/index.html")
        #~ self.assertFile("/tmp/janitoo_test/home/public/rrd/js/javascriptrrd.wlibs.js")
        th.stop()
