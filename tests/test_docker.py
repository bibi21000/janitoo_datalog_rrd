# -*- coding: utf-8 -*-

"""Unittests for Janitoo-common.
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
__copyright__ = "Copyright © 2013-2014-2015-2016 Sébastien GALLET aka bibi21000"

import warnings
warnings.filterwarnings("ignore")

import sys, os
import time
import unittest
import logging
import threading
import mock
import logging

from janitoo_nosetests import JNTTBase
from janitoo_nosetests.server import JNTTDockerServerCommon, JNTTDockerServer

from janitoo.runner import Runner, jnt_parse_args
from janitoo.server import JNTServer
from janitoo.utils import HADD_SEP, HADD

from janitoo_datalog_rrd.server import DatalogServer

class TestDatalogRRDSerser(JNTTDockerServer, JNTTDockerServerCommon):
    """Test the server
    """
    loglevel = logging.DEBUG
    path = '/tmp/janitoo_test'
    broker_user = 'toto'
    broker_password = 'toto'
    server_class = DatalogServer
    server_conf = "tests/data/janitoo_datalog.conf"
    hadds=[HADD%(1014,0), HADD%(1014,1), HADD%(1018,0), HADD%(1018,1)]

    def test_040_server_start_no_error_in_log(self):
        JNTTDockerServerCommon.test_040_server_start_no_error_in_log(self)
        self.assertFile("/tmp/janitoo_test/home/rrd/rrd_cache.pickle")
        self.assertFile("/tmp/janitoo_test/home/public/rrd/rrds/num_threads.rrd")
        self.assertFile("/tmp/janitoo_test/home/public/rrd/rrds/index.txt")
        self.assertDir("/tmp/janitoo_test/home/public/rrd/js")
        self.assertDir("/tmp/janitoo_test/home/public/rrd/css")
        self.assertDir("/tmp/janitoo_test/home/public/rrd/images")
        self.assertFile("/tmp/janitoo_test/home/public/rrd/index.html")
        self.assertFile("/tmp/janitoo_test/home/public/rrd/js/javascriptrrd.wlibs.js")
