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
__copyright__ = "Copyright © 2013-2014-2015 Sébastien GALLET aka bibi21000"

# Set default logging handler to avoid "No handler found" warnings.
import logging
logger = logging.getLogger(__name__)

import os, sys
import threading
import pickle
import datetime
from pkg_resources import get_distribution, DistributionNotFound
from janitoo.thread import JNTBusThread, BaseThread
from janitoo.options import get_option_autostart
from janitoo.utils import HADD, HADD_SEP
from janitoo.utils import TOPIC_VALUES_USERS, TOPIC_VALUES
from janitoo.utils import json_dumps, json_loads
from janitoo.component import JNTComponent
from janitoo.node import JNTNode
from janitoo.value import JNTValue
from janitoo.classes import COMMAND_DESC
from janitoo.bus import JNTBus
from janitoo.mqtt import MQTTClient
import rrdtool

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_CONTROLLER = 0x1050

assert(COMMAND_DESC[COMMAND_CONTROLLER] == 'COMMAND_CONTROLLER')
##############################################################

RRD_DIR = "rrd"

class RrdStoreThread(BaseThread):
    """The Rdd cache thread

    Implement a cache.

    """
    def __init__(self, section, options={}):
        """Initialise the cache thread

        Manage a cache for the rrd.

        A timer in a separated thread will pickle the cache to disk every 30 seconds.

        An other thread will update the rrd every hours

        :param options: The options used to start the worker.
        :type clientid: str
        """
        self.section = section
        BaseThread.__init__(self, options=options)
        self.config_timeout_delay = 1
        self.loop_sleep = 0.01
        self._lock = threading.Lock()
        #~ self._cache_rrd_ttl = 60*60
        self._cache_rrd_ttl = 60*60
        self._cache_pickle_ttl = 240
        self._cache_pickle_timer = None
        self._cache_dead_ttl = 60*60*24
        self._cache_dead_timer = None
        self._thread_delay = 0.01
        self._rrd_rotate_next_run = None
        self._rrd_rotate_ttl = 1
        self._dirmask = None
        self._filemask = None
        self._cache = {}
        """
        whe have a datasource with a unique_name haddnode but at component start, we don't have it.
        whe receive data from mqtt with params : haddvalue, value_uuid, value_index at etime

        whe should update the rrd with : rtime:val1:val2:val3 ...

        Whe should be abble to flush a rrd file for graphing

        cache { 'rrd_0001' : { 'step':300, 'values' : {'epoch_time' : { 0 : 'U', ...}}, 'labels':{0:...}}

        When updating a data, we can find the latest serie values filtering on epoch_time

        We should look at the cache to find rrd_files that need a new serie of values (now - last_epoch) > step.
        In this case, we add a new serie of with 'U' as values.

                hadd
                    value_uuid
                        value_index
        """
        self.epoch = datetime.datetime(1970,1,1)
        self._mqttc = None
        """
        """
        self.params = {}

    def config_thread(self, cache_rrd_ttl=None, cache_pickle_ttl=None, cache_dead_ttl=None,
                    dirmask=RRD_DIR, filemask='%(rrd_file)s.rrd'):
        """
        """
        if dirmask is not None:
            self._dirmask = dirmask
        if filemask is not None:
            self._filemask = filemask
        if cache_rrd_ttl is not None:
            self._cache_rrd_ttl = cache_rrd_ttl
        if cache_dead_ttl is not None:
            self._cache_dead_ttl = cache_dead_ttl
        if cache_pickle_ttl is not None:
            self._cache_pickle_ttl = cache_pickle_ttl

    def pre_loop(self):
        """Launch before entering the run loop. The node manager is available.
        """
        self._mqttc = MQTTClient(options=self.options.data)
        self._mqttc.connect()
        self._mqttc.subscribe(topic=TOPIC_VALUES, callback=self.on_value)
        self._mqttc.start()
        self.restore()
        self.start_timer_pickle()
        self._rrd_rotate_next_run = datetime.datetime.now()
        self.start_timer_dead()

    def post_loop(self):
        """Launch after finishing the run loop. The node manager is still available.
        """
        logger.debug("stop_timer_pickle in postloop")
        self.stop_timer_pickle()
        self.stop_timer_dead()
        self._mqttc.unsubscribe(topic=TOPIC_VALUES)
        self._mqttc.stop()
        #~ self.flush_all()
        self.dump()
        if self._mqttc.is_alive():
            self._mqttc.join()
        self._mqttc = None

    def loop(self):
        """Launch after finishing the run loop. The node manager is still available.
        """
        if self._rrd_rotate_next_run < datetime.datetime.now():
            now = datetime.datetime.now()
            #Check for data that need a rotation
            etime = (datetime.datetime.now() - self.epoch).total_seconds()
            try:
                for key in self._cache.keys():
                    try:
                        epochs = sorted(self._cache[key]['values'].keys())
                        #~ print "epochs : ", epochs
                        #~ print "condition : ", epochs[0] + self._cache_rrd_ttl, etime
                        if len(epochs) == 0 or etime > epochs[-1] + self._cache[key]['step']:
                            #We should rotate the values
                            self.timer_rrd_rotate(key, etime)
                        elif len(epochs) > 1 and epochs[0] + self._cache_rrd_ttl < etime :
                            #We should flush to the rrd
                            self.flush(key)
                    except:
                        logger.exception("[%s] - Exception when rotating %s in cache", self.__class__.__name__, key)
            except:
                logger.exception("[%s] - Exception when rotating in cache", self.__class__.__name__)
            self._rrd_rotate_next_run = datetime.datetime.now() + datetime.timedelta(seconds=self._rrd_rotate_ttl)
        self._reloadevent.wait(self.loop_sleep)

    def on_value(self, client, userdata, message):
        """On value

        Do not lock as it don't add new values to dict. Should be ok using keys instead of iterator.

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        #logger.debug("[%s] - on_value %s", self.__class__.__name__, message.payload)
        try:
            data = json_loads(message.payload)
            if 'genre' in data:
                data = {0:{0:data}}
            elif 'genre' in data[data.keys()[0]]:
                data = {0:data}
            store_index = self.create_store_index()
            for nval in data:
                for kval in data[nval]:
                    if data[nval][kval]['genre'] in [0x02, 0x01]:
                        hadd = data[nval][kval]['hadd']
                        uuid = data[nval][kval]['uuid']
                        index = 0
                        if 'index' in data[nval][kval]:
                            index = data[nval][kval]['index']
                        index = str(index)
                        #~ logger.debug("[%s] - update_last %s,%s,%s : %s", self.__class__.__name__, hadd, value_uuid, value_index)
                        if (hadd, uuid, index) in store_index:
                            self.update_last(hadd, uuid, index, data[nval][kval]['data'])
        except:
            logger.exception("[%s] - Exception in on_value", self.__class__.__name__)

    def create_store_index(self):
        """ Create an in dex of keys
            :ret: a list of tuple () of values in cache
        """
        ret = []
        rrds = self._cache.keys()
        for rrd in rrds:
            try:
                indexes = self._cache[rrd]['indexes'].keys()
                for index in indexes:
                    try:
                        ret.append( (self._cache[rrd]['hadds'][index], \
                                     self._cache[rrd]['uuids'][index], \
                                     self._cache[rrd]['indexes'][index]) )
                    except:
                        logger.exception('[%s] - Exception in create_store_index : rrd= %s, index = %s', self.__class__.__name__, rrd, index)
            except:
                logger.exception('[%s] - Exception in create_store_index : rrd = %s', self.__class__.__name__, rrd)
        #~ logger.debug("[%s] - create_store_index %s", self.__class__.__name__, ret)
        return ret

    def update_last(self, hadd, value_uuid, value_index, data):
        """ An helper to find
            :ret:
        """
        #~ logger.debug("[%s] - update_last %s,%s,%s : %s", self.__class__.__name__, hadd, value_uuid, value_index, data)
        ret = []
        rrds = self._cache.keys()
        for rrd in rrds:
            indexes = self._cache[rrd]['indexes'].keys()
            for index in indexes:
                if self._cache[rrd]['hadds'][index]==hadd and \
                        self._cache[rrd]['uuids'][index]==value_uuid and \
                        self._cache[rrd]['indexes'][index]==value_index:
                    epochs = sorted(self._cache[rrd]['values'].keys())
                    if len(epochs) == 0:
                        logger.warning("[%s] - Can't update value. No epoch found for %s", self.__class__.__name__, rrd)
                    else:
                        if data is None:
                            data = 'U'
                        self._cache[rrd]['values'][epochs[-1]][index] = data
                        self._cache[rrd]['last_update'] = datetime.datetime.now()
                        logger.debug("[%s] - Value updated in store %s,%s,%s : %s", self.__class__.__name__, hadd, value_uuid, value_index, data)

    def timer_rrd_rotate(self, rrd_file, etime=None):
        """Rotate via a separate thread in a timer
        """
        if rrd_file is None or rrd_file not in self._cache:
            return False
        if etime is None:
            etime = (datetime.datetime.now() - self.epoch).total_seconds()
        th = threading.Timer(self._thread_delay, self.rrd_rotate, args=(rrd_file, etime))
        th.start()

    def rrd_rotate(self, rrd_file, etime=None):
        """Rotate
        """
        if etime is None:
            etime = (datetime.datetime.now() - self.epoch).total_seconds()
        logger.debug("Rotate the rrd data in cache")
        self._lock.acquire()
        try:
            if rrd_file is None or rrd_file not in self._cache:
                return False
            self._cache[rrd_file]['values'][etime] = {}
            for key in self._cache[rrd_file]['hadds'].keys():
                self._cache[rrd_file]['values'][etime][key]='U'
        except:
            logger.exception("[%s] - Exception when rotating %s in cache", self.__class__.__name__, rrd_file)
        finally:
            self._lock.release()

    def run(self):
        """Run the loop
        """
        self._stopevent.clear()
        #~ self.boot()
        self.trigger_reload()
        logger.debug("[%s] - Wait for the thread reload event for initial startup", self.__class__.__name__)
        while not self._reloadevent.isSet() and not self._stopevent.isSet():
            self._reloadevent.wait(0.50)
        logger.debug("[%s] - Entering the thread loop", self.__class__.__name__)
        while not self._stopevent.isSet():
            self._reloadevent.clear()
            try:
                self.pre_loop()
            except:
                logger.exception('[%s] - Exception in pre_loop', self.__class__.__name__)
                self._stopevent.set()
            while not self._reloadevent.isSet() and not self._stopevent.isSet():
                self.loop()
            try:
                self.post_loop()
            except:
                logger.exception('[%s] - Exception in post_loop', self.__class__.__name__)

    def get_rrd_directory(self, params):
        """Get and create the direcotry if needed
        """
        dirname='.'
        if 'home_dir' in self.options.data and self.options.data['home_dir'] is not None:
            dirname = self.options.data['home_dir']
        directory = os.path.join(dirname, self._dirmask %(params))
        if not os.path.exists(directory):
            os.makedirs(directory)
        return directory

    def get_rrd_public_directory(self, params):
        """Get and create the direcotry if needed
        """
        dirname='.'
        if 'home_dir' in self.options.data and self.options.data['home_dir'] is not None:
            dirname = self.options.data['home_dir']
        dirname = os.path.join(dirname, "public")
        directory = os.path.join(dirname, 'rrd', 'rrds')
        if not os.path.exists(directory):
            os.makedirs(directory)
        return directory

    def get_rrd_file(self, params):
        """
        """
        return self._filemask %(params)

    def get_pickle_filename(self):
        """Restore data from disk using pickle
        """
        params={"rrd_file":''}
        dirname = self.get_rrd_directory(params)
        return os.path.join(dirname, 'rrd_cache.pickle')

    def get_list_filename(self):
        """Restore data from disk using pickle
        """
        params={"rrd_file":''}
        directory = self.get_rrd_public_directory(params)
        return os.path.join(directory, "index.txt")

    def get_rrd_filename(self, rrd_file):
        """
        """
        if rrd_file is None:
            logger.debug("Can't retrieve rrd_file %s", rrd_file)
            return None
        params={"rrd_file":rrd_file}
        directory = self.get_rrd_public_directory(params)
        filename = self.get_rrd_file(params)
        return os.path.join(directory, filename)

    def get_rrd_httpname(self, rrd_file):
        """
        """
        if rrd_file is None:
            logger.debug("Can't retrieve rrd_file %s", rrd_file)
            return None
        params={"rrd_file":rrd_file}
        directory = self._dirmask %(params)
        filename = self.get_rrd_file(params)
        return os.path.join(directory, 'rrds', filename)

    def get_rrd_label(self, index, rrd_file, config):
        """
        """
        if config is None:
            if rrd_file in self._cache and index in self._cache[rrd_file]["labels"]:
                return self._cache[rrd_file]["labels"][index]
        try:
            hadd = None
            hadd, value_uuid, value_index, rrd_type, rrd_label = config.split('|')
            self._cache[rrd_file]["labels"][index] = rrd_label
            return rrd_label
        except:
            logger.exception("Can't retrieve add_ctrl, add_node from hadd %s", hadd)
            return None

    def dump(self):
        """Dump data to disk using pickle
        """
        self._lock.acquire()
        logger.debug("Dump cache to disk")
        try:
            filename = self.get_pickle_filename()
            pickle.dump( self._cache, open( filename, "wb" ) )
        except:
            logger.exception("Exception when dumping data to file")
        finally:
            self._lock.release()

    def restore(self):
        """Restore data from disk using pickle
        """
        self._lock.acquire()
        logger.debug("Restore cache from disk")
        try:
            filename = self.get_pickle_filename()
            self._cache = pickle.load( open( filename, "rb" ) )
        except:
            self._cache = {}
            logger.exception("Exception when restoring data from dump")
        finally:
            self._lock.release()

    def start_timer_dead(self):
        """
        """
        if self._cache_dead_timer is None:
            self._cache_dead_timer = threading.Timer(self._cache_dead_ttl / 3, self.timer_dead)
            self._cache_dead_timer.start()

    def timer_dead(self):
        """Remove dead entries from cache
        """
        self.stop_timer_dead()
        logger.debug("Remove dead entries in cache")
        try:
            now = datetime.datetime.now()
            dead_time = now - datetime.timedelta(seconds=self._cache_dead_ttl)
            for key in self._cache.keys():
                self._lock.acquire()
                if 'last_update' not in self._cache[key]:
                    self._cache[key]['last_update'] = now
                try:
                    if key in self._cache and self._cache[key]['last_update']  < dead_time:
                        logger.debug("Remove dead entries in cache : %s", key)
                        self.remove_rrd_from_list(key)
                        del self._cache[key]
                except:
                    logger.exception("[%s] - Exception when removing dead entry %s in cache", self.__class__.__name__, key)
                finally:
                    self._lock.release()
        except:
            logger.exception("Exception when removing dead entries")
        self.start_timer_dead()

    def stop_timer_dead(self):
        """
        """
        if self._cache_dead_timer is not None:
            self._cache_dead_timer.cancel()
            self._cache_dead_timer = None

    def start_timer_pickle(self):
        """
        """
        if self._cache_pickle_timer is None:
            self._cache_pickle_timer = threading.Timer(self._cache_pickle_ttl, self.timer_pickle)
            self._cache_pickle_timer.start()

    def timer_pickle(self):
        """Dump cache to file using pickle
        """
        self.stop_timer_pickle()
        self.dump()
        self.start_timer_pickle()

    def stop_timer_pickle(self):
        """
        """
        if self._cache_pickle_timer is not None:
            self._cache_pickle_timer.cancel()
            self._cache_pickle_timer = None

    def timer_flush_all(self):
        """Flush all data via a separate thread in a timer
        """
        if hadd is None or value_uuid is None or value_index is None:
            return False
        th = threading.Timer(self._thread_delay, self.flush_all, args=(hadd, value_uuid, value_index))
        th.start()

    def flush_all(self):
        """Flush all data to rrd files and remove them from cache
        """
        rrds = self._cache.keys()
        for rrd in rrds:
            try:
                self.flush(rrd)
            except:
                logger.exception("Exception in flush_all : rrd = %s", rrd)

    def timer_flush(self, rrd_file):
        """Flush data from in cache from a value via a separate thread in a timer
        """
        if hadd is None or value_uuid is None or value_index is None:
            return False
        th = threading.Timer(self._thread_delay, self.flush, args=(rrd_file))
        th.start()

    def flush(self, rrd_file):
        """Flush data from a value to rrd file and remove them from cache
        """
        if rrd_file is None or rrd_file not in self._cache:
            return False
        self._lock.acquire()
        logger.info("Flush rrd_file %s", rrd_file)
        try:
            rrd_dict = self._cache[rrd_file]
            epochs = sorted(rrd_dict['values'].keys())
            rrd_data = [self.get_rrd_filename(rrd_file)]
            last_epoch = epochs[-1]
            for epoch in epochs:
                try:
                    rrd_line = ""
                    if epoch != last_epoch:
                        #We must let the last serie in cache
                        #Otherwise we could raise :
                        # error: /tmp/janitoo/home/public/datarrd_store/rrd/open_files.rrd: illegal attempt to update using time 1443837167 when last
                        # update time is 1443837240 (minimum one second step)
                        rrd_line = '%s' %(epoch)
                        for key_idx in rrd_dict['values'][epoch]:
                            try:
                                val = 'U'
                                if rrd_dict['values'][epoch][key_idx] is not None:
                                    val = rrd_dict['values'][epoch][key_idx]
                                rrd_line = '%s:%s' %(rrd_line, val)
                            except:
                                rrd_line = '%s:%s' %(rrd_line, 'U')
                                logger.exception("[%s] - Exception when flushing cache for %s epoch %s:%s", self.__class__.__name__, rrd_file, epoch, key_idx)
                        del self._cache[rrd_file]['values'][epoch]
                    if rrd_line != "":
                        rrd_data.append(rrd_line)
                except:
                    logger.exception("[%s] - Exception when flushing cache for %s epoch %s", self.__class__.__name__, rrd_file, epoch)
            if len (rrd_data) > 1:
                rrdtool.update(rrd_data)
        except:
            logger.exception("[%s] - Exception when flushing cache for %s", self.__class__.__name__, rrd_file)
        finally:
            self._lock.release()

    def get_count_values(self):
        """Retrieve the number of values cached
        """
        return len(self._cache)

    def get_count_series(self):
        """Retrieve the number of series of values cached
        """
        numb=0
        for rrd_file in self._cache.keys():
            numb += len(self._cache[rrd_file]['values'])
        return numb

    def get_values_to_dump(self):
        """Return a list of tuples (hadd, value_uuid, value_index) of values in timeout. They must be flush to disk
        """
        return 0

    def remove_config(self, rrd_file):
        """Remove an entry in cache and its rrd file
        """
        if rrd_file not in self._cache:
            logger.warning("[%s] - Remove a non existent entry [%s] from cache ", self.__class__.__name__, rrd_file)
        if len(self._cache[rrd_file]['values']) > 0:
            logger.warning("[%s] - Remove a non empty entry [%s] from cache : %s ", self.__class__.__name__, rrd_file, self._cache[rrd_file])
        self._lock.acquire()
        try:
            filename = self.get_rrd_filename(rrd_file)
            if os.path.exists(filename) == True:
                os.remove(filename)
            if rrd_file is not None and rrd_file in self._cache:
                del self._cache[rrd_file]
        except:
            logger.exception("Exception when removing config")
        finally:
            self._lock.release()

    def timer_add_config(self, rrd_file, step, config):
        """Add a config via a separate thread in a timer
        """
        if rrd_file is None or step is None or config is None:
            return False
        th = threading.Timer(self._thread_delay*5, self.add_config, args=(rrd_file, step, config))
        th.start()

    def add_config(self, rrd_file, step, config):
        """
        ret = rrdtool.create("example.rrd", "--step", "1800", "--start", '0',
                                 "DS:metric1:GAUGE:2000:U:U",
                                 "DS:metric2:GAUGE:2000:U:U",
                                 "RRA:AVERAGE:0.5:1:600",
                                 "RRA:AVERAGE:0.5:6:700",
                                 "RRA:AVERAGE:0.5:24:775",
                                 "RRA:AVERAGE:0.5:288:797",
                                 "RRA:MAX:0.5:1:600",
                                 "RRA:MAX:0.5:6:700",
                                 "RRA:MAX:0.5:24:775",
                                 "RRA:MAX:0.5:444:797")

        Let’s consider all lines in details. First line include name of RRD database (“example.rrd”) and you can use here any path you want,
        step of parameters checking (30 minutes in our case), and the start point (0 or N means ‘now’).
        ‘DS’ in line 4-5 means Data Source, these lines include two our metrics.
        ‘2000’ means that RRD can wait for 2000 seconds to get new values until it considers them as unknown
        (that’s is why we use 2000, which 200 seconds more of our 30 minutes interval).
        Last two parameters – ‘U:U’ – stand for min and max values of each metric (‘unknown’ in our case).
        Lines 6-13 describe what types of gained values RRD should store in its database.
        It’s pretty self-describing (average and max values).  Mentioned values describe how many parameters RRD should keep.
        Considering it can be confusing I will omit explanation but note that these values were choosen  to be compatible with MRTG (actually, it’s not quite true
        since we use 1800 seconds periods and not 5 minutes, so you might need to modify it (if you also don’t use 5 minutes period) or keep like I did).

        GAUGE, COUNTER, DERIVE or ABSOLUTE
        """
        #print "add_config", rrd_file, config
        self._lock.acquire()
        rrd_sources = []
        try:
            if rrd_file is None:
                logger.warning("Can't add %s in cache", rrd_file)
                return False
            if rrd_file not in self._cache:
                self._cache[rrd_file] = {'step':step, 'last_update':datetime.datetime.now(), 'labels' : {}, 'types':{}, 'hadds':{}, 'uuids':{}, 'indexes':{}, 'values':{}}
            for key in sorted(config.keys()):
                hadd, value_uuid, value_index, rrd_type, rrd_label = config[key].split('|')
                self._cache[rrd_file]["labels"][key] = rrd_label
                self._cache[rrd_file]["types"][key] = rrd_type
                self._cache[rrd_file]["hadds"][key] = hadd
                self._cache[rrd_file]["uuids"][key] = value_uuid
                self._cache[rrd_file]["indexes"][key] = value_index
                rrd_sources.append("DS:%s:%s:%s:U:U" %(rrd_label, rrd_type, step*2))
        except:
            logger.exception("Exception when adding config in cache")
        finally:
            self._lock.release()
        #print "rrd_sources :", rrd_sources
        try:
            filename = self.get_rrd_filename(rrd_file)
            if os.path.exists(filename) == False:
                rrdtool.create(filename, "--step", str(step), "--start", '0',
                                     rrd_sources,
                                     "RRA:AVERAGE:0.5:1:1440",
                                     "RRA:AVERAGE:0.5:12:1440",
                                     "RRA:AVERAGE:0.5:144:1440",
                                     "RRA:AVERAGE:0.5:288:1440",
                                     "RRA:MAX:0.5:1:1440",
                                     "RRA:MAX:0.5:12:1440",
                                     "RRA:MAX:0.5:144:1440",
                                     "RRA:MAX:0.5:288:1440",
                                     "RRA:MIN:0.5:1:1440",
                                     "RRA:MIN:0.5:12:1440",
                                     "RRA:MIN:0.5:144:1440",
                                     "RRA:MIN:0.5:288:1440")
            self.add_rrd_to_list(rrd_file)
        except:
            logger.exception("Exception when creating rrd file %s", rrd_file)

    def add_rrd_to_list(self, rrd_file):
        """Add the rrd_file to index.txt
        """
        filename = self.get_list_filename()
        rrd_list = []
        if os.path.exists(filename) == True:
            with open(filename) as file:    # Use file to refer to the file object
                data = file.read()
                rrd_list = data.split("|")
        if rrd_file in rrd_list:
            return
        rrd_list.append(rrd_file)
        line = '|'.join(rrd_list)
        with open(filename, "w") as file:
            file.write(line)

    def remove_rrd_from_list(self, rrd_file):
        """Remove the rrd from index.txt
        """
        filename = self.get_list_filename()
        rrd_list = []
        if os.path.exists(filename) == True:
            with open(filename) as file:    # Use file to refer to the file object
                data = file.read()
                rrd_list = data.split("|")
        if rrd_file not in rrd_list:
            return
        rrd_list.remove(rrd_file)
        line = '|'.join(rrd_list)
        with open(filename, "w") as file:
            file.write(line)

class RrdBus(JNTBus):
    """A pseudo-bus to manage RRDTools
    """
    def __init__(self, **kwargs):
        """
        :param int bus_id: the SMBus id (see Raspberry Pi documentation)
        :param kwargs: parameters transmitted to :py:class:`smbus.SMBus` initializer
        """
        JNTBus.__init__(self, **kwargs)
        self.store = None
        self.store_last = False

        uuid="count_values"
        self.values[uuid] = self.value_factory['sensor_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The number of values in the store',
            label='#Values',
            get_data_cb=self.get_count_values,
            genre=0x01,
        )
        poll_value = self.values[uuid].create_poll_value(default=300)
        self.values[poll_value.uuid] = poll_value

        uuid="count_series"
        self.values[uuid] = self.value_factory['sensor_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The number of series of values in the store',
            label='#Series',
            get_data_cb=self.get_count_series,
            genre=0x01,
        )
        poll_value = self.values[uuid].create_poll_value(default=300)
        self.values[poll_value.uuid] = poll_value

        uuid="cache_rrd_ttl"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The cache_rrd_ttl',
            label='Rrd ttl',
            default=60*60,
        )

        uuid="cache_pickle_ttl"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The cache_pickle_ttl',
            label='Pickle ttl',
            default=60,
        )

        uuid="cache_dead_ttl"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The cache_dead_ttl',
            label='Cache dead ttl',
            default=60*60*24,
        )

        uuid="actions"
        self.values[uuid] = self.value_factory['action_list'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The action on the store',
            label='Actions',
            list_items=['flush'],
            set_data_cb=self.set_action,
            is_writeonly = True,
            cmd_class = COMMAND_CONTROLLER,
            genre=0x01,
        )

    def check_heartbeat(self):
        """Check that the component is 'available'

        """
        #~ print "it's me %s : %s" % (self.values['upsname'].data, self._ups_stats_last)
        if self.store is not None:
            return self.store.is_alive()
        return False

    def get_count_values(self, node_uuid, index):
        """
        """
        if self.store is not None:
            return self.store.get_count_values()
        return 0

    def get_count_series(self, node_uuid, index):
        """
        """
        if self.store is not None:
            return self.store.get_count_series()
        return 0

    def set_action(self, node_uuid, index, data):
        """Act on the server
        """
        params = {}
        if data == "flush":
            if self.store is not None:
                self.store.flush()

    def start(self, mqttc, trigger_thread_reload_cb=None):
        JNTBus.start(self, mqttc, trigger_thread_reload_cb)
        self.store = RrdStoreThread("datarrd_store", self.options.data)
        self.store.config_thread(cache_rrd_ttl=self.values["cache_rrd_ttl"].data,
                cache_pickle_ttl=self.values["cache_pickle_ttl"].data,
                cache_dead_ttl=self.values["cache_dead_ttl"].data)
        self.store.start()

    def stop(self):
        JNTBus.stop(self)
        if self.store is not None:
            self.store.stop()
            self.store = None

    def get_package_name(self):
        """Return the name of the package. Needed to publish static files

        **MUST** be copy paste in every extension that publish statics files
        """
        return __package__
