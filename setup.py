#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup file of Janitoo
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

from os import name as os_name
from setuptools import setup, find_packages
from platform import system as platform_system
import glob
import os
import sys
from _version import janitoo_version

DEBIAN_PACKAGE = False
filtered_args = []

for arg in sys.argv:
    if arg == "--debian-package":
        DEBIAN_PACKAGE = True
    else:
        filtered_args.append(arg)
sys.argv = filtered_args

def data_files_config(res, rsrc, src, pattern):
    for root, dirs, fils in os.walk(src):
        if src == root:
            sub = []
            for fil in fils:
                sub.append(os.path.join(root,fil))
            res.append((rsrc, sub))
            for dire in dirs:
                    data_files_config(res, os.path.join(rsrc, dire), os.path.join(root, dire), pattern)

data_files = []
data_files_config(data_files, 'docs','src/docs/','*')
data_files_config(data_files, 'public','src/public/','*')

#~ def get_package_data(res, pkgdir, src, pattern):
    #~ for root, dirs, fils in os.walk(os.path.join(pkgdir, src)):
        #~ print os.path.join(pkgdir, src), root, dirs, fils
        #~ if os.path.join(pkgdir, src) == root:
            #~ sub = []
            #~ for fil in fils:
                #~ sub.append(os.path.join(src,fil))
            #~ res.extend(sub)
            #~ for dire in dirs:
                #~ get_package_data(res, pkgdir, os.path.join(src, dire), pattern)
    #~ return res

#~ package_data = []
#~ get_package_data(package_data, 'src', 'public','*')
#~ get_package_data(package_data, 'src/janitoo_manager', 'themes','*')
#~ get_package_data(package_data, 'src/janitoo_manager', 'static','*')
#~ get_package_data(package_data, 'src/janitoo_manager', 'bower_components','*')

#You must define a variable like the one below.
#It will be used to collect entries without installing the package
janitoo_entry_points = {
    "janitoo.components": [
        "datarrd.datasource = janitoo_datalog_rrd.components:make_datasource",
        "http.rrd = janitoo_datalog_rrd.components:make_http_resource",
    ],
    "janitoo.threads": [
        "datarrd = janitoo_datalog_rrd.thread:make_thread",
    ],
}

setup(
    name = 'janitoo_datalog_rrd',
    description = "A Data logger using rrd for janitoo",
    long_description = "A Data logger using rrd for janitoo",
    author='Sébastien GALLET aka bibi2100 <bibi21000@gmail.com>',
    author_email='bibi21000@gmail.com',
    license = """
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
    """,
    url='http://bibi21000.gallet.info/',
    version = janitoo_version,
    zip_safe = False,
    keywords = "rrd,graph",
    scripts=['src/scripts/jnt_datalog_rrd'],
    packages = find_packages('src', exclude=["scripts", "docs", "public", "config"]),
    package_dir = { '': 'src' },
    #~ include_package_data=True,
    #~ package_data={
            #~ 'janitoo_datalog_rrd': package_data,
        #~ },
    data_files = data_files,
    install_requires=[
                     'janitoo',
                     'janitoo_factory',
                     'python-rrdtool',
                    ],
    dependency_links = [
      'https://github.com/bibi21000/janitoo/archive/master.zip#egg=janitoo-%s',
      'https://github.com/bibi21000/janitoo_factory/archive/master.zip#egg=janitoo_factory',
      'https://github.com/kyokenn/python-rrdtool/archive/master.zip#egg=python-rrdtool',
    ],
    entry_points = janitoo_entry_points,
)
