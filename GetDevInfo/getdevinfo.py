#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# Device Information Obtainer for Wine Autostart Version 2.0.2
# This file is part of Wine Autostart.
# Copyright (C) 2013-2016 Hamish McIntyre-Bhatty
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

#Begin Main Class.
class Main():
    def GetVendor(self, Node):
        """Get the vendor"""
        try:
            return unicode(Node.vendor.string)

        except AttributeError:
            return "Unknown"

    def GetProduct(self, Node):
        """Get the product"""
        try:
            return unicode(Node.product.string)

        except AttributeError:
            return "Unknown"

    def GetDeviceInfo(self, Node):
        """Get Device Information"""
        HostDisk = unicode(Node.logicalname.string)

        #Ignore non-optical devices.
        if "/dev/sr" not in HostDisk and "/dev/cdrom" not in HostDisk and "/dev/dvd" not in HostDisk:
            return HostDisk
 
        DiskInfo[HostDisk] = {}
        DiskInfo[HostDisk]["Name"] = HostDisk
        DiskInfo[HostDisk]["Vendor"] = self.GetVendor(Node)
        DiskInfo[HostDisk]["Product"] = self.GetProduct(Node)
        DiskInfo[HostDisk]["Description"] = unicode(Node.description.string)

        return HostDisk

    def GetInfo(self, Standalone=False):
        """Get Disk Information."""
        logger.info("GetDevInfo: Main().GetInfo(): Preparing to get Disk info...")

        #Run lshw to try and get disk information.
        logger.debug("GetDevInfo: Main().GetInfo(): Running 'LC_ALL=C lshw -sanitize -class disk -class volume -xml'...")
        runcmd = subprocess.Popen("LC_ALL=C pkexec lshw -sanitize -class disk -class volume -xml", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

        #Get the output.
        stdout, stderr = runcmd.communicate()

        if Standalone:
            global DiskInfo
            DiskInfo = {}

        logger.debug("GetDevInfo: Main().GetInfo(): Done.")

        #Parse XML as HTML to support Ubuntu 12.04 LTS. Otherwise output is cut off.
        self.Output = BeautifulSoup(stdout, "html.parser")

        #Support for Ubuntu 12.04 LTS as that lshw outputs XML differently in that release.
        if unicode(type(self.Output.list)) == "<type 'NoneType'>":
            ListOfDevices = self.Output.children

        else:
            ListOfDevices = self.Output.list.children

        #Find the disks.
        for Node in ListOfDevices:
            if unicode(type(Node)) != "<class 'bs4.element.Tag'>":
                continue

            #These are devices.
            self.GetDeviceInfo(Node)

        logger.info("GetDevInfo: Main().GetInfo(): Finished!")
        return DiskInfo

#End Main Class.
if __name__ == "__main__":
    #Import modules.
    import subprocess
    import logging
    from bs4 import BeautifulSoup

    #Set up basic logging to stdout.
    logger = logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p', level=logging.DEBUG)

    DiskInfo = Main().GetInfo(Standalone=True)

    #Print the info in a (semi :D) readable way.
    Keys = DiskInfo.keys()
    Keys.sort()

    for Key in Keys:
        print("\n\n", DiskInfo[Key], "\n\n")
