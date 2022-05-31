Wine Autostart (2.0.2):

  * Fix a bug in the autorun.inf parser.
  * Use wx.TextCtrl.LoadFile() where possible.
  * Always call panels self.Panel.
  * Don't use the name "Wine Autoscan" in the GUI because it sounds like a different product.
  * Make sure dialogue boxes and windows are on top and visible to the user.
  * Use os.walk() instead of find for searching CDs.
  * Fix exporting config on first run.
  * Pull in new GetDevInfo package from WxFixBoot.
  * Save config for each user (in home dir) for greater customisation.
  * Save StartOnBoot settings for each user as well.
  * Put Python version into logfile on startup.

Wine Autostart (2.0.1);

  * Changes since 2.0:
  * Fix a bug that very occasionally causes the backend to start two or more times,
    and display the same dialogs to the user more than once.

Wine Autostart (2.0);

Changes since 1.0:

  * Begin rewriting in wxpython.
  * Semi-finish indicator menus.
  * Finish aboutbox.
  * Allow quitting via the menu item.
  * Add logging and support for cmdline options.
  * Setup config file reading.
  * Get a basic update check working.
  * Create the privacy policy box and some test text (because of new update feature).
  * Use a sizer with the privacy policy box.
  * Create the update settings box.
  * Add more configuration entries in the config file.
  * Make the update settings window save settings (to memory) when closed.
  * Make the update settings window populate itself with settings when opened.
  * Devise a smarter, more helpful method of gathering and displaying device information.
  * Optimize the new device info detection method for speed and efficency.
  * Future-proof, preparing for future support for python 3.
  * Create the new settings window.
  * Remove the periodic auto-update feature, as I've decided it's pointless.
  * Remove the update settings window, as it's not needed without the above feature.
  * Make the revert button work in SettingsWindow().
  * Use docstrings for functions, rather than comments at the start of each function.
  * Get the update check feature working.
  * Fix the indicator problems (unreliable, doesn't work at all in Unity) by using pyGTK and libappindicator to power the indicator, and using IPC (Inter-Process Communication) with wxPython, which powers the rest of the GUI.
  * Write the privacy policy.
  * Port the new device detection system from DDRescue-GUI 1.4 (active development).
  * Integrate the new device detection system with Wine Autostart.
  * Enable exporting Wine Autostart's configuration to a user-specified file.
  * Fully integrate the icon into the GUI.
  * Remove the log file when closing.
  * Enable importing config.
  * Enable exporting config.
  * Enable option for starting on boot.
  * Enable ignoring drives until they're ejected.
  * Implement the main part of the backend.
  * Get start on boot working.
  * Implement scanning support (Wine Autoscan).
  * Fix wx.PyDeadObject error when exiting.
  * Do startup update check if needed.
  * Get creating the config file working if needed.
  * Prepare for stable release.
  * Release 2.0~rc1
  * Add support for mountpoints with spaces.
  * Fix a UI bug with the throbber (wxPython > 2.8.12.1, only affects 2.0~rc1, not 1.0).
  * Move the privacy policy text into the "other" subdirectory in /usr/share/wineautostart.

Wine Autostart (1.0):

  * New Indicator.
  * Rewritten in Python for increased efficency.
  * Faster.
  * Lots of bugs fixed.
  * Can now ignore disks, rather than wait for 10 minutes.
  * Uses virtually no CPU power and RAM.
  * Removed wineautoscan as it is no longer useful.

Wine Autostart (0.9):

  * More comments added to code.
  * Use unset, not (var)="".
  * Use sed, not tr.
  * Use custom gksudo messages.
  * Created wineautostarterror to handle errors.
  * Stop creating files in /tmp.
  * Use "wine start /Unix (path)", not "wine (path)". This fixes various uninteresting problems with wine crashing. (Thanks Daniel Curtis)
  * Use "grep .exe" instead of "grep open=", and use more intelligent sed commands to get the correct exe file.

Wine Autostart (0.8.5):

  * Eject functionality now works properly and as expected.
  * Now works with disks with spaced mount points
  * Refactored and optimised code.
  * Updated information in About_wineautostart.

Wine Autostart (0.8):

  * General bugfixes and simplifications to the code.
  * Modifications to the indicator's menu and improved reliability.
  * Include wine as a package dependency.
  * Include a more helpful and much shorter package description.

Wine Autostart (0.7):

  * Initial release.
  * Added readme to source package.
