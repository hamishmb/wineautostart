#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# Wine Autostart Version 2.0.2
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
from distutils.version import LooseVersion

import wx
import wx.animate
import sys
import threading
import time
import os
import shutil
import subprocess
import logging
import getopt
import re

#Import custom-made modules
import GetDevInfo
import Tools

from GetDevInfo.getdevinfo import Main as DevInfoTools
from Tools.tools import Main as BackendTools

#Define the version number, release date, and release type as global variables.
Version = "2.0.2"
ReleaseDate = "18/10/2016"
ReleaseType = "Stable"

def usage():
    print("\nUsage: WineAutostart.py [OPTION]\n")
    print("       -h, --help:                   Show this help message")
    print("       -q, --quiet:                  Show only warning, error and critical error messages in the log file. Very unhelpful for debugging, and not recommended.")
    print("       -v, --verbose:                Enable logging of info messages, as well as warnings, errors and critical errors.")
    print("                                     Not the best for debugging, but acceptable if there is little disk space.")
    print("       -d, --debug:                  Log lots of boring debug messages, as well as information, warnings, errors and critical errors. Usually used for diagnostic purposes.")
    print("                                     The default, as it's very helpful if problems are encountered, and the user needs help\n")
    print("Wine Autostart "+Version+" is released under the GNU GPL Version 3")
    print("Copyright (C) Hamish McIntyre-Bhatty 2013-2015")

#Check cmdline options
try:
    opts, args = getopt.getopt(sys.argv[1:], "hqvd", ["help", "quiet", "verbose", "debug"])
except getopt.GetoptError as err:
    #Invalid option. Show the help message and then exit.
    #Show the error.
    print(unicode(err))
    usage()
    sys.exit(2)

#Make Wine Autostart's temporary directory, clearing it if it is already present.
if os.path.isdir("/tmp/wineautostart"):
    shutil.rmtree("/tmp/wineautostart")

os.mkdir("/tmp/wineautostart")

#Set up logging.
logger = logging.getLogger('Wine Autostart')
logging.basicConfig(filename='/tmp/wineautostart/wineautostart.log', format='%(asctime)s - %(name)s - %(levelname)s: %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')
logger.setLevel(logging.DEBUG)

#Determine the option(s) given, and change the level of logging based on cmdline options.
for o, a in opts:
    if o in ["-q", "--quiet"]:
        print("Setting logging level to warning mode..")
        logger.setLevel(logging.WARNING)
    elif o in ["-v", "--verbose"]:
        print("Setting logging level to verbose mode..")
        logger.setLevel(logging.INFO)
    elif o in ["-d", "--debug"]:
        print("Setting logging level to debug mode..")
        logger.setLevel(logging.DEBUG)
    elif o in ["-h", "--help"]:
        usage()
        sys.exit()
    else:
        assert False, "unhandled option"

#Setup custom-made modules (make global variables accessible inside the packages).
GetDevInfo.getdevinfo.subprocess = subprocess
GetDevInfo.getdevinfo.re = re
GetDevInfo.getdevinfo.logger = logger

Tools.tools.subprocess = subprocess
Tools.tools.logger = logger

#Begin Device Information Handler thread.
class GetDeviceInformation(threading.Thread):
    def __init__(self, ParentWindow):
        """Initialize and start the thread."""
        self.ParentWindow = ParentWindow
        threading.Thread.__init__(self)
        self.start()

    def run(self):
        """Get Device Information and return it as a list with embedded lists"""
        #Use a module I've written to collect data about connected devices, and return it.
        wx.CallAfter(self.ParentWindow.ReceiveDeviceInfo, DevInfoTools().GetInfo())

#End Device Information Handler thread.
#Begin App Indicator IPC Thread.
class AppIndicatorIPCThread(threading.Thread):
    """Thread to receive messages from the App Indicator, so we don't block the GUI thread"""
    def __init__(self, ParentWindow, Indicator):
        """Initialize and start the thread."""
        self.ParentWindow = ParentWindow
        self.Indicator = Indicator
        threading.Thread.__init__(self)
        self.start()

    def run(self):
        """Main body of the thread, started with self.start()"""
        while self.Indicator.poll() is None:
            try:
                Line = self.Indicator.stdout.readline().replace("\n", "")
                wx.CallAfter(self.ParentWindow.ProcessMessage, Line)
            except wx.PyDeadObjectError:
                #MainClass is dead. Break out of the loop and exit the thread.
                break

#End App Indicator IPC Thread.
#Starter class
class WineAutostart(wx.App):
    def OnInit(self):
        MainClass()
        return True

#End Starter class.
#Begin Main class.
class MainClass(wx.Frame):
    def __init__(self):
        """Initialize the hidden frame."""
        wx.Frame.__init__(self, parent=None, style=wx.FRAME_NO_TASKBAR)

        print("Wine Autostart Version "+Version+" Starting...")
        logger.info("WxFixBoot Version "+Version+" Starting...")
        logger.info("Release date: "+ReleaseDate)
        logger.info("Running on wxPython version: "+wx.version()+"...")

        global Exiting
        Exiting = False

        global RunningBackend
        RunningBackend = False

        #Create the taskbar icon.
        logger.info("MainClass().__init__(): Creating Indicator...")
        self.Indicator = subprocess.Popen(['/usr/share/wineautostart/IndicatorWineAutostart.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE) 

        #Create the program's icon.
        global AppIcon
        AppIcon = wx.Icon("/usr/share/wineautostart/images/Logo.png", wx.BITMAP_TYPE_PNG)

        #Read the configuration file.
        logger.info("MainClass().__init__(): Reading configuration...")
        self.ReadConfig()

        #Bind events.
        logger.info("MainClass().__init__(): Binding events...")
        self.BindEvents()

        #Start the IPC thread.
        logger.info("MainClass().__init__(): Starting Indicator Management Thread...")
        AppIndicatorIPCThread(self, self.Indicator)

        #Start the backend thread.
        self.StartBackend()

        logger.info("MainClass().__init__(): Ready.")

    def ReadConfig(self, StartBackend=False, UpdateCheckNow=True):
        """Parse the config file."""
        #Define all global vars.
        global StartOnBoot
        global StartupUpdateCheck
        global UseWineAutoscan
        global PromptBeforeScanning
        global DevicesToMonitor
        ConfigPresent = True

        #Set them all to initial values.
        DevicesToMonitor = []
        UseWineAutoscan = None
        StartOnBoot = None
        PromptBeforeScanning = None
        StartupUpdateCheck = None
        AutoConfig = False

        #Check the file exists. If it doesn't we'll use default values.
        if os.path.isfile("/usr/share/wineautostart/wineautostart.cfg"):

            #Open it.
            logger.info("MainClass().ReadConfig(): Found config file at /usr/share/wineautostart/wineautostart.cfg. Opening it...")
            ConfigFile = open("/usr/share/wineautostart/wineautostart.cfg", "r")

            #Loop through, reading all required settings.
            logger.info("MainClass().ReadConfig(): Reading configuration from file...")

            for line in ConfigFile:

                #Determine whether we're starting on boot.
                if "StartOnBoot" in line and '#' not in line:
                    #Read the value. Also, convert the result into a boolean value, so it can be used easily.
                    StartOnBoot = bool(int(line.split()[2]))
                    logger.debug("MainClass().ReadConfig(): Found configuration for StartOnBoot ("+unicode(StartOnBoot)+")...")

                    #Apply the setting if needed.
                    if StartOnBoot:
                        if not os.path.isfile("/etc/xdg/autostart/wineautostart.desktop"):
                            logger.debug("MainClass().ReadConfig(): Applying settings for StartOnBoot...")

                            #Send a notification so the user understands why he/she is being asked for a password.
                            subprocess.Popen(["notify-send", "Wine Autostart", "Applying StartOnBoot settings... You may be asked for your password.", "-i", "/usr/share/pixmaps/wineautostart.png"])
                            subprocess.Popen("pkexec cp /usr/share/wineautostart/other/wineautostart.desktop /etc/xdg/autostart/wineautostart.desktop", shell=True).wait()

                    else:
                        if os.path.isfile("/etc/xdg/autostart/wineautostart.desktop"):
                            logger.debug("MainClass().ReadConfig(): Applying settings for StartOnBoot...")

                            #Send a notification so the user understands why he/she is being asked for a password.
                            subprocess.Popen(["notify-send", "Wine Autostart", "Applying StartOnBoot settings... You may be asked for your password.", "-i", "/usr/share/pixmaps/wineautostart.png"])
                            subprocess.Popen("pkexec rm /etc/xdg/autostart/wineautostart.desktop", shell=True).wait()

                #Determine whether we're checking for updates on startup.
                elif "StartupUpdateCheck" in line and '#' not in line:
                    #Read the value. Also, convert the result into a boolean value, so it can be used easily.
                    StartupUpdateCheck = bool(int(line.split()[2]))
                    logger.debug("MainClass().ReadConfig(): Found configuration for StartupUpdateCheck ("+unicode(StartupUpdateCheck)+")...")

                #Determine whether we're using Wine Autoscan.
                elif "UseWineAutoscan" in line and '#' not in line:
                    #Read the value. Also, convert the result into a boolean value, so it can be used easily.
                    UseWineAutoscan = bool(int(line.split()[2]))
                    logger.debug("MainClass().ReadConfig(): Found configuration for UseWineAutoscan ("+unicode(UseWineAutoscan)+")...")

                #Determine whether we're to prompt before looking for software on a disk.
                elif "PromptBeforeScanning" in line and '#' not in line:
                    #Read the value. Also, convert the result into a boolean value, so it can be used easily.
                    PromptBeforeScanning = bool(int(line.split()[2]))
                    logger.debug("MainClass().ReadConfig(): Found configuration for PromptBeforeScanning ("+unicode(PromptBeforeScanning)+")...")

                #Determine which devices to monitor.
                elif "DevicesToMonitor" in line and '#' not in line:
                    #Read the value(s).
                    DevicesToMonitor = line.split()[2:]

                    if DevicesToMonitor in [['None'], []]:
                        DevicesToMonitor = []

                    else:
                        logger.debug("MainClass().ReadConfig(): Found configuration for DevicesToMonitor ("+unicode(DevicesToMonitor)+")...")

            
            #Close the config file.
            ConfigFile.close()

        else:
            #Ask the user to configure.
            logger.warning("MainClass().ReadConfig(): Couldn't find the config file! This is probably the first run. Using default config...")
            self.SetStatus("Please Configure...")
            wx.MessageDialog(None, "Please configure Wine Autostart using the indicator menus, as this is the first run. For the moment, Wine Autostart will use some default settings.", "Wine Autostart - First Run", wx.OK | wx.ICON_EXCLAMATION, pos=wx.DefaultPosition).ShowModal()
            ConfigPresent = False

        #Check if we found all settings.
        if StartOnBoot == None:
            logger.warning("MainClass().ReadConfig(): Using default value of True for StartOnBoot...")
            StartOnBoot = True
            AutoConfig = True

        if StartupUpdateCheck == None:
            logger.warning("MainClass().ReadConfig(): Using default value of True for StartupUpdateCheck...")
            StartupUpdateCheck = False
            AutoConfig = True

        if UseWineAutoscan == None:
            logger.warning("MainClass().ReadConfig(): Using default value of True for UseWineAutoscan...")
            UseWineAutoscan = True
            AutoConfig = True

        if PromptBeforeScanning == None:
            logger.warning("MainClass().ReadConfig(): Using default value of True for PromptBeforeScanning...")
            PromptBeforeScanning = True
            AutoConfig = True

        if DevicesToMonitor == []:
            logger.warning("MainClass().ReadConfig(): Using default value of '/dev/sr0' for DevicesToMonitor...")
            DevicesToMonitor = ['/dev/sr0']
            AutoConfig = True

        if AutoConfig == True and ConfigPresent == True:
            #Let the user know.
            self.SetStatus("Please Configure...")

            logger.warning("MainClass().ReadConfig(): Couldn't find all of the config in the config file! Using default values for settings that were not found...")
            wx.MessageDialog(None, "Please configure Wine Autostart using the indicator menus, as the configuration is incomplete. For the moment, Wine Autostart will use defaults for settings that weren't found.", "Wine Autostart - Configuration Problem", wx.OK | wx.ICON_EXCLAMATION, pos=wx.DefaultPosition).ShowModal()

        #Do the startup update check if set.
        if StartupUpdateCheck and UpdateCheckNow:
            logger.debug("MainClass().ReadConfig(): Doing startup update check as config is set as such...")
            self.CheckForUpdates()

        #Start the backend if we need to.
        if StartBackend:
            logger.debug("MainClass().ReadConfig(): Starting backend as requested by caller...")
            self.StartBackend()

    def BindEvents(self):
        """Bind all events for MainClass"""
        #Close event.
        self.Bind(wx.EVT_CLOSE, self.OnExit)

    def ProcessMessage(self, Line):
        """Process a message (in the form of a line) from the Indicator, and do certain things based on what it is. Also, log it."""
        #Silence the echo for status messages.
        if "Status:" not in Line:
            logger.debug("MainClass().ProcessMessage(): Message from indicator process (self.Indicator): "+Line)

        #React to it, if it's commanding us to do anything.
        if Line == "ShowSettings":
            self.ShowSettings()

        elif Line == "UpdateCheck":
            self.CheckForUpdates()

        elif Line == "ShowPrivacyPolicy":
            self.ShowPrivacyPolicy()

        elif Line == "Start":
            self.StartBackend()

        elif Line == "Stop":
            self.StopBackend()

        elif Line == "ShowAbout":
            self.OnAbout()

        elif Line == "Quit":
            self.OnExit()

    def SendMessage(self, Event=None, Message="", Quiet=False):
        """Send a message to the indicator (self.Indicator). Also, log it if Quiet == False."""
        if Quiet == False:
            logger.debug("MainClass().SendMessage(): Sending message to indicator process: "+Message+"...")

        self.Indicator.stdin.write(Message+"\n")

    def SetStatus(self, Status):
        """Update the status menu item in the indicator to reflect changes in the status."""
        logger.debug("MainClass().SetStatus(): Setting status to '"+Status+"'...")
        self.SendMessage(Message="Status: "+Status, Quiet=True)

    def CheckForUpdates(self):
        """Check whether we're running the latest version of Wine Autostart."""
        logger.info("MainClass().CheckForUpdates(): Checking for updates...")

        try:
            #Send a notification so the user knows Wine Autostart hasn't crashed if getting update info is slow.
            subprocess.Popen(["notify-send", "Wine Autostart", "Please wait a few seconds for Wine Autostart to gather update information.", "-i", "/usr/share/pixmaps/wineautostart.png"])

            #Use bzr to download the version text file from the repo, which contains only that file. Sounds excessive, but how else could I do it?
            logger.debug("MainClass().CheckForUpdates(): Downloading LatestVersion.txt from code.launchpad.net (https://code.launchpad.net/~wineautostart-development-team/wineautostart/latestversion)...")
            subprocess.check_call(['bzr', 'branch', '-q', 'lp:~wineautostart-development-team/wineautostart/latestversion', '/tmp/wineautostart/bzrrepo'])
            logger.debug("MainClass().CheckForUpdates(): Finished downloading LatestVersion.txt. Processing the contents...")

            #Open the file and prepare some variables.
            VersionFile = open("/tmp/wineautostart/bzrrepo/LatestVersion.txt", "r").readlines()
            LatestStable = None
            LatestDevel = None

            #Loop through the file, processing each line.
            for Line in VersionFile:
                if "Stable:" in Line:
                    LatestStable = Line.split()[1]
                elif "Development:" in Line:
                    LatestDevel = Line.split()[1]

            #Check we got all the data.
            if None in [LatestStable, LatestDevel]:
                #We didn't!
                logger.error("MainClass().CheckForUpdates(): Bad update information! Telling user...")
                wx.MessageDialog(None, "Wine Autostart failed to process the update information! This is either because of bad update information, or a bug in Wine Autostart. Please contact me (via www.launchpad.net/~hamishmb), so I can fix it. Thanks.", "Wine Autostart - Update Status", wx.OK | wx.ICON_ERROR, pos=wx.DefaultPosition).ShowModal()
            else:
                #We did. Compare the update information to this program's version an type (Stable or Development). As we do this, create a multiline string for the dialog to report to the user.
                UpdateInfo = "Update Information:\n\nProgram Version: "+Version+"\nRelease Type: "+ReleaseType+"\n\nIf you are using the PPA (www.launchpad.net/~hamishmb/myppa), you will get automatic updates.\n\n"

                #First do the stable version.
                logger.debug("MainClass().CheckForUpdates(): Comparing stable version to current version...")
                Versions = [Version, LatestStable]

                #Order the list so the last entry has the latest version number.
                Versions = sorted(Versions, key=LooseVersion)

                #Now compare the last entry to the current version number. If they are equal then this is the latest version, else we have an old version.
                if Versions[-1] == Version and ReleaseType == "Stable":
                    #We have the latest stable version.
                    UpdateInfo += "You are running the latest stable version.\n\n"

                elif ReleaseType == "Stable" and Versions[-1] != Version:
                    #We are running an older stable version.
                    UpdateInfo += "You are running an older stable version. The latest stable version is "+LatestStable+", and is downloadable from www.launchpad.net/wineautostart/+release/"+LatestStable+".\n\n"

                elif ReleaseType == "Development":
                    #We are running a development version. Deal with that in a minute.
                    UpdateInfo += "The latest stable version is "+LatestStable+".\n\n"

                #Now do the development version.
                logger.debug("MainClass().CheckForUpdates(): Comparing development version to current version...")
                Versions = [Version, LatestDevel]

                #Order the list so the last entry has the latest version number.
                Versions = sorted(Versions, key=LooseVersion)

                #Now compare the last entry to the current version number.
                if Versions[-1] == Version and ReleaseType == "Development":
                    #We have the latest development version.
                    UpdateInfo += "You are running the latest development version."

                elif ReleaseType == "Development" and Versions[-1] != Version:
                    #We are running an older development version.
                    UpdateInfo += "You are running an older development version. The latest development version is "+LatestDevel+", and is downloadable from www.launchpad.net/wineautostart/+release/"+LatestDevel

                elif ReleaseType == "Stable":
                    #We are running a stable version.
                    UpdateInfo += "The latest development version is "+LatestDevel+".\n"

                #Delete the directory with the update info.
                logger.debug("MainClass().CheckForUpdates(): Deleting update info...")
                shutil.rmtree("/tmp/wineautostart/bzrrepo")

                #Finally, show the user the gathered info.
                logger.debug("MainClass().CheckForUpdates(): Showing the user the finished info...")
                wx.MessageDialog(None, UpdateInfo, "Wine Autostart - Update Status", wx.OK | wx.ICON_INFORMATION, pos=wx.DefaultPosition).ShowModal()

        except subprocess.CalledProcessError:
            #Bad/No internet connection! Warn the user.
            logger.error("MainClass().CheckForUpdates(): Couldn't establish a connection to code.launchpad.net! The internet connection is probably at fault here.")
            wx.MessageDialog(None, "Wine Autostart failed to download the update information! Please check your internet connection. If you were prompted for one, you may have refused to enter your SSH key password. Don't worry; it's safe to do that.", "Wine Autostart - Update Status", wx.OK | wx.ICON_ERROR, pos=wx.DefaultPosition).ShowModal()

    def ShowPrivacyPolicy(self):
        """Show PrivPolWindow"""
        PrivPolWindow(self).Show()

    def ShowSettings(self):
        """Show SettingsWindow"""
        if RunningSoftware == False:
            SettingsWindow(self).Show()

        else:
            logger.error("MainClass().ShowSettings(): Can't change settings while running software! Warning user...")
            wx.MessageDialog(None, "Wine Autostart is currently running software! Please close the software before editing settings.", "Wine Autostart - Error", wx.OK | wx.ICON_ERROR, pos=wx.DefaultPosition).ShowModal()

    def StartBackend(self):
        """Start the backend"""
        global RunningBackend
        if RunningBackend == False:
            logger.debug("MainClass().StartBackend(): Starting backend...")
            RunningBackend = True
            BackendThread(self)

            #Disable the start item, and enable the stop item.
            self.SendMessage(Message="DisableStartItem")
            time.sleep(1)
            self.SendMessage(Message="EnableStopItem")

        else:
            logger.warning("MainClass().StartBackend(): Backend is already running! Doing nothing...")

    def StopBackend(self):
        """Stop the backend"""
        if RunningSoftware:
            logger.error("MainClass().StopBackend(): Can't stop the backend while running software! Warning user...")
            wx.MessageDialog(None, "Wine Autostart is currently running software! Please close the software before stopping Wine Autostart. You may need to wait a few moments for Wine Autostart to recognise software is no longer running.", "Wine Autostart - Error", wx.OK | wx.ICON_ERROR, pos=wx.DefaultPosition).ShowModal()

        else:
            logger.debug("MainClass().StopBackend(): Stopping backend...")
            global RunningBackend
            RunningBackend = False

            #Disable the stop item, and enable the start item.
            self.SendMessage(Message="DisableStopItem")
            time.sleep(1)
            self.SendMessage(Message="EnableStartItem")

    def OnAbout(self):
        """Show the about dialog"""
        aboutbox = wx.AboutDialogInfo()
        aboutbox.SetIcon(AppIcon)
        aboutbox.Name = "Wine Autostart"
        aboutbox.Version = Version+"\nReleased "+ReleaseDate+"\n"
        aboutbox.Copyright = "(C) 2013-2015 Hamish McIntyre-Bhatty"
        aboutbox.Description = "Allows Windows Software disks\nto be run under Linux with WINE"
        aboutbox.WebSite = ("https://launchpad.net/wineautostart", "Launchpad page")
        aboutbox.Developers = ["Hamish McIntyre-Bhatty"]
        aboutbox.Artists = ["Holly McIntyre-Bhatty (Logos)", "Hamish McIntyre-Bhatty (Throbbers)"]
        aboutbox.License = "Wine Autostart is free software: you can redistribute it and/or modify it\nunder the terms of the GNU General Public License version 3 or,\nat your option, any later version.\n\nWine Autostart is distributed in the hope that it will be useful,\nbut WITHOUT ANY WARRANTY; without even the implied warranty of\nMERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\nGNU General Public License for more details.\n\nYou should have received a copy of the GNU General Public License\nalong with Wine Autostart.  If not, see <http://www.gnu.org/licenses/>."

        #Show the About Box
        wx.AboutBox(aboutbox)

    def ShowThreadMsgdlg(self,msg,kind="info"):
        """Show a Message dialog for a background thread. Use this with: wx.CallAfter(self.ParentWindow.ShowThreadMsgdlg, kind=<kind>, msg=<message>)"""
        global dlgClosed

        if kind == "info":
            title = "Wine Autostart - Information"
            style = wx.OK | wx.ICON_INFORMATION
        elif kind == "warning":
            title = "Wine Autostart - Warning"
            style = wx.OK | wx.ICON_EXCLAMATION
        elif kind == "error":
            title = "Wine Autostart - Error"
            style = wx.OK | wx.ICON_ERROR

        dlg = wx.MessageDialog(None, msg, title, style, pos=wx.DefaultPosition).ShowModal()
        dlgClosed = True

    def ShowThreadYesNodlg(self,msg,title="Wine Autostart - Question"):
        """Show a Yes/No dialog for a background thread. Use this with: wx.CallAfter(self.ParentWindow.ShowThreadYesNodlg, msg=<message>, title=<title>)"""
        global dlgResult
        dlg = wx.MessageDialog(None, msg, title, wx.YES_NO | wx.ICON_QUESTION)

        if dlg.ShowModal() == wx.ID_YES:
            dlgResult = "Yes"
        else:
            dlgResult = "No"

        logger.debug("MainClass().ShowThreadYesNodlg(): Result of BackendThread yesno dlg was: "+dlgResult)

    def ShowThreadChoicedlg(self,msg,choices,title="Wine Autostart - Select an Option"):
        """Show a Single Choice dialog for a background thread. Use this with: wx.CallAfter(self.ParentWindow.ShowThreadChoicedlg, msg=<message>, title=<title>, choices=<data>)"""
        global dlgResult

        dlg = wx.SingleChoiceDialog(None, msg, title, choices, pos=wx.DefaultPosition)

        if dlg.ShowModal() == wx.ID_OK:
            dlgResult = dlg.GetStringSelection()
        else:
            dlgResult = "Clicked no..."

        logger.debug("MainClass().ShowThreadChoicedlg(): Result of InitThread choice dlg was: "+dlgResult)

    def OnExit(self,Event=None):
        """Exit the program"""
        if RunningSoftware:
            logger.error("MainClass().StopBackend(): Can't close Wine Autostart while running software! Warning user...")
            wx.MessageDialog(None, "Wine Autostart is currently running software! Please close the software before exiting Wine Autostart. You may need to wait a few moments for Wine Autostart to recognise software is no longer running.", "Wine Autostart - Error", wx.OK | wx.ICON_ERROR, pos=wx.DefaultPosition).ShowModal()

        else:
            logger.info("MainClass().OnExit(): Exiting...")

            #Stop the backend thread, if it's running.
            global Exiting
            Exiting = True
            self.StopBackend()

            #Prompt user to save the log file.
            dlg = wx.MessageDialog(None, "Do you want to keep Wine Autostart's log file? For privacy reasons, Wine Autostart will delete its log file when closing. If you want to save it, which is helpful for debugging if something went wrong, click yes, and otherwise click no.", "Wine Autostart - Question", style=wx.YES_NO | wx.ICON_QUESTION, pos=wx.DefaultPosition)

            if dlg.ShowModal() == wx.ID_YES:
                #Make sure it eventually gets saved, even if there are permission errors and suchlike.
                while True:
                    #Ask the user where to save it.
                    Dlg = wx.FileDialog(None, "Save log file to...", defaultDir=os.environ["HOME"], wildcard="Log Files (*.log)|*.log|All Files/Devices (*)|*" , style=wx.SAVE)

                    if Dlg.ShowModal() == wx.ID_OK:
                        #Get the path.
                        File = Dlg.GetPath()

                        #Try and export to it.
                        try:
                            subprocess.check_output(["cp", "/tmp/wineautostart/wineautostart.log", File], stderr=subprocess.STDOUT)

                        except subprocess.CalledProcessError, Error:
                            if "Permission denied" in unicode(Error.output, errors='ignore'):
                                wx.MessageDialog(None, "Couldn't save log to "+File+"! Wine Autostart doesn't have permission to write to that folder. Please try saving to a different folder.", "Wine Autostart - Error!", style=wx.OK | wx.ICON_ERROR, pos=wx.DefaultPosition).ShowModal()

                            else:
                                wx.MessageDialog(None, "Couldn't save log to "+File+"! Please try saving to a different folder.", "Wine Autostart - Error!", style=wx.OK | wx.ICON_ERROR, pos=wx.DefaultPosition).ShowModal()

                        else:
                            wx.MessageDialog(None, 'Done! Wine Autostart will now exit.', 'Wine Autostart - Information', wx.OK | wx.ICON_INFORMATION).ShowModal()
                            break

                    else:
                        wx.MessageDialog(None, 'Okay, Wine Autostart will now exit without saving the log file.', 'Wine Autostart - Information', wx.OK | wx.ICON_INFORMATION).ShowModal()
                        break

            else:
                wx.MessageDialog(None, 'Okay, Wine Autostart will now exit without saving the log file.', 'Wine Autostart - Information', wx.OK | wx.ICON_INFORMATION).ShowModal()

            #Destroy the indicator.
            self.SendMessage(Message="Quit")
            time.sleep(1)
            self.Indicator.terminate()

            #Empty and remove the temporary directory.
            if os.path.isdir("/tmp/wineautostart"):
                shutil.rmtree("/tmp/wineautostart")

            #Use wx.Exit() here as we've already done all the cleanup, and Wine Autostart randomly hangs here.
            self.Destroy()
            wx.Exit()

#End Main class.
#Begin Privacy Policy Window.
class PrivPolWindow(wx.Frame):
    def __init__(self,ParentWindow):
        """Initialize PrivPolWindow"""
        wx.Frame.__init__(self, parent=wx.GetApp().TopWindow, title="Wine Autostart - Privacy Policy", size=(400,310), style=wx.DEFAULT_FRAME_STYLE)
        self.Panel = wx.Panel(self)
        self.SetClientSize(wx.Size(400,310))
        self.ParentWindow = ParentWindow
        wx.Frame.SetIcon(self, AppIcon)

        logger.debug("PrivPolWindow().__init__(): Creating widgets...")
        self.CreateWidgets()

        logger.debug("PrivPolWindow().__init__(): Setting up sizers...")
        self.SetupSizers()

        logger.debug("PrivPolWindow().__init__(): Binding Events...")
        self.BindEvents()

        #Call Layout() on self.Panel() to ensure it displays properly.
        self.Panel.Layout()

        logger.debug("PrivPolWindow().__init__(): Ready. Waiting for events...")

    def CreateWidgets(self):
        """Create all widgets for PrivPolWindow"""
        #Make a text box to contain the policy's text.
        self.TextBox = wx.TextCtrl(self.Panel, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_WORDWRAP)

        #Populate the text box.
        self.TextBox.LoadFile("/usr/share/wineautostart/other/privacypolicy.txt")

        #Scroll the text box back up to the top.
        self.TextBox.SetInsertionPoint(0)

        #Make a button to close the dialog.
        self.CloseButton = wx.Button(self.Panel, -1, "Okay")

    def SetupSizers(self):
        """Set up sizers for PrivPolWindow"""
        #Make a boxsizer.
        MainSizer = wx.BoxSizer(wx.VERTICAL)

        #Add each object to the main sizer.
        MainSizer.Add(self.TextBox, 1, wx.EXPAND|wx.ALL, 10)
        MainSizer.Add(self.CloseButton, 0, wx.BOTTOM|wx.CENTER, 10)

        #Get the sizer set up for the frame.
        self.Panel.SetSizer(MainSizer)
        MainSizer.SetMinSize(wx.Size(400,310))
        MainSizer.SetSizeHints(self)

    def BindEvents(self):
        """Bind events so we can close this window."""
        self.Bind(wx.EVT_BUTTON, self.OnClose, self.CloseButton)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self,Event=None):
        """Close PrivPolWindow"""
        self.Destroy()

#End Privacy Policy Window.
#Begin Settings Window.
class SettingsWindow(wx.Frame):
    def __init__(self,ParentWindow):
        """Initialize SettingsWindow"""
        wx.Frame.__init__(self, parent=ParentWindow, title="Wine Autostart - Settings", size=(510,380), style=wx.DEFAULT_FRAME_STYLE)
        self.Panel = wx.Panel(self)
        self.SetClientSize(wx.Size(510,380))
        self.ParentWindow = ParentWindow
        self.CurrentDeviceSelections = DevicesToMonitor[:]
        wx.Frame.SetIcon(self, AppIcon)

        #Create text.
        logger.debug("SettingsWindow().__init__(): Creating text...")
        self.CreateText()

        #Create checkboxes.
        logger.debug("SettingsWindow().__init__(): Creating CheckBoxes...")
        self.CreateCheckBoxes()

        #Create buttons.
        logger.debug("SettingsWindow().__init__(): Creating buttons...")
        self.CreateButtons()

        #Create other widgets.
        logger.debug("SettingsWindow().__init__(): Creating other remaining widgets...")
        self.CreateOtherWidgets()

        #Setup sizers.
        logger.debug("SettingsWindow().__init__(): Setting up sizers...")
        self.SetupSizers()

        #Setup the window.
        logger.debug("SettingsWindow().__init__(): Setting up window...")
        self.SetupWindow()

        #Bind events.
        logger.debug("SettingsWindow().__init__(): Binding events...")
        self.BindEvents()

        #Call Layout() on self.Panel() to ensure it displays properly.
        self.Panel.Layout()

        #Stop the backend thread, if it's running.
        logger.info("SettingsWindow().SaveConfig(): Stopping backend thread...")
        self.ParentWindow.StopBackend()

        logger.info("SettingsWindow().__init__(): Ready. Waiting for events...")

    def CreateText(self):
        """Create all text for SettingsWindow"""
        self.TitleText = wx.StaticText(self.Panel, -1, "Welcome to settings. Here you can set everything as you prefer.")
        self.ConfigText = wx.StaticText(self.Panel, -1, "Configuration settings:")
        self.DevicesToMonitorText = wx.StaticText(self.Panel, -1, "Which devices do you want Wine Autostart to monitor?")

    def CreateCheckBoxes(self):
        """Create all CheckBoxes for SettingsWindow"""
        self.StartOnBootCB = wx.CheckBox(self.Panel, -1, "Start Wine Autostart on boot")
        self.StartupUpdateCheckCB = wx.CheckBox(self.Panel, -1, "Check for updates on startup.")
        self.UseWineAutoscanCB = wx.CheckBox(self.Panel, -1, "Scan for software\nif no autorun info is found")
        self.PromptBeforeScanningCB = wx.CheckBox(self.Panel, -1, "Ask before looking\nfor software on a disk")
 
    def CreateButtons(self):
        """Create all Buttons for SettingsWindow"""
        self.RevertButton = wx.Button(self.Panel, -1, "Revert Changes")
        self.RefreshButton = wx.Button(self.Panel, -1, "Update Drive List")
        self.ImportButton = wx.Button(self.Panel, -1, "Import Config")
        self.ExportButton = wx.Button(self.Panel, -1, "Export Config")
        self.CloseButton = wx.Button(self.Panel, -1, "Save Config and Close")

    def CreateOtherWidgets(self):
        """Create all the remaining widgets for SettingsWindow"""
        #Create the animation for the throbber here too.
        throb = wx.animate.Animation("/usr/share/wineautostart/images/ThrobberDesign.gif")
        self.Throbber = wx.animate.AnimationCtrl(self.Panel, -1, throb)
        self.Throbber.SetUseWindowBackgroundColour(True)
        self.Throbber.SetInactiveBitmap(wx.Bitmap("/usr/share/wineautostart/images/ThrobberRest.png", wx.BITMAP_TYPE_PNG))
        self.Throbber.SetClientSize(wx.Size(30,30))

    def SetupSizers(self):
        """Set up sizers for SettingsWindow"""
        #Make the main boxsizer.
        self.MainSizer = wx.BoxSizer(wx.VERTICAL)

        #Make the main config boxsizer.
        MainConfigSizer = wx.BoxSizer(wx.HORIZONTAL)

        #Make the checkbox sizer.
        CheckBoxSizer = wx.BoxSizer(wx.VERTICAL)

        #Add objects to the checkbox sizer.
        CheckBoxSizer.Add(self.StartOnBootCB, 0, wx.ALIGN_LEFT)
        CheckBoxSizer.Add(self.StartupUpdateCheckCB, 0, wx.TOP|wx.ALIGN_LEFT, 10)
        CheckBoxSizer.Add(self.UseWineAutoscanCB, 0, wx.TOP|wx.ALIGN_LEFT, 10)
        CheckBoxSizer.Add(self.PromptBeforeScanningCB, 0, wx.TOP|wx.ALIGN_LEFT, 10)

        #Make the right-hand sizer.
        RightHandSizer = wx.BoxSizer(wx.VERTICAL)

        #Add objects to the right-hand sizer.
        RightHandSizer.Add(self.ConfigText, 0, wx.ALIGN_CENTER)
        RightHandSizer.Add(self.RevertButton, 0, wx.TOP|wx.ALIGN_CENTER, 20)
        RightHandSizer.Add(self.ImportButton, 0, wx.TOP|wx.ALIGN_CENTER, 20)
        RightHandSizer.Add(self.ExportButton, 0, wx.TOP|wx.ALIGN_CENTER, 20)

        #Add objects to the main config sizer.
        MainConfigSizer.Add(CheckBoxSizer, 1, wx.CENTER)
        MainConfigSizer.Add(wx.StaticLine(self.Panel), 0, wx.TOP|wx.BOTTOM|wx.EXPAND, 5)
        MainConfigSizer.Add(RightHandSizer, 1, wx.CENTER)

        #Make the device selection sizer.
        box = wx.StaticBox(self.Panel, -1, "Optical Devices")
        self.DeviceSizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        #Make the button sizer.
        ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)

        #Add objects to the button sizer.
        ButtonSizer.Add(self.RefreshButton, 1, wx.ALIGN_BOTTOM)
        ButtonSizer.Add(self.CloseButton, 1, wx.LEFT|wx.ALIGN_BOTTOM, 10)

        #Add objects to the main sizer.
        self.MainSizer.Add(self.TitleText, 0, wx.TOP|wx.CENTER, 10)
        self.MainSizer.Add(wx.StaticLine(self.Panel), 0, wx.TOP|wx.BOTTOM|wx.EXPAND, 5)
        self.MainSizer.Add(MainConfigSizer, 0, wx.ALL|wx.CENTER|wx.EXPAND, 10)
        self.MainSizer.Add(wx.StaticLine(self.Panel), 0, wx.TOP|wx.BOTTOM|wx.EXPAND, 5)
        self.MainSizer.Add(self.DevicesToMonitorText, 0, wx.TOP|wx.CENTER, 10)
        self.MainSizer.Add(self.Throbber, 0, wx.TOP|wx.CENTER|wx.FIXED_MINSIZE, 10)
        self.MainSizer.Add(self.DeviceSizer, 1, wx.ALL|wx.CENTER|wx.EXPAND, 10)
        self.MainSizer.Add(ButtonSizer, 0, wx.ALL ^ wx.TOP|wx.CENTER|wx.EXPAND, 10)

        #Get the sizer set up for the frame.
        self.Panel.SetSizer(self.MainSizer)
        self.MainSizer.SetMinSize(wx.Size(510,380))
        self.MainSizer.SetSizeHints(self)

    def SetupWindow(self, Event=None):
        """(re)Populate the window with settings."""
        #Log it if we're reverting config.
        if Event != None:
            logger.debug("SettingsWindow().SetupWindow(): Reverting config...")

        #StartOnBoot:
        if StartOnBoot:
            self.StartOnBootCB.SetValue(1)
        else:
            self.StartOnBootCB.SetValue(0)

        #StartupUpdateCheck:
        if StartupUpdateCheck:
            self.StartupUpdateCheckCB.SetValue(1)
        else:
            self.StartupUpdateCheckCB.SetValue(0)

        #UseWineAutoscan:
        if UseWineAutoscan:
            self.UseWineAutoscanCB.SetValue(1)
        else:
            self.UseWineAutoscanCB.SetValue(0)

        #PromptBeforeScanning:
        if PromptBeforeScanning:
            self.PromptBeforeScanningCB.SetValue(1)
        else:
            self.PromptBeforeScanningCB.SetValue(0)

        #DevicesToMonitor:
        if Event == None:
            #Don't block the initialization of the panel when calling the method.
            wx.CallLater(500, self.GetDeviceInfo)
        else:
            self.CurrentDeviceSelections = DevicesToMonitor[:]
            self.UpdateCheckBoxes()

    def BindEvents(self):
        """Bind all events."""
        self.Bind(wx.EVT_BUTTON, self.SetupWindow, self.RevertButton)
        self.Bind(wx.EVT_BUTTON, self.ImportConfig, self.ImportButton)
        self.Bind(wx.EVT_BUTTON, self.ExportConfig, self.ExportButton)
        self.Bind(wx.EVT_BUTTON, self.GetDeviceInfo, self.RefreshButton)
        self.Bind(wx.EVT_BUTTON, self.SaveConfig, self.CloseButton)
        self.Bind(wx.EVT_CLOSE, self.SaveConfig)

    def OnCheckBox(self, Event=None):
        """Save selection information about the checkbox that triggered this function, so we can keepthe user's selection even when refreshing the device list"""
        ID = Event.GetId()
        CheckBox = self.Panel.FindWindowById(ID)
        Device = CheckBox.GetLabel().split()[0].replace(",", "")

        if CheckBox.IsChecked() and Device not in self.CurrentDeviceSelections:
            #Add the device to the list.
            logger.debug("SettingsWindow().OnCheckBox(): Adding device: "+Device+" to the current device selections list...")
            self.CurrentDeviceSelections.append(Device)
        elif CheckBox.IsChecked() == False:
            #Remove the device from the list, if it's in the list.
            logger.debug("SettingsWindow().OnCheckBox(): Removing device: "+Device+" from the current device selections list...")
            try:
                Index = self.CurrentDeviceSelections.index(Device)
            except ValueError:
                pass
            else:
                self.CurrentDeviceSelections.pop(Index)

    def GetDeviceInfo(self, Event=None):
        """Call the thread to get device info, disable the update button, and start the throbber"""
        logger.info("SettingsWindow().UpdateDeviceInfo(): Getting new device information...")
        self.RefreshButton.Disable()
        GetDeviceInformation(self)
        self.Throbber.Play()

    def ReceiveDeviceInfo(self, Info):
        """Get new device info and to call the function that updates the checkboxes"""
        logger.info("MainWindow().ReceiveDeviceInfo(): Getting new device information...")
        global DeviceInfo
        DeviceInfo = Info

        #Update the checkboxes in self.DeviceSizer.
        self.UpdateCheckBoxes()

        #Stop the throbber and enable the update button.
        self.Throbber.Stop()
        self.RefreshButton.Enable()

    def UpdateCheckBoxes(self):
        """Remove all device checkboxes, and add new ones"""
        #First, remove all checkboxes in the sizer and clear the IDList.
        self.DeviceSizer.Clear(True)
        self.CheckBoxIDList = []

        #Now add new ones.
        for Device in DeviceInfo[0]:
            #Get the element number of the device.
            DeviceNumber = DeviceInfo[0].index(Device)

            #Find the vendor, product and description for each device.
            Vendor = DeviceInfo[2][DeviceNumber]
            Product = DeviceInfo[3][DeviceNumber]
            Description = DeviceInfo[5][DeviceNumber]

            #Create a checkbox object, and add it to the sizer, save its ID, and bind an event for it.
            CheckBox = wx.CheckBox(self.Panel, -1, Device+", "+Vendor+" "+Product+", "+Description)
            self.DeviceSizer.Add(CheckBox, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_TOP)
            self.CheckBoxIDList.append(CheckBox.GetId())
            self.Bind(wx.EVT_CHECKBOX, self.OnCheckBox, CheckBox)

            #Check it if the device is one of our current selections.
            if Device in self.CurrentDeviceSelections:
                CheckBox.SetValue(1)
            else:
                CheckBox.SetValue(0)

        #Make sure the window displays properly.
        self.MainSizer.Fit(self)
        self.Panel.Layout()

    def ImportConfig(self, Event=None):
        """Import config from a different file. Don't save it or permanently set it."""
        logger.debug("SettingsWindow().ImportConfig(): Getting user selection...")

        Dlg = wx.FileDialog(self.Panel, "Import From...", defaultDir=os.environ["HOME"], wildcard="Configuration Files (*.cfg)|*.cfg|All Files/Devices (*)|*" , style=wx.OPEN)

        if Dlg.ShowModal() == wx.ID_OK:
            #Get the path.
            File = Dlg.GetPath()
            logger.info("SettingsWindow().ImportConfig(): Importing config from: "+File+"...")

            #Attempt to open it.
            logger.info("SettingsWindow().ImportConfig(): Attempting to open config file at /usr/share/wineautostart/wineautostart.cfg...")
            try:
                ConfigFile = open(File, "r")

            except IOError, Error:

                if "Permission denied" in unicode(Error):
                    logger.error("SettingsWindow().ImportConfig(): Error importing config from: "+File+"! Insufficient permissions. Warning user and giving up...")
                    wx.MessageDialog(self.Panel, "Couldn't import config from "+File+"! Wine Autostart doesn't have permission to read that file. Please try importing from a different file.", "Wine Autostart - Error!", style=wx.OK | wx.ICON_ERROR, pos=wx.DefaultPosition).ShowModal()

                else:
                    logger.error("SettingsWindow().ImportConfig(): Error importing config from: "+File+"! Warning user and giving up...")
                    wx.MessageDialog(self.Panel, "Couldn't import config from "+File+"! Please try importing from a different file.", "Wine Autostart - Error!", style=wx.OK | wx.ICON_ERROR, pos=wx.DefaultPosition).ShowModal()

            else:

                logger.info("SettingsWindow().ImportConfig(): Successfully opened: "+File+". Reading config...")

                #Loop through, reading all required settings.
                for line in ConfigFile:

                    #Determine whether we're starting on boot.
                    if "StartOnBoot" in line:
                        #Read the value. Also, convert the result into a boolean value, so it can be used easily.
                        self.StartOnBootCB.SetValue(bool(int(line.split()[2])))
                        logger.debug("SettingsWindow().ImportConfig(): Found configuration for StartOnBoot ("+unicode(StartOnBoot)+")...")

                    #Determine whether we're checking for updates on startup.
                    elif "StartupUpdateCheck" in line:
                        #Read the value. Also, convert the result into a boolean value, so it can be used easily.
                        self.StartupUpdateCheckCB.SetValue(bool(int(line.split()[2])))
                        logger.debug("SettingsWindow().ImportConfig(): Found configuration for StartupUpdateCheck ("+unicode(StartupUpdateCheck)+")...")

                    #Determine whether we're using Wine Autoscan.
                    elif "UseWineAutoscan" in line:
                        #Read the value. Also, convert the result into a boolean value, so it can be used easily.
                        self.UseWineAutoscanCB.SetValue(bool(int(line.split()[2])))
                        logger.debug("SettingsWindow().ImportConfig(): Found configuration for UseWineAutoscan ("+unicode(UseWineAutoscan)+")...")

                    #Determine whether we're to prompt before looking for software on a disk.
                    elif "PromptBeforeScanning" in line:
                        #Read the value. Also, convert the result into a boolean value, so it can be used easily.
                        self.PromptBeforeScanningCB.SetValue(bool(int(line.split()[2])))
                        logger.debug("SettingsWindow().ImportConfig(): Found configuration for PromptBeforeScanning ("+unicode(PromptBeforeScanning)+")...")

                    #Determine which devices to monitor.
                    elif "DevicesToMonitor" in line:
                        #Read the value(s).
                        self.ImportedDevicesToMonitor = line.split()[2:]
                        logger.debug("SettingsWindow().ImportConfig(): Found configuration for DevicesToMonitor ("+unicode(DevicesToMonitor)+")...")

                        #Set the checkboxes.
                        for ID in self.CheckBoxIDList:
                            #Get the device associated wth each checkbox.
                            CheckBox = self.Panel.FindWindowById(ID)
                            Device = CheckBox.GetLabel().split()[0].replace(",", "")

                            if Device in self.ImportedDevicesToMonitor:
                                CheckBox.SetValue(1)
                            else:
                                CheckBox.SetValue(0)

                        self.CurrentDeviceSelections = self.ImportedDevicesToMonitor[:]

                #Close the config file.
                ConfigFile.close()

        else:
            logger.info("SettingsWindow().ImportConfig(): User canceled selection dialog...")

    def ExportConfig(self, Event=None):
        """Export Wine Autostart's settings to a file specified by the user"""
        logger.debug("SettingsWindow().ExportConfig(): Getting user selection...")

        Dlg = wx.FileDialog(self.Panel, "Export As...", defaultDir=os.environ["HOME"], wildcard="Configuration Files (*.cfg)|*.cfg|All Files/Devices (*)|*" , style=wx.SAVE)

        if Dlg.ShowModal() == wx.ID_OK:
            #Get the path.
            File = Dlg.GetPath()
            logger.info("SettingsWindow().ExportConfig(): Exporting config to: "+File+"...")

            #Try and export to it.
            try:
                subprocess.check_output(["cp", "/usr/share/wineautostart/wineautostart.cfg", File], stderr=subprocess.STDOUT)

            except subprocess.CalledProcessError, Error:

                if "Permission denied" in unicode(Error.output, errors='ignore'):
                    logger.error("SettingsWindow().ExportConfig(): Error exporting config to: "+File+"! Insufficient permissions. Warning user and giving up...")
                    wx.MessageDialog(self.Panel, "Couldn't export config to "+File+"! Wine Autostart doesn't have permission to write to that folder. Please try exporting to a different folder.", "Wine Autostart - Error!", style=wx.OK | wx.ICON_ERROR, pos=wx.DefaultPosition).ShowModal()

                else:
                    logger.error("SettingsWindow().ExportConfig(): Error exporting config to: "+File+"! Warning user and giving up...")
                    wx.MessageDialog(self.Panel, "Couldn't export config to "+File+"! Please try exporting to a different folder.", "Wine Autostart - Error!", style=wx.OK | wx.ICON_ERROR, pos=wx.DefaultPosition).ShowModal()

            else:
                logger.info("SettingsWindow().ExportConfig(): Finished exporting config to: "+File+"...")
                wx.MessageDialog(self.Panel, "Your config has been successfully exported to "+File+".", "Wine Autostart - Information", style=wx.OK | wx.ICON_INFORMATION, pos=wx.DefaultPosition).ShowModal()

        else:
            logger.info("SettingsWindow().ExportConfig(): User canceled selection dialog...")

    def SaveConfig(self, Event=None):
        """Save all options, and exit SettingsWindow"""
        logger.info("SettingsWindow().SaveConfig(): Saving Config...")

        #Define global variables:
        global StartOnBoot
        global StartupUpdateCheck
        global UseWineAutoscan
        global PromptBeforeScanning
        global DevicesToMonitor

        #Checkboxes:
        #Start on boot setting.
        if self.StartOnBootCB.IsChecked():
            StartOnBoot = True
            logger.info("SettingsWindow().SaveConfig(): Starting On Boot: True.")
        else:
            StartOnBoot = False
            logger.info("SettingsWindow().SaveConfig(): Starting On Boot: False.")

        #Check for updates on startup setting.
        if self.StartupUpdateCheckCB.IsChecked():
            StartupUpdateCheck = True
            logger.info("SettingsWindow().SaveConfig(): Check for updates on startup: True.")
        else:
            StartupUpdateCheck = False
            logger.info("SettingsWindow().SaveConfig(): Check for updates on startup: False.")

        #Use Wine Autoscan (if there is no autorun info) setting.
        if self.UseWineAutoscanCB.IsChecked():
            UseWineAutoscan = True
            logger.info("SettingsWindow().SaveConfig(): Use Wine Autoscan: True.")
        else:
            UseWineAutoscan = False
            logger.info("SettingsWindow().SaveConfig(): Use Wine Autoscan: False.")

        #Prompt before scanning option.
        if self.PromptBeforeScanningCB.IsChecked():
            PromptBeforeScanning = True
            logger.info("SettingsWindow().SaveConfig(): Prompt before scanning: True.")
        else:
            PromptBeforeScanning = False
            logger.info("SettingsWindow().SaveConfig(): Prompt before scanning: False.")

        #Devices To Monitor:
        DevicesToMonitor = self.CurrentDeviceSelections[:]

        #Now we need to write the config to the file.
        #Create it if it doesn't exist.
        if not os.path.isfile("/usr/share/wineautostart/wineautostart.cfg"):
            subprocess.Popen(["pkexec", "touch", "/usr/share/wineautostart/wineautostart.cfg"]).wait()

        #Open the file in read mode, so we can find the important bits of config to edit. Also, use a list to temporarily store the modified lines.
        ConfigFile = open("/usr/share/wineautostart/wineautostart.cfg", 'r')
        NewFileContents = []

        #Set these variables so we know if we set all the settings.
        SetStartOnBoot = False
        SetStartupUpdateCheck = False
        SetUseWineAutoscan = False
        SetPromptBeforeScanning = False
        SetDevicesToMonitor = False

        #Loop through each line in the file, paying attention only to the important ones.
        for line in ConfigFile:
            #Look for the StartOnBoot setting.
            if 'StartOnBoot' in line and '=' in line and '#' not in line:
                #Found it! Seperate the line.
                SetStartOnBoot = True
                head, sep, Temp = line.partition('=')

                #Reassemble the line.
                line = head+sep+" "+unicode(int(StartOnBoot))+"\n"

            #Look for the StartupUpdateCheck setting.
            elif 'StartupUpdateCheck' in line and '=' in line and '#' not in line:
                #Found it, seperate the line.
                SetStartupUpdateCheck = True
                head, sep, Temp = line.partition('=')

                #Reassemble the line.
                line = head+sep+" "+unicode(int(StartupUpdateCheck))+"\n"

            #Look for the UseWineAutoscan setting.
            elif 'UseWineAutoscan' in line and '=' in line and '#' not in line:
                #Found it, seperate the line.
                SetUseWineAutoscan = True
                head, sep, Temp = line.partition('=')

                #Reassemble the line.
                line = head+sep+" "+unicode(int(UseWineAutoscan))+"\n"

            #Look for the PromptBeforeScanning setting.
            elif 'PromptBeforeScanning' in line and '=' in line and '#' not in line:
                #Found it, seperate the line.
                SetPromptBeforeScanning = True
                head, sep, Temp = line.partition('=')

                #Reassemble the line.
                line = head+sep+" "+unicode(int(PromptBeforeScanning))+"\n"

            #Look for the DevicesToMonitor setting.
            elif 'DevicesToMonitor' in line and '=' in line and '#' not in line:
                #Found it, seperate the line.
                SetDevicesToMonitor = True
                head, sep, Temp = line.partition('=')

                if DevicesToMonitor == []:
                    DevicesToMonitor = ['None']

                #Reassemble the line.
                line = head+sep+" "+' '.join(DevicesToMonitor)+"\n"

            NewFileContents.append(line)

        #Check that everything was set. If not, write that config now.
        if SetStartOnBoot == False:
            NewFileContents.append("#Configuration for Wine Autostart 2.0.2. '1' represents True and '0' represents False. Any other values (including text) will also be interpreted as True.\n")
            NewFileContents.append("#All the config in here needs to stay in this order, or it might not work properly.\n")
            NewFileContents.append("#Lines starting with a '#' are comments. Feel free to add comments where necessary.\n\n")
            NewFileContents.append("#Whether to start on boot.\n")
            NewFileContents.append("StartOnBoot = "+unicode(int(StartOnBoot))+"\n\n")

        if SetStartupUpdateCheck == False:
            NewFileContents.append("#Whether we should check for updates on startup.\n")
            NewFileContents.append("StartupUpdateCheck = "+unicode(int(StartupUpdateCheck))+"\n\n")

        if SetUseWineAutoscan == False:
            NewFileContents.append("#Whether to scan for software if autorun file parsing fails.\n")
            NewFileContents.append("UseWineAutoscan = "+unicode(int(UseWineAutoscan))+"\n\n")

        if SetPromptBeforeScanning == False:
            NewFileContents.append("#Whether to prompt before scanning a disk for software.\n")
            NewFileContents.append("PromptBeforeScanning = "+unicode(int(PromptBeforeScanning))+"\n\n")

        if SetDevicesToMonitor == False:
            NewFileContents.append("#List of space-seperated devices you wish to be monitored.\n")
            NewFileContents.append("DevicesToMonitor = "+' '.join(DevicesToMonitor)+"\n\n")

        #Write the finished lines to the file, using the helperscript.
        ConfigFile.close()
        subprocess.Popen(["pkexec", "/usr/share/wineautostart/helperscripts/saveconfig.py", ''.join(NewFileContents)]).wait()

        #Finally, exit, and tell MainClass to re-read the config.
        logger.info("SettingsWindow().SaveConfig(): Finished saving options. Closing Settings Window...")
        self.Destroy()

        wx.CallAfter(self.ParentWindow.ReadConfig, StartBackend=True, UpdateCheckNow=False)

#End Settings Window.
#Start Backend thread.
class BackendThread(threading.Thread):
    def __init__(self, ParentWindow):
        """Initialize and start the thread."""
        self.ParentWindow = ParentWindow
        threading.Thread.__init__(self)
        self.DevicesToIgnore = []
        self.RunningSoftwareDevice = None
        self.RunningSoftwareMountPoint = None
        self.start()

    def ShowMsgDlg(self,Message,Kind="info"):
        """Handle showing thread message dialogs, reducing code duplication and compilications and errors."""
        #Use this with: self.ShowMsgDlg(Kind=<kind>, Message=<message>)
        #Reset dlgClosed, avoiding errors.
        global dlgClosed
        dlgClosed = None

        wx.CallAfter(self.ParentWindow.ShowThreadMsgdlg, kind=Kind, msg=Message)

        #Trap the thread until the user responds.
        while dlgClosed == None:
            time.sleep(0.5)

    def ShowYesNoDlg(self,Message,Title="Wine Autostart - Question"):
        """Handle showing thread yes/no dialogs, reducing code duplication and compilications and errors."""
        #Use this with: self.ShowYesNoDlg(Message=<message>, Title = <title>)
        #Reset dlgResult, avoiding errors.
        global dlgResult
        dlgResult = None

        wx.CallAfter(self.ParentWindow.ShowThreadYesNodlg, msg=Message, title=Title)

        #Trap the thread until the user responds.
        while dlgResult == None:
            time.sleep(0.5)

        #Return dlgResult directly potentially avoiding problems.
        return dlgResult

    def ShowChoiceDlg(self,Message,Title,Choices):
        """Handle showing thread choice dialogs, reducing code duplication and compilications and errors."""
        #Use this with: self.ShowChoiceDlg(Message=<message>, Title=<title>, Choices=<choices>)
        while True:
            #Reset dlgResult, avoiding errors.
            global dlgResult
            dlgResult = None

            wx.CallAfter(self.ParentWindow.ShowThreadChoicedlg, msg=Message, title=Title, choices=Choices)

            #Trap the thread until the user responds.
            while dlgResult == None:
                time.sleep(0.5)

            #Stop the user from avoiding entering anything.
            if dlgResult in ["", "Clicked no..."]:
                self.ShowMsgDlg(Kind="warning", Message="Please select an appropriate option.")
            else:
                #Return dlgResult directly potentially avoiding problems.
                return dlgResult

    def ReadAutorunInfo(self, MountPoint):
        """Try to find an autorun file, and run the specified exe file."""
        AutorunFile = BackendTools().FindAutorunFile(MountPoint)

        #Check if we found one.
        if AutorunFile != None:
            #Now parse the autorun file to try and find an executable.
            logger.info("BackendThread().ReadAutorunInfo(): Found autorun file at: "+AutorunFile+". Parsing it...")
            AutorunExeFile = BackendTools().ParseAutorunFile(AutorunFile)

            #Check if we found one.
            if AutorunExeFile == None:
                #We haven't, so try Wine Autoscan instead.
                logger.info("BackendThread().ReadAutorunInfo(): No exe file specified in autorun info. Using Wine Autoscan...")

            elif os.path.isfile(MountPoint.replace("\\", "")+"/"+AutorunExeFile.replace("\\", "")):
                #We have! Ask the user if he/she wants to run this file.
                logger.info("BackendThread().ReadAutorunInfo(): Found helpful autorun information! Asking the user if he/she wants to run the specified file ("+MountPoint+"/"+AutorunExeFile+")...")
                Result = self.ShowYesNoDlg(Message="Wine Autostart has found the following Windows software on the CD/DVD you inserted: "+MountPoint+"/"+AutorunExeFile+". Do you want to run it?\n\nNote: If you click no, you will be prompted to use Wine Autoscan instead.")

                #Do what the user says.
                if Result == "No":
                    #Try to use Wine Autoscan instead.
                    logger.info("BackendThread().ReadAutorunInfo(): Not running the software as the user requested. Using Wine Autoscan...")

                else:
                    #Run the software.
                    logger.info("BackendThread().ReadAutorunInfo(): Running the software as the user requested...")

                    #Return the file so FindAndRunSoftware knows to run the file.
                    return MountPoint.replace("\\", "")+"/"+AutorunExeFile.replace("\\", "")

            else:
                #Bad autorun information, because it points at a file that doesn't exist, so try Wine Autoscan instead.
                logger.warning("BackendThread().ReadAutorunInfo(): Bad autorun information! It points to an executable file ("+MountPoint+"/"+AutorunExeFile+") that doesn't exist!")

        else:
            logger.info("BackendThread().ReadAutorunInfo(): No autorun information found. Using Wine Autoscan...")

    def WineAutoscan(self, MountPoint):
        """Try to scan for exe files, and return a user-chosen one to self.FindAndRunSoftware"""
        logger.info("BackendThread().WineAutoscan(): Scanning for exe files in "+MountPoint+"...")
        DeclinedInstallers = False
        ExeFiles = BackendTools().ScanForExeFiles(MountPoint)

        #See if there are any installers.
        Installers = []

        for File in ExeFiles:
            if "SETUP.EXE" in File.upper() or "INSTALL.EXE" in File.upper():
                Installers.append(File)

        if Installers != []:
            #Ask the user which installer to run.
            logger.info("BackendThread().WineAutoscan(): Found at least one installer! Asking the user which one to run...")
            Result = self.ShowChoiceDlg(Message="Please select which installer you'd like to run, or select 'None'.\n\nNote: If you select 'None', you will be asked if you want to run any other software on the disk.", Title="Wine Autostart - Select an Installer", Choices=["None"] + Installers)

            if Result != "None":
                logger.info("BackendThread().WineAutoscan(): User selected "+Result+". Running software...")
                return Result
            else:
                logger.info("BackendThread().WineAutoscan(): User declined the installers. Asking to run any other files instead...")
                DeclinedInstallers = True

        if Installers == [] or DeclinedInstallers:
            #See if there are any other exe files.
            if ExeFiles != []:
                #Ask the user which file to run.
                logger.info("BackendThread().WineAutoscan(): Found at least one exe file! Asking the user which one to run...")
                Result = self.ShowChoiceDlg(Message="Please select which exe file you'd like to run, or select 'None'\n\nNote: If you select 'None' the disk will be ignored until the media is ejected.", Title="Wine Autostart - Select a File", Choices=["None"] + ExeFiles)

                if Result != "None":
                    logger.info("BackendThread().WineAutoscan(): User selected "+Result+". Running software...")
                    return Result
                else:
                    logger.info("BackendThread().WineAutoscan(): User declined running any suggested software. Ignoring the disk...")

    def run(self):
        """Main body of the thread, started with self.start()"""
        global RunningSoftware
        RunningSoftware = False

        while RunningBackend:
            #Use a try statement to see if wineserver is running.
            try:
                subprocess.check_output(["pgrep", "wineserver"])

            except subprocess.CalledProcessError:
                #If it isn't, start the main part of the loop.
                #Check if we just finished running software.
                if RunningSoftware:
                    #If so, ignore the disk that houses the software that was just being run until it is ejected.
                    self.DevicesToIgnore.append(self.RunningSoftwareDevice)
                    self.DevicesToIgnore.append(self.RunningSoftwareMountPoint)

                wx.CallAfter(self.ParentWindow.SetStatus, "Checking for disk...")
                RunningSoftware = self.FindAndRunSoftware()

                #If WINE is starting, wait 30 seconds before checking again because the startup procedure is slow.
                if RunningSoftware:
                    #Notify the user.
                    subprocess.call("notify-send 'Wine Autostart' 'Wine Autostart is preparing to run software, please wait for up to 30 seconds...' -i /usr/share/pixmaps/wineautostart.png", shell=True)
                    wx.CallAfter(self.ParentWindow.SetStatus, "Running software...")

                    #Wineserver starts in much  less than 10 seconds, so give it plenty of time, but also allow upating the status quickly in case the app crashed, and we start looking for disks again.
                    time.sleep(10)

                else:
                    #Check again.
                    time.sleep(1)

            #If wineserver is running, wait for it (and any software) to finish before doing anything else. 
            else:
                wx.CallAfter(self.ParentWindow.SetStatus, "Running software...")
                time.sleep(10)

        #Change the status message, if the program isn't shutting down.
        if Exiting == False:
            wx.CallAfter(self.ParentWindow.SetStatus, "Stopped.")

    def FindAndRunSoftware(self):
        """Try to find and run Windows software"""
        #Check for disks in each drive we're monitoring and not currently ignoring.
        for Dev in DevicesToMonitor:
            #Look for mounted media in each drive.
            MountPoint = BackendTools().GetDiskMountPoint(Dev)

            if Dev in self.DevicesToIgnore:
                #Check if we still need to ignore this drive, or whether the media has changed (or been ejected).
                IgnoredMountPoint = self.DevicesToIgnore[self.DevicesToIgnore.index(Dev)+1]

                if MountPoint != IgnoredMountPoint:
                    #Remove it from the list of devices to ignore.
                    logger.debug("BackendThread().FindAndRunSoftware(): Stopped ignoring "+Dev+", as media has changed or is no longer present...")
                    self.DevicesToIgnore.pop(self.DevicesToIgnore.index(Dev))
                    self.DevicesToIgnore.pop(self.DevicesToIgnore.index(IgnoredMountPoint))
                    MountPoint = None

                else:
                    #Avoid an UnboundLocalError.
                    MountPoint = None
                
            if MountPoint != None:
                #Found media!
                logger.info("BackendThread().FindAndRunSoftware(): Found media in "+Dev+"! Media is mounted at: "+MountPoint+"...")
                Device = Dev

                #If set this way, ask the user if he/she wants Wine Autostart to look for software on this disk. Otherwise continue without confirmation.
                if PromptBeforeScanning:
                    logger.info("BackendThread().FindAndRunSoftware(): Asking the user if we're going to look for software in "+Device+"...")
                    Result = self.ShowYesNoDlg(Message="Wine Autostart has detected a disk in the drive "+Device+". Do you want Wine Autostart to look for Windows software on it?\n\nNote: If you click no, the drive will also be ignored by Wine Autostart until the media is ejected.")

                else:
                    Result = "Yes"

                #Do what the user says.
                if Result == "No":
                    #Ignore the drive.
                    logger.info("BackendThread().FindAndRunSoftware(): Ignoring the drive as the user requested...")
                    self.DevicesToIgnore.append(Device)
                    self.DevicesToIgnore.append(MountPoint)
                    MountPoint = None

                else:
                    break

        #Check if we found any media, and return False if we didn't, stopping the function.
        if MountPoint == None:
            logger.info("BackendThread().FindAndRunSoftware(): No media found in any of our devices to monitor that we aren't ignoring. Waiting for media...")
            return False

        #Look for software.
        logger.info("BackendThread().FindAndRunSoftware(): Looking for software as the user requested...")
        ExeFile = self.ReadAutorunInfo(MountPoint)

        #Check if an exe file was found.
        if ExeFile != None:
            #Run it, and allow the disk to be ignored when the software has closed.
            subprocess.Popen("wine start /Unix '"+ExeFile+"'", shell=True)
            self.RunningSoftwareDevice = Device
            self.RunningSoftwareMountPoint = MountPoint
            return True

        #Check if Wine Autoscan is enabled.
        if UseWineAutoscan == False:
            logger.info("BackendThread().FindAndRunSoftware(): Wine Autoscan is disabled. Ignoring disk and notifying user...")
            self.ShowMsgDlg(Message="No helpful autorun information was found on "+Device+", and Wine Autoscan is disabled in the settings window, so this drive will now be ignored until the media is ejected.")

        else:
            logger.info("BackendThread().FindAndRunSoftware(): Asking the user if we're going to use Wine Autoscan...")
            Result = self.ShowYesNoDlg(Message="Wine Autostart couldn't find any software on "+Device+" from autorun information. Do you want Wine Autostart to scan for Windows software instead?\n\nNote: If you click no, the drive will also be ignored by Wine Autostart until the media is ejected.")

            if Result == "Yes":
                #Try to scan for exe files.
                logger.info("BackendThread().FindAndRunSoftware(): We are using Wine Autoscan. Continuing...")
                ExeFile = self.WineAutoscan(MountPoint)

                #Check if an exe file was found.
                if ExeFile != None:
                    #Run it, and allow the disk to be ignored when the software has closed.
                    subprocess.Popen("wine start /Unix '"+ExeFile+"'", shell=True)
                    self.RunningSoftwareDevice = Device
                    self.RunningSoftwareMountPoint = MountPoint
                    return True

        #If we get here, software isn't being run, so ignore the disk and return False.
        logger.info("BackendThread().FindAndRunSoftware(): We didn't find any software to run. Ignoring the device until media changes...")
        self.ShowMsgDlg(Message="Wine Autostart coudn't find any windows software to run on "+Device+", so this drive will now be ignored until the media is ejected.")
        self.DevicesToIgnore.append(Device)
        self.DevicesToIgnore.append(MountPoint)

        return False
                    
#End Backend thread.
app = WineAutostart(False)
app.MainLoop()
