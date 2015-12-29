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
__copyright__ = "Copyright © 2013-2014-2015 Sébastien GALLET aka bibi21000"

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
data_files_config(data_files, 'templates','src/janitoo_manager_proxy/templates/','*')
data_files_config(data_files, 'themes','src/janitoo_manager_proxy/themes/','*')
data_files_config(data_files, 'static','src/janitoo_manager_proxy/static/','*')
data_files_config(data_files, 'docs','src/docs/','*')
data_files_config(data_files, 'publlic','src/public/','*')

    #~ package_data={
    #~ '': ['docs/*', 'docs/images/*'],
    #~ 'janitoo_datalog_rrd': ['public/css/*', 'public/js/*', 'public/images/*', 'public/templates/*', 'public/html/*'],
    #~ },

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
    packages = find_packages('src', exclude=["scripts", "docs", "config"]),
    package_dir = { '': 'src' },
    include_package_data=True,
    data_files = data_files,
    install_requires=[
                     'janitoo >= %s'%'0.0.6',
                     'python-rrdtool >= 1.4.7',
                    ],
    dependency_links = [
      'https://github.com/bibi21000/janitoo/archive/master.zip#egg=janitoo-%s'%"0.0.7",
    ],
    entry_points = janitoo_entry_points,
)
