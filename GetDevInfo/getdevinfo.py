#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# Device Information Obtainer for Wine Autostart Version 2.0.2
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

#Begin Main Class.
class Main():
    def FoundExactMatch(self, Item, Text, Log=True):
        """Check if an exact match of "Item" (arg) can be found in "Text" (arg), seperated by commas or spaces."""
        if Log == True:
            logger.debug("GetDevInfo: Main().FoundExactMatch(): Looking for: "+Item+" in: "+Text+"...")

        Result = re.findall('\\'+Item+'\\b', Text)

        if len(Result) > 0:
            Result =  True
        else:
            Result =  False

        if Log == True:
            logger.info("GetDevInfo: Main().FoundExactMatch(): Result: "+str(Result)+"...")

        return Result

    def IsPartition(self, Device, DeviceList=None):
        """Check if the given device is a partition, and if the host device of that partition is in the given list"""
        logger.debug("GetDevInfo: Main().IsPartition(): Checking if device: "+Device+" is a partition...")

        if Device[0:7] not in ["/dev/sr", "/dev/fd"] and Device[-1].isdigit() and Device[0:8] in DeviceList:
            Result =  True
        else:
            Result = False

        logger.info("GetDevInfo: Main().IsPartition(): Result: "+str(Result)+"...")
        return Result

    def DeduplicateList(self, ListToDeduplicate):
        """Deduplicate the given list."""
        logger.debug("GetDevInfo: Main().DeduplicateList(): Deduplicating list: "+str(ListToDeduplicate)+"...")
        ResultsList = []

        for Element in ListToDeduplicate:
            if Element not in ResultsList:
                ResultsList.append(Element)

        #Return the results.
        logger.info("GetDevInfo: Main().DeduplicateList(): Results: "+str(ResultsList)+"...")
        return ResultsList

    def GetVendor(self, Device, DeviceLineNumber=None):
        """Find vendor information for the given device."""
        logger.info("GetDevInfo: Main().GetVendor(): Getting vendor info for device: "+Device+"...")

        #Look for the information using the device's line number.
        for Number in self.VendorLinesList:
            #Ignore the line number if it is before the device name...
            if Number < DeviceLineNumber:
                if self.VendorLinesList[-1] != Number:
                    continue
                else:
                    #...unless it is the last line.
                    VendorLineNumber = Number
            else:
                #The first time this is run, we know the last line number was the right one!
                #Now we just have to grab that line, and format it.
                VendorLineNumber = self.VendorLinesList[self.VendorLinesList.index(Number)-1]

            #Return the Vendor info. Use the found line if it is less than ten lines apart from the Device line. Otherwise it's probably bogus.
            if DeviceLineNumber - VendorLineNumber < 10:
                Vendor = ' '.join(self.Output[VendorLineNumber].split()[1:])
                logger.info("GetDevInfo: Main().GetVendor(): Found vendor info: "+Vendor)
                return Vendor
            else:
                logger.warning("GetDevInfo: Main().GetVendor(): Found probable wrong vendor: "+' '.join(self.Output[VendorLineNumber].split()[1:])+". Ignoring it and returning 'Unknown'...")
                return "Unknown"

    def GetProduct(self, Device, DeviceIsPartition, DeviceLineNumber=None, DeviceLinesList=None, ProductInfoList=None):
        """Find product information for the given device."""
        logger.info("GetDevInfo: Main().GetProduct(): Getting product info for device: "+Device+"...")

        #Check if the device is actually a partition.
        if DeviceIsPartition:
            #Temporarily reset DeviceLineNumber to the partition's host DeviceLineNumber, so we can grab product info, and keep the old DeviceLineNumber.
            logger.debug("GetDevInfo: Main().GetProduct(): Using product info from host device, because this is a partition...")
            OldDeviceLineNumber = DeviceLineNumber

            #Find the line number that the host device is on.
            for Number in DeviceLinesList:
                if self.FoundExactMatch(Device[0:8], self.Output[Number]):
                    DeviceLineNumber = Number
                    break

        #Look for the information using the device's line number.
        for Number in self.ProductLinesList:
            if Number < DeviceLineNumber:
                #Ignore the line number if it is before the device name...
                if self.ProductLinesList[-1] != Number:
                    continue
                else:
                    #...unless it is the last line.
                    ProductLineNumber = Number
            else:
                #The first time this is run, we know the last line num was the right one!
                #Now we just have to grab that line, and format it.
                ProductLineNumber = self.ProductLinesList[self.ProductLinesList.index(Number)-1]

            #Save the Vendor info. Use the found line if it is less than ten lines apart from the Device line. Otherwise it's probably bogus.
            if DeviceLineNumber - ProductLineNumber < 10:
                Product = ' '.join(self.Output[ProductLineNumber].split()[1:])
                logger.info("GetDevInfo: Main().GetProduct(): Found product info: "+Product+"...")
            else:
                Product = "Unknown"
                logger.warning("GetDevInfo: Main().GetProduct(): Found probable wrong product: "+' '.join(self.Output[ProductLineNumber].split()[1:])+". Ignoring it and returning 'Unknown'...")

            #Break out of the loop to save time.
            break

        if DeviceIsPartition:
            #Reset the device line number to the original value so the rest of the code works properly, and return the value.
            DeviceLineNumber = OldDeviceLineNumber
            return "Host Device: "+Product
        else:
            #Return the value.
            return Product

    def GetSize(self, Device, DeviceLineNumber=None):
        """Find size information for the given device."""
        logger.info("GetDevInfo: Main().GetSize(): Getting size info for device: "+Device+"...")

        #Look for the information using the device's line number.
        for Number in self.SizeLinesList:
            if Number < DeviceLineNumber:
                #Ignore the line number if it is before the device name...
                if self.SizeLinesList[-1] != Number:
                    continue
                else:
                    #...unless it is the last line. Keep going rather than reiterating the loop.
                    pass
            else:
                #The first time this is run, we know this line num is the right one!
                #Now we just have to grab this line, check it is within 10 lines, and format it. Keep going and don't use SizeLineNumber, becuase we don't need it.
                pass

             #Return the Size info. Use the found line if it is less than ten lines apart from the Device line. Otherwise it's probably bogus.
            if Number - DeviceLineNumber < 10:
                Size = ' '.join(self.Output[Number].split()[1:])
                logger.info("GetDevInfo: Main().GetSize(): Found size info: "+Size+"...")
                return Size
            else:
                if Device[0:7] == "/dev/sr":
                    #Report size information in a more friendly way for optical drives.
                    logger.info("GetDevInfo: Main().GetSize(): Device is an optical drive, and getting size info isn't supported for optical drives. Returning 'N/A'...")
                    return "N/A"
                else:
                    logger.warning("GetDevInfo: Main().GetSize(): Found probable wrong size: "+' '.join(self.Output[Number].split()[1:])+". Ignoring it and returning 'Unknown'...")
                    return "Unknown"

    def GetDescription(self, Device, DeviceLineNumber=None, DeviceList=None, VendorInfoList=None, ProductInfoList=None):
        """Find description information for the given device."""
        logger.info("GetDevInfo: Main().GetDescription(): Getting description info for device: "+Device+"...")

        #Look for the information using the device's line number.
        for Number in self.DescriptionLinesList:
            if Number < DeviceLineNumber:
                #Ignore the line number if it is before the device name...
                if self.DescriptionLinesList[-1] != Number:
                    continue
                else:
                    #...unless it is the last line.
                    DescriptionLineNumber = Number
            else:
                #The first time this is run, we know the last line num is the right one!
                #Now we just have to grab this line, check it is within 10 lines, and format it.
                DescriptionLineNumber = self.DescriptionLinesList[self.DescriptionLinesList.index(Number)-1]

            #Return the Description info. Use the found line if it is less than ten lines apart from the Device line. Otherwise it's probably bogus.
            if DeviceLineNumber - DescriptionLineNumber < 10:
                Description = ' '.join(self.Output[DescriptionLineNumber].split()[1:])
                logger.info("GetDevInfo: Main().GetDescription(): Found description info: "+Description+"...")
                return Description
            else:
                logger.warning("GetDevInfo: Main().GetDescription(): Found probable wrong description: "+' '.join(self.Output[DescriptionLineNumber].split()[1:])+". Ignoring it and returning 'Unknown'...")
                return "Unknown"

    def GetInfo(self):
    	"""Get device information."""
        logger.info("GetDevInfo: Main().GetInfo(): Preparing to get device info...")

 	    #Run lshw to try and get disk information.
        logger.debug("GetDevInfo: Main().GetInfo(): Running 'lshw -sanitize'...")
        runcmd = subprocess.Popen("LC_ALL=C pkexec lshw -sanitize", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

        #Get the output.
        stdout, stderr = runcmd.communicate()
        self.Output = stdout.split("\n")
        logger.debug("GetDevInfo: Main().GetInfo(): Done.")

        #Now we should be able to grab the names of all devices, and detailed info on each device we find.
        #Use rather a lot of lists to keep track of the line numbers of each Device, Vendor, Product, Size, Description, and Capability line.
        #I'm using my own counter here to make sure I get the right line number, not the first line with similar contents.
        DeviceList = []
        DeviceLinesList = []
        self.VendorLinesList = []
        self.ProductLinesList = []
        self.SizeLinesList = []
        self.DescriptionLinesList = []
        TempLineCount = -1

        for Line in self.Output:
            TempLineCount += 1

            #Try to grab info.
            if "logical name:" in Line:
                try:
                    Device = Line.split()[2]
                    DeviceLinesList.append(TempLineCount)
                except IndexError as e:
                    continue

                #See if it's a device that's in our categories, and add it to the list if it is.
                if '/dev/sr' in Device:
                    DeviceList.append(Device)

            elif "vendor:" in Line:
                self.VendorLinesList.append(TempLineCount)
            elif "product:" in Line:
                self.ProductLinesList.append(TempLineCount)
            elif "size:" in Line or "capacity:" in Line:
                self.SizeLinesList.append(TempLineCount)
            elif "description:" in Line:
                self.DescriptionLinesList.append(TempLineCount)

        #Deduplicate them.
        DeviceList = self.DeduplicateList(DeviceList)

        #Use a final set of lists to store the info, making it easier to input into a multi-column wx.ListCtrl as used in the new device information dialogs.
        VendorInfoList = []
        DeviceTypeInfoList = []
        ProductInfoList = []
        SizeInfoList = []
        DescriptionInfoList = []

        logger.info("GetDevInfo: Main().GetInfo(): Getting device info...")

        for Device in DeviceList:
            #Get the Vendor, Product, Size and Description for each drive.
            #First find the line number where the device is. Don't log the output here, because it will waste lots of time and fill the log file with junk.
            logger.debug("GetDevInfo: Main().GetInfo(): Finding device line number (number of line where device name is)...")
            for Line in self.Output:
                if self.FoundExactMatch(Item=Device, Text=Line, Log=False):
                    DeviceLineNumber = self.Output.index(Line)
                    break

            #Check if the device is a partition.
            DeviceIsPartition = self.IsPartition(Device, DeviceList)
            if DeviceIsPartition:
                DeviceTypeInfoList.append("Partition")
            else:
                DeviceTypeInfoList.append("Device")

            #Get all other information, making sure it remains stable even if we found no info at all.
            #Vendor.
            if len(self.VendorLinesList) > 0:
                Vendor = self.GetVendor(Device, DeviceLineNumber)
            else:
                Vendor = "Unknown"

            if Vendor != None:
                VendorInfoList.append(Vendor)
            else:
                VendorInfoList.append("Unknown")

            #Product.
            if len(self.ProductLinesList) > 0:
                Product = self.GetProduct(Device, DeviceIsPartition, DeviceLineNumber, DeviceLinesList)
            else:
                Product = "Unknown"

            if Product != None:
                ProductInfoList.append(Product)
            else:
                ProductInfoList.append("Unknown")

            #Size.
            if len(self.SizeLinesList) > 0:
                Size = self.GetSize(Device, DeviceLineNumber)
            else:
                Size = "Unknown"

            if Size != None:
                SizeInfoList.append(Size)
            else:
                SizeInfoList.append("Unknown")

            #Description.
            if len(self.DescriptionLinesList) > 0:
                Description = self.GetDescription(Device, DeviceLineNumber=DeviceLineNumber)
            else:
                Description = "Unknown"

            if Description != None:
                DescriptionInfoList.append(Description)
            else:
                DescriptionInfoList.append("Unknown")

        #Return the info.
        logger.info("GetDevInfo: Main().GetInfo(): Finished!")
        return [DeviceList, DeviceTypeInfoList, VendorInfoList, ProductInfoList, SizeInfoList, DescriptionInfoList]

    def GetBlockSize(self, Device):
        """Find the given device's blocksize, and return it"""
        logger.debug("GetDevInfo: Main().GetBlockSize(): Finding blocksize for device: "+Device+"...")

  	    #Run /sbin/blockdev to try and get blocksize information.
        logger.debug("GetDevInfo: Main().GetBlockSize(): Running 'blockdev --getbsz "+Device+"'...")
        runcmd = subprocess.Popen("pkexec blockdev --getbsz "+Device, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

        #Get the output.
        stdout, stderr = runcmd.communicate()

        Result = stdout.replace('\n', '')

        #Check it worked (it should be convertable to an integer if it did).
        try:
            tmp = int(Result)
        except ValueError:
            #It didn't, this is probably a file, not a device.
            logger.warning("GetDevInfo: Main().GetBlockSize(): Couldn't get blocksize for device: "+Device+"! Returning None...")
            return None
        else:
            #It did.
            logger.info("GetDevInfo: Main().GetBlockSize(): Blocksize for device: "+Device+": "+Result+". Returning it...")
            return Result

#End Main Class.

if __name__ == "__main__":
    #Import modules.
    import subprocess
    import re
    import logging

    #Set up basic logging to stdout.
    logger = logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p', level=logging.DEBUG)

    Info = Main().GetInfo()

    #Get blocksizes.
    BlockSizeList = []
    for Device in Info[0]:
        BlockSizeList.append(Main().GetBlockSize(Device))

    #Print the info in a readable way.
    print("\nDevice: "+str(Info[0])+"\n")
    print("\nBlocksize: "+str(BlockSizeList)+"\n")
    print("\nType: "+str(Info[1])+"\n")
    print("\nVendor: "+str(Info[2])+"\n")
    print("\nProduct: "+str(Info[3])+"\n")
    print("\nSize: "+str(Info[4])+"\n")
    print("\nDescription: "+str(Info[5])+"\n")
