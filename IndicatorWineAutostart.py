#!/usr/bin/python
# -*- coding: utf-8 -*- 
# Indicator for Wine Autostart Version 2.0.1
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

#Import modules.
import appindicator
import gtk
import sys
import threading

#Define version here.
Version = "2.0.1"

#Begin Main Process IPC Thread.
class MainProcessIPCThread(threading.Thread):
    """Thread to receive messages from the Main Process (WineAutostart.py), so we don't block the Indicator thread"""
    def __init__(self, Parent):
        """Initialize and start the thread."""
        self.Parent = Parent
        threading.Thread.__init__(self)
        self.start()

    def run(self):
        """Main body of the thread, started with self.start()"""
        while True:
            try:
                #Wait for a line.
                Line = sys.stdin.readline().replace("\n", "")

                #Notify the main process that we received the line, so it can be logged.
                if Line != "Quit":
                    print("Received message: "+Line)
                    sys.stdout.flush()

                #Process the line.
                #React to it, if it's commanding us to do anything.
                if "Status:" in Line:
                    self.Parent.SetStatus(Line)

                elif Line == "EnableStartItem":
                    gtk.Widget.set_sensitive(self.Parent.StartItem, True)

                elif Line == "DisableStartItem":
                    gtk.Widget.set_sensitive(self.Parent.StartItem, False)

                elif Line == "EnableStopItem":
                    gtk.Widget.set_sensitive(self.Parent.StopItem, True)

                elif Line == "DisableStopItem":
                    gtk.Widget.set_sensitive(self.Parent.StopItem, False)

                elif Line == "Quit":
                    sys.exit()

            except (AttributeError, IndexError, NameError) as Error:
                #Return the error to the main process, so it can be logged.
                print("Error occurred! Error: "+unicode(Error))

#End Main Process IPC Thread.
#Begin Indicator class.
class Indicator:
    """Indicator for Wine Autostart v"""+Version+""". It is started by WineAutostart.py, and communicates through stdout and stdin.""" 
    def __init__(self):
        """Set up Wine Autostart """+Version+"""'s indicator"""
        #Create the actual indicator.
        self.AppIndicator = appindicator.Indicator("Wine Autostart v"+Version, "wineautostart", appindicator.CATEGORY_APPLICATION_STATUS)
        self.AppIndicator.set_status(appindicator.STATUS_ACTIVE)
        self.AppIndicator.set_attention_icon("wineautostart")

        #Run the setup methods.
        self.CreateMenus()
        self.BindEvents()

        #Start the IPC thread.
        MainProcessIPCThread(self)

        #Enter GTK's main loop, and prepare for threading.
        gtk.gdk.threads_init()
        gtk.main()

    def CreateMenus(self):
        """Create all menus for Indicator"""
        self.MainMenu = gtk.Menu()
        self.ControlsMenu = gtk.Menu()
        self.UpdatesMenu = gtk.Menu()

        #Create the items for the main menu.
        self.VersionandNameItem = gtk.MenuItem("Wine Autostart v"+Version)
        self.Separator1 = gtk.SeparatorMenuItem()
        self.StatusItem = gtk.MenuItem("Status: Please wait...")
        self.Separator2 = gtk.SeparatorMenuItem()
        self.SettingsItem = gtk.MenuItem("Settings")
        self.UpdatesMenuItem = gtk.MenuItem("Updates")
        self.ControlsMenuItem = gtk.MenuItem("Controls")
        self.Separator3 = gtk.SeparatorMenuItem()
        self.AboutItem = gtk.MenuItem("About")
        self.Separator4 = gtk.SeparatorMenuItem()
        self.QuitItem = gtk.MenuItem("Quit")

        #Create the items for the updates menu.
        self.UpdateCheckItem = gtk.MenuItem("Check For Updates")
        self.PrivacyPolicyItem = gtk.MenuItem("Privacy Policy")

        #Create the items for the controls menu.
        self.StartItem = gtk.MenuItem("Start")
        self.StopItem = gtk.MenuItem("Stop")

        #Add the items to the main menu.
        self.MainMenu.append(self.VersionandNameItem)
        self.MainMenu.append(self.Separator1)
        self.MainMenu.append(self.StatusItem)
        self.MainMenu.append(self.Separator2)
        self.MainMenu.append(self.SettingsItem)
        self.MainMenu.append(self.UpdatesMenuItem)
        self.MainMenu.append(self.ControlsMenuItem)
        self.MainMenu.append(self.Separator3)
        self.MainMenu.append(self.AboutItem)
        self.MainMenu.append(self.Separator4)
        self.MainMenu.append(self.QuitItem)

        #Add the items to the updates menu.
        self.UpdatesMenu.append(self.UpdateCheckItem)
        self.UpdatesMenu.append(self.PrivacyPolicyItem)
        self.UpdatesMenuItem.set_submenu(self.UpdatesMenu)

        #Add the items to the controls menu.
        self.ControlsMenu.append(self.StartItem)
        self.ControlsMenu.append(self.StopItem)
        self.ControlsMenuItem.set_submenu(self.ControlsMenu)

        #Show the items
        self.VersionandNameItem.show()
        self.Separator1.show()
        self.StatusItem.show()
        self.Separator2.show()
        self.SettingsItem.show()
        self.UpdatesMenuItem.show()
        self.UpdateCheckItem.show()
        self.PrivacyPolicyItem.show()
        self.ControlsMenuItem.show()
        self.StartItem.show()
        self.StopItem.show()
        self.Separator3.show()
        self.AboutItem.show()
        self.Separator4.show()
        self.QuitItem.show()

        #Set MainMenu as the menu for the appindicator.
        self.AppIndicator.set_menu(self.MainMenu)

    def BindEvents(self):
        """Bind all events for Indicator"""
        self.SettingsItem.connect("activate", self.SendMessage, "ShowSettings")
        self.UpdateCheckItem.connect("activate", self.SendMessage, "UpdateCheck")
        self.PrivacyPolicyItem.connect("activate", self.SendMessage, "ShowPrivacyPolicy")
        self.StartItem.connect("activate", self.SendMessage, "Start")
        self.StopItem.connect("activate", self.SendMessage, "Stop")
        self.AboutItem.connect("activate", self.SendMessage, "ShowAbout")
        self.QuitItem.connect("activate", self.SendMessage, "Quit")

    def SendMessage(self, Event=None, Message=""):
        """Writes the contents of Message to stdout"""
        print(Message)
        sys.stdout.flush()

    def SetStatus(self, Status):
        """Updates the status menu item with the new status"""
        self.StatusItem.set_label(Status)

#End Indicator class.
Indicator()
