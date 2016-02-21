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

import warnings
warnings.filterwarnings("ignore")

import sys, os
import time, datetime
import unittest
import threading
import logging
from logging.config import fileConfig as logging_fileConfig
from pkg_resources import iter_entry_points
import mock

sys.path.insert(0,os.path.dirname(__name__))

from janitoo_nosetests.server import JNTTServer, JNTTServerCommon
from janitoo_nosetests.thread import JNTTThread, JNTTThreadCommon
from janitoo_nosetests.thread import JNTTThreadRun, JNTTThreadRunCommon

from janitoo.utils import json_dumps, json_loads
from janitoo.utils import HADD_SEP, HADD
from janitoo.utils import TOPIC_HEARTBEAT
from janitoo.utils import TOPIC_NODES, TOPIC_NODES_REPLY, TOPIC_NODES_REQUEST
from janitoo.utils import TOPIC_BROADCAST_REPLY, TOPIC_BROADCAST_REQUEST
from janitoo.utils import TOPIC_VALUES_USER, TOPIC_VALUES_CONFIG, TOPIC_VALUES_SYSTEM, TOPIC_VALUES_BASIC
from janitoo.runner import jnt_parse_args

from janitoo_datalog_rrd.thread import RrdThread

class TestDataRrdThread(JNTTThreadRun, JNTTThreadRunCommon):
    """Test the datarrd thread
    """
    thread_name = "datarrd"
    conf_file = "tests/data/janitoo_datalog.conf"

    def test_101_thread_start_wait_long_stop(self):
        self.thread.start()
        try:
            self.assertHeartbeatNode(hadd=HADD%(1014, 0001))
            time.sleep(31)
            self.assertFile("/tmp/janitoo_test/home/public/rrd/rrds/num_threads.rrd")
            self.assertFile("/tmp/janitoo_test/home/public/rrd/rrds/index.txt")
            self.assertFile("/tmp/janitoo_test/home/rrd/rrd_cache.pickle")
        finally:
            self.thread.stop()

class TestHttpThread(JNTTThreadRun, JNTTThreadRunCommon):
    """Test the datarrd thread
    """
    thread_name = "http"
    conf_file = "tests/data/janitoo_datalog.conf"

    def test_101_thread_start_wait_long_stop(self):
        self.thread.start()
        try:
            self.assertHeartbeatNode(hadd=HADD%(1018, 0001))
            self.assertDir("/tmp/janitoo_test/home/public/rrd/js")
            self.assertDir("/tmp/janitoo_test/home/public/rrd/css")
            self.assertDir("/tmp/janitoo_test/home/public/rrd/images")
            self.assertFile("/tmp/janitoo_test/home/public/rrd/index.html")
            self.assertFile("/tmp/janitoo_test/home/public/rrd/js/javascriptrrd.wlibs.js")
        finally:
            self.thread.stop()
