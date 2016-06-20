#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# Config File Saver for Wine Autostart Version 2.0.1
# This file is part of Wine Autostart.
# Copyright (C) 2013-2015 Hamish McIntyre-Bhatty
# Wine Autostart is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 or,
# at your option, any later version.
#
# Wine Autostart is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Wine Autostart.  If not, see <http://www.gnu.org/licenses/>.

#Do future imports to prepare to support python 3. Use unicode strings rather than ASCII strings, as they fix potential problems.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

#Import modules
import sys
import subprocess

#Only write the configuration if it is valid.
if "#Configuration for Wine Autostart" in sys.argv[1]:
    ConfigFile = open("/usr/share/wineautostart/wineautostart.cfg", 'w')
    ConfigFile.write(sys.argv[1])
    ConfigFile.close()

else:
    sys.exit("Invalid Input! Exiting...")
