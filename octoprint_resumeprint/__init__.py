# coding=utf-8
from __future__ import absolute_import

# from tkinter.tix import Tree

import octoprint.plugin
from octoprint.filemanager import FileDestinations
from octoprint.access.permissions import Permissions
from octoprint.events import Events
import os
from flask import jsonify
import octoprint.settings
import octoprint.filemanager
import threading
import time
import re


class ResumeprintPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.EventHandlerPlugin,
):
    _recovery_file = ""
    recovery_data = []

    def __init__(self):
        # self._fileManager = octoprint.filemanager.FileManager
        self._recovery_file = os.path.join(
            octoprint.settings.settings().getBaseFolder("data"),
            "print_recovery_data.yaml",
        )

    def file_thread(self, origin, path, pos):
        self._logger.info("Thread")
        self._logger.info(self.recovery_data)

        disallowed = [
            "G0 ",
            "G1 ",
            "G2 ",
            "G3 ",
            "G4 ",
            "G29",
            "M117",
            "M300",
            "M600",
            "M6001",
            "@OCTOLAPSE",
        ]
        moves = ["G0 ", "G1 ", "G2 ", "G3 ", "G4 "]
        good_moves = ["G0 ", "G1 "]
        lastFANLine = ""
        lastZLine = ""
        lastFRLine = ""

        if origin != "local":
            self._logger.info("Origin != local => {}".format(origin))
            return

        gcode_filename = self._file_manager.path_on_disk("local", path)
        self._logger.info("gcode_filename: {}".format(gcode_filename))
        curr_pos = 0
        good_pos = 0
        lineNum = 0
        breakLoop = False

        with open(
            gcode_filename, encoding="utf-8-sig", errors="replace", newline=""
        ) as gcode_file:
            self._logger.info("gcode file opened")
            # for line in gcode_file:
            while True:
                if breakLoop:
                    break

                lineNum += 1
                line = gcode_file.readline()
                if not line:
                    breakLoop = True
                    break

                tmplen = len(line.encode("utf-8"))
                curr_pos += tmplen

                # self._logger.info("line[{}]@{}|{}: >{}<".format(lineNum, tmplen, curr_pos, line))

                if curr_pos >= pos:
                    breakLoop = True

                if len(line) < 2:
                    continue

                if line.startswith(";"):
                    continue

                skip = False
                for d in disallowed:
                    if line.startswith(d):
                        skip = True
                        break

                if skip:
                    for d in moves:
                        if line.startswith(d):
                            if " Z" in line:
                                line = re.sub(";.+", "", line)
                                line = re.sub(" [^ZF]\-?[0-9\.]+", "", line)
                                lastZLine = line
                                break
                            if " F" in line:
                                line = re.sub(";.+", "", line)
                                line = re.sub(" [^F]\-?[0-9\.]+", "", line)
                                lastFRLine = line
                                break
                    for d in good_moves:
                        if line.startswith(d):
                            good_pos = curr_pos - tmplen
                else:
                    if line.startswith("M106") or line.startswith("M107"):
                        lastFANLine = line
                        skip = True

                if skip:
                    continue

                if len(line) <= 2:
                    continue

                self._logger.info("line[{}]@{}: {}".format(lineNum, curr_pos, line))
                self._printer.commands("{}".format(line))

        if len(lastFANLine):
            self._logger.info("lastFANLine: {}".format(lastFANLine))
            self._printer.commands("{}".format(lastFANLine))

        if len(lastFRLine):
            self._logger.info("lastFRLine: {}".format(lastFRLine))
            self._printer.commands("{}".format(lastFRLine))

        if len(lastZLine):
            self._logger.info("lastZLine: {}".format(lastZLine))
            self._printer.commands("{}".format(lastZLine))

        # self._printer.commands("M117 {}".format(message))
        self._logger.info(
            "Thread finished. Starting print of file {} at pos {}, curr_pos {}, good_pos {}".format(
                gcode_filename, pos, curr_pos, good_pos
            )
        )

        # self._printer.select_file(path, False, printAfterSelect = True, user=None, pos=curr_pos)
        self._printer.select_file(path, False, printAfterSelect=False)
        self._printer.start_print(pos=curr_pos)

    def is_file_available(self):
        return os.path.isfile(self._recovery_file)

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return {
            # put your plugin's default settings here
        }

    ##~~ AssetPlugin mixin

    def get_api_commands(self):
        return dict(resume=[])

    def on_api_command(self, command, data):
        if command == "resume":
            self._logger.info("resume print called")

            try:
                if self.is_file_available():
                    self._logger.info("File is available")
                else:
                    self._logger.info("File is not available")
                    return "Recovery file not available"

                recovery_data = self._file_manager.get_recovery_data()
                self._logger.info(recovery_data)
                if recovery_data:
                    # clean up recovery data if we just selected a different file
                    actual_origin = recovery_data.get("origin", None)
                    actual_path = recovery_data.get("path", None)
                    pos = recovery_data.get("pos", None)

                    self._logger.info("origin: {}".format(actual_origin))
                    self._logger.info("path: {}".format(actual_path))
                    self._logger.info("pos: {}".format(pos))
                    self.recovery_data = recovery_data

                    thread = threading.Thread(
                        target=self.file_thread,
                        args=(actual_origin, actual_path, pos),
                    )
                    thread.daemon = False
                    thread.start()

                    return jsonify(
                        dict(
                            msg="Resume printing of file {} @ pos {}".format(
                                actual_path, pos
                            )
                        )
                    )
            except Exception:
                # anything goes wrong with the recovery data, we ignore it
                self._logger.exception(
                    "Something was wrong with processing the recovery data"
                )

        self._logger.info("TESTING command: {}".format(command))

    def on_api_get(self, request):
        return jsonify(wrong="method")

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/resumeprint.js"],
            # "css": ["css/resumeprint.css"],
            # "less": ["less/resumeprint.less"],
        }

    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "resumeprint": {
                "displayName": "Resumeprint Plugin",
                "displayVersion": self._plugin_version,
                # version check: github repository
                "type": "github_release",
                "user": "Pavulon87",
                "repo": "OctoPrint-ResumePrint",
                "current": self._plugin_version,
                # update method: pip
                "pip": "https://github.com/Pavulon87/OctoPrint-ResumePrint/archive/{target_version}.zip",
            }
        }


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Resumeprint Plugin"


# Set the Python version your plugin is compatible with below. Recommended is Python 3 only for all new plugins.
# OctoPrint 1.4.0 - 1.7.x run under both Python 3 and the end-of-life Python 2.
# OctoPrint 1.8.0 onwards only supports Python 3.
__plugin_pythoncompat__ = ">=3,<4"  # Only Python 3


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = ResumeprintPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
