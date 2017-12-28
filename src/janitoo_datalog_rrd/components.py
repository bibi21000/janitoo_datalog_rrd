# -*- coding: utf-8 -*-
"""The Raspberry hardware worker

Define a node for the cpu with 3 values : temperature, frequency and voltage

http://www.maketecheasier.com/finding-raspberry-pi-system-information/

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

# Set default logging handler to avoid "No handler found" warnings.
import logging
logger = logging.getLogger(__name__)

import os
import threading
import pickle
import datetime
from pkg_resources import get_distribution, DistributionNotFound
from janitoo.thread import JNTBusThread, BaseThread
from janitoo.options import get_option_autostart
from janitoo.utils import HADD, HADD_SEP
from janitoo.utils import TOPIC_VALUES_USERS
from janitoo.utils import json_dumps, json_loads
from janitoo.component import JNTComponent
from janitoo.node import JNTNode
from janitoo.value import JNTValue
from janitoo.bus import JNTBus
from janitoo.mqtt import MQTTClient
from janitoo_factory.threads.http import BasicResourceComponent
from janitoo_datalog_rrd.bus import RRD_DIR
import rrdtool

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_CONTROLLER = 0x1050

assert(COMMAND_DESC[COMMAND_CONTROLLER] == 'COMMAND_CONTROLLER')
##############################################################

def make_datasource(**kwargs):
    return RrdDatasource(**kwargs)

def make_http_resource(**kwargs):
    return RrdResourceComponent(**kwargs)

class RrdDatasource(JNTComponent):
    """ Use psutil to retrieve informations. """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        JNTComponent.__init__(self, 'datarrd.datasource', bus=bus, addr=addr, name="RRD Datasource",
                product_name="RRD Datasource", product_type="Software", product_manufacturer="RRD", **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)
        self._lock =  threading.Lock()

        uuid="source"
        self.values[uuid] = self.value_factory['sensor_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            get_data_cb=self.get_rrd_label,
            help='The source label',
            label='Source label',
            genre=0x01,
        )
        config_value = self.values[uuid].create_config_value(help='The configuration of the rrd source : hadd|value_uuid|value_index|rrd_type|rrd_label', label='Rrd Config', type=0x16)
        self.values[config_value.uuid] = config_value
        poll_value = self.values[uuid].create_poll_value(default=900)
        self.values[poll_value.uuid] = poll_value

        uuid="rrd_file"
        self.values[uuid] = self.value_factory['config_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The name of the rrd file. Must be unique on the server.',
            label='Rrd file',
            default='default_rrd',
        )

        uuid="rrd_step"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The Rrd step',
            label='Rrd test',
            default=300,
        )

        uuid="http_file"
        self.values[uuid] = self.value_factory['sensor_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            get_data_cb=self.get_http_rrd_file,
            help='The http address of the rrd file',
            label='http',
            genre=0x01,
        )

    def check_heartbeat(self):
        """Check that the component is 'available'
        """
        #~ print "it's me %s : %s" % (self.values['upsname'].data, self._ups_stats_last)
        if self._bus.store is None:
            return False
        filename = self._bus.store.get_rrd_filename(self.values['rrd_file'].data)
        if filename is None:
            return False
        return os.path.exists(filename)

    def start(self, mqttc):
        """Start the component.
        """
        logger.warning("[%s] - Start component : %s ", self.__class__.__name__, self.values['rrd_file'].data)
        JNTComponent.start(self, mqttc)
        value_source = self.values['source']
        config = {}
        for i in range(0, value_source.get_max_index()+1):
            config[i] = value_source.get_config(value_source.node_uuid, i)
        self._bus.store.timer_add_config(self.values['rrd_file'].data, self.values['rrd_step'].data, config)
        return True

    def stop(self):
        """Stop the component.
        """
        JNTComponent.stop(self)
        return True

    def get_http_rrd_file(self, node_uuid, index):
        """
        """
        if self._bus.store is not None:
            value_source = self.values['source']
            config = value_source.get_config(value_source.node_uuid, index)
            if config is None:
                return None
            return self._bus.store.get_rrd_httpname(self.values['rrd_file'].data)
        return None

    def get_rrd_label(self, node_uuid, index):
        """
        """
        if self._bus.store is not None:
            value_source = self.values['source']
            config = value_source.get_config(value_source.node_uuid, index)
            if config is None:
                return None
            return self._bus.store.get_rrd_label(index, self.values['rrd_file'].data, config)
        return None

    def get_package_name(self):
        """Return the name of the package. Needed to publish static files

        **MUST** be copy paste in every extension that publish statics files
        """
        return __package__

class RrdResourceComponent(BasicResourceComponent):
    """ A resource ie /rrd """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        BasicResourceComponent.__init__(self, path=RRD_DIR, oid='http.rrd', bus=bus, addr=addr, name="Http rrd resource",
                product_name="HTTP rrd resource", **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

    def get_package_name(self):
        """Return the name of the package. Needed to publish static files

        **MUST** be copy paste in every extension that publish statics files
        """
        return __package__

    def check_heartbeat(self):
        """Check that the component is 'available'
        """
        return self.check_heartbeat_file(RRD_DIR)
