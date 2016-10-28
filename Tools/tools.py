#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# Tools Package for Wine Autostart Version 2.0.2
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

class Main():
    def GetDiskMountPoint(self, Device):
        """Find if the given device is mounted or not, and return the mount point, or None if it isn't mounted"""

        #Run a command to get filesystem info.
        Output = subprocess.check_output(["lsblk", "-r"]).split("\n")

        #Read the output and find the info. ('None' will be returned automatically if we don't return anything, for example if the device isn't found in Output)
        for Line in Output:

            try:
                Dev = "/dev/"+Line.split()[0]
                MountPoint = ' '.join(Line.split()[6:]).replace(' ', '\\ ').replace("x20", " ")

            except IndexError:
                continue

            else:
                try:
                    if Dev == Device and MountPoint[0] == "/":
                        return MountPoint
                except: continue

    def FindAutorunFile(self, MountPoint): #*** test ***
        """Use the find command to look for autorun files, and return the result."""
        logger.debug("Tools: Main().FindAutorunFile(): Finding and returning any autorun file found in "+MountPoint+"...")

        #Just in case there's more than one autorun file (incredibly unlikely), return the first if there is one.
        FilesGenerator = os.walk(MountPoint.replace("\\", ""))

        AutorunFile = None

        for BaseDir, SubDir, Files in FilesGenerator:
            for File in Files:
                if File.upper() == "AUTORUN.INF":
                    AutorunFile = os.path.join(BaseDir, File)
                    logger.info("Tools: Main().FindAutorunFile(): Found autorun file at: "+AutorunFile+"...")
                    break

        #Return the file or None if not found.
        return AutorunFile

    def ParseAutorunFile(self, AutorunFile):
        """Read the autorun file, and return the path to an exe file listed inside, if there is one"""
        logger.debug("Tools: Main().ParseAutorunFile(): Finding and returning exe file info found in "+AutorunFile+" (if any)...")
        ExeFile = None

        #Open the file.
        File = open(AutorunFile, "r")

        #Read each line, looking for '.exe' and one (or both) of 'open=' and 'shellexecute='.
        for Line in File.readlines():
            if "open=" in Line or "shellexecute=" in Line:
                if ".exe" in Line:
                    #Save the formatted info in a temporary variable, and break out of the loop.
                    #First, just get whatever comes after '=' on this line.
                    Temp = Line.split("=")[-1]

                    #Next remove any spaces that appear after the end of the filename, which mess things up.
                    Temp = Temp.split(".exe")[0]+".exe"

                    #Finally, swap '\' for '/', escape whitespace with '\', and remove the '\n' from the end of the line.
                    ExeFile = Temp.replace('\\', '/').replace("\\", "").replace('\n', '')
                    break

                elif ".EXE" in Line: #*** Test this ***
                    #Save the formatted info in a temporary variable, and break out of the loop.
                    #First, just get whatever comes after '=' on this line.
                    Temp = Line.split("=")[-1]

                    #Next remove any spaces that appear after the end of the filename, which mess things up.
                    Temp = Temp.split(".EXE")[0]+".EXE"

                    #Finally, swap '\' for '/', escape whitespace with '\', and remove the '\n' from the end of the line.
                    ExeFile = Temp.replace('\\', '/').replace("\\", "").replace('\n', '')
                    break

        #Close the file.
        File.close()

        #Return the info.
        logger.debug("Tools: Main().ParseAutorunFile(): Done!")
        return ExeFile

    def ScanForExeFiles(self, MountPoint): #*** Test ***
        """Use 'find' to look for exe files in the given mountpoint"""
        logger.debug("Tools: Main().ScanForExeFiles(): Finding and returning and exe files found in "+MountPoint+"...")

        #Get a list of files.
        ExeFilesGenerator = os.walk(MountPoint.replace("\\", ""))
        ExeFiles = []

        for BaseDir, SubDir, Files in ExeFilesGenerator:
            for File in Files:
                if ".EXE" in File.upper():
                    ExeFiles.append(os.path.join(BaseDir, File))

        #Return the list.
        logger.debug("Tools: Main().ScanForExeFiles(): Done!")
        return ExeFiles
