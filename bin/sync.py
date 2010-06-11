#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ============================================================================
#  Name        : sync.py
#  Part of     : Hb
#  Description : Hb themes sync script
#  Version     : %version: %
#
#  Copyright (c) 2008-2010 Nokia.  All rights reserved.
#  This material, including documentation and any related computer
#  programs, is protected by copyright controlled by Nokia.  All
#  rights are reserved.  Copying, including reproducing, storing,
#  adapting or translating, any or all of this material requires the
#  prior written consent of Nokia.  This material also contains
#  confidential information which may not be disclosed to others
#  without the prior written consent of Nokia.
# ============================================================================

import os
import re
import sys
import time
import copy
import shutil
import fnmatch
import zipfile
import optparse
import tempfile
import posixpath
if sys.version_info[0] == 2 and sys.version_info[1] < 4:
    # for scratchbox compatibility
    import popen2
else:
    import subprocess

# ============================================================================
# Globals
# ============================================================================
VERBOSE = False
ARCHIVES = False
INCLUDE = None
EXCLUDE = None
INPUT_DIR = os.getcwd()
OUTPUT_DIR = os.getcwd()
IBY_SOURCE_PREFIX = "ZRESOURCE/hb/themes"
IBY_TARGET_PREFIX = "RESOURCE_FILES_DIR/hb/themes"
BLD_HW_TARGET_PREFIX = "/epoc32/data/z/resource/hb/themes"
BLD_EMU_TARGET_PREFIX = "/epoc32/winscw/c/resource/hb/themes"
BLD_TARGET_PREFIXES = []
SYMBIAN = False
EXIT_STATUS = 0
NAME = "themes"
THEME_COMMON = "themecommon"
THEME_SETTINGS_FILE = "theme.theme"
ENCODER = "SVGTBinEncode.exe"
NVG = True

# ============================================================================
# OptionParser
# ============================================================================
class OptionParser(optparse.OptionParser):
    def __init__(self):
        optparse.OptionParser.__init__(self)
        self.add_option("-v", "--verbose", action="store_true", dest="verbose",
                        help="print verbose information about each step of the sync process")
        self.add_option("-q", "--quiet", action="store_false", dest="verbose",
                        help="do not print information about each step of the sync process")
        self.add_option("-n", "--name", dest="name", metavar="name",
                        help="specify the package <name> (default %s)" % NAME)
        self.add_option("--symbian", action="store_true", dest="symbian",
                        help="work in Symbian mode")
        self.add_option("--nvg", action="store_true", dest="nvg",
                        help="do convert svg to nvg")
        self.add_option("--no-nvg", action="store_false", dest="nvg",
                        help="do not convert svg to nvg")

        group = optparse.OptionGroup(self, "Input/output options")
        self.add_option("-i", "--input", dest="input", metavar="dir",
                        help="specify the input <dir> (default %s)" % INPUT_DIR)
        self.add_option("-o", "--output", dest="output", metavar="dir",
                        help="specify the output <dir> (default %s)" % OUTPUT_DIR)
        self.add_option("-a", "--archives", action="store_true", dest="archives",
                        help="export/install archives (default %s)" % ARCHIVES)
        self.add_option("--include", dest="include", action="append", metavar="pattern",
                        help="specify the include <pattern> (default %s)" % INCLUDE)
        self.add_option("--exclude", dest="exclude", action="append", metavar="pattern",
                        help="specify the exclude <pattern> (default %s)" % EXCLUDE)
        self.add_option_group(group)

        group = optparse.OptionGroup(self, "Prefix options")
        self.add_option("--iby-source-prefix", dest="ibysourceprefix", metavar="prefix",
                        help="specify the iby source <prefix> (default %s)" % IBY_SOURCE_PREFIX)
        self.add_option("--iby-target-prefix", dest="ibytargetprefix", metavar="prefix",
                        help="specify the iby target <prefix> (default %s)" % IBY_TARGET_PREFIX)
        self.add_option("--bld-hw-target-prefix", dest="bldhwtargetprefix", metavar="prefix",
                        help="specify the bld harware target <prefix> (default %s)" % BLD_HW_TARGET_PREFIX)
        self.add_option("--bld-emu-target-prefix", dest="bldemutargetprefix", metavar="prefix",
                        help="specify the bld emulator target <prefix> (default %s)" % BLD_EMU_TARGET_PREFIX)
        self.add_option("--bld-target-prefix", dest="bldtargetprefixes", action="append", metavar="prefix",
                        help="specify an additional bld target <prefix>")
        self.add_option_group(group)

# ============================================================================
# Utils
# ============================================================================
if not hasattr(os.path, "relpath"):
    def relpath(path, start=os.curdir):
        abspath = os.path.abspath(path)
        absstart = os.path.abspath(start)
        if abspath == absstart:
            return "."
        i = len(absstart)
        if not absstart.endswith(os.path.sep):
            i += len(os.path.sep)
        if not abspath.startswith(absstart):
            i = 0
        return abspath[i:]
    os.path.relpath = relpath

def run_process(command, cwd=None):
    code = 0
    output = ""
    try:
        if cwd != None:
            oldcwd = os.getcwd()
            os.chdir(cwd)
        if sys.version_info[0] == 2 and sys.version_info[1] < 4:
            process = popen2.Popen4(command)
            code = process.wait()
            output = process.fromchild.read()
        else:
            process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            (stdout, stderr) = process.communicate()
            code = process.returncode
            output = stdout + stderr
        if cwd != None:
            os.chdir(oldcwd)
    except Exception, e:
        print(e)
        code = -1
    return [code, output]

def make_target(path):
    # generate a compatible make target name from path
    target = os.path.splitdrive(path)[1].strip("\\/")
    return "_".join(re.split("[\\\/]+", target))

def zip_filelist(filepath):
    files = list()
    archive = zipfile.ZipFile(filepath)
    for entry in archive.namelist():
        if not entry.endswith("/"):
            files.append(entry)
    return files

class Theme:
    def __init__(self, name):
        self.name = name
        self.paths = []
        self.files = {}
        self.archives = {}

    def initialize(self):
        for path in self.paths:
            for root, dirs, files in os.walk(path):
                for file in files:
                    filepath = posixpath.join(root, file).replace("\\", "/")
                    if self._include(filepath):
                        extension = os.path.splitext(filepath)[1]
                        if extension == ".zip":
                            if root not in self.archives:
                                self.archives[root] = list()
                            self.archives[root].append(filepath)
                        else:
                            if root not in self.files:
                                self.files[root] = list()
                            self.files[root].append(filepath)

    def _write_zip_entry(self, archive, filepath):
        path, filename = os.path.split(filepath)
        oldcwd = os.getcwd()
        os.chdir(path)
        archive.write(filename)
        os.chdir(oldcwd)

    def encode(self):
        print "Encoding: %s" % self.name
        for path, archives in self.archives.iteritems():
            relpath = os.path.relpath(path, INPUT_DIR)
            if not relpath.startswith("icons"):
                continue
            for archive in archives:
                # ensure that output dir exists
                outpath = os.path.join(OUTPUT_DIR, relpath)
                if not os.path.exists(outpath):
                    os.makedirs(outpath)

                # extract to a temp dir
                tempdir = tempfile.mkdtemp()
                zip = zipfile.ZipFile(archive)
                for name in zip.namelist():
                    file = open(os.path.join(tempdir, name),'w')
                    file.write(zip.read(name))
                    file.close()

                # convert & re-archive
                total = 0
                converted = 0
                tmpfile, tmpfilepath = tempfile.mkstemp(".zip")
                tmparchive = zipfile.ZipFile(tmpfilepath, 'w')
                for root, dirs, files in os.walk(tempdir):
                    for file in files:
                        filepath = os.path.join(root, file)
                        basepath, extension = os.path.splitext(filepath)
                        if extension == ".svg":
                            total += 1
                            encoder = ENCODER
                            if os.path.exists("/ext/tools/hbbins/bin/3rdparty/%s" % ENCODER):
                                encoder = "/ext/tools/hbbins/bin/3rdparty/%s" % ENCODER
                            res = run_process([encoder, "-v", "6", filepath, "-e", ".nvg"])[0]
                            exists = os.path.exists(basepath + ".nvg")
                            if not exists:
                                self._write_zip_entry(tmparchive, filepath)
                            else:
                                converted += 1
                                self._write_zip_entry(tmparchive, basepath + ".nvg")
       
                # cleanup
                tmparchive.close()
                os.close(tmpfile)
                if converted > 0:
                    shutil.move(tmpfilepath, os.path.join(outpath, os.path.basename(archive)))
                else:
                    os.remove(tmpfilepath)
                shutil.rmtree(tempdir, True)
                print "          %s (%s/%s)" % (os.path.join(relpath, os.path.basename(archive)), converted, total)

    def write_css(self, csspath):
        outpath = os.path.dirname(csspath)
        if not os.path.exists(outpath):
            os.makedirs(outpath)
        groupfile = open(csspath, "w")
        for path, files in copy.deepcopy(self.files.items()):
            for filepath in files:
                basename = os.path.basename(filepath)
                extension = os.path.splitext(basename)[1]
                if extension == ".css":
                    if basename != os.path.basename(csspath):
                        cssfile = open(filepath, "r")
                        groupfile.write(cssfile.read())
                        cssfile.close()
                    self.files[path].remove(filepath)
        groupfile.close()
        if outpath not in self.files:
            self.files[outpath] = list()
        if csspath not in self.files[outpath]:
            self.files[outpath].append(csspath)

    def write_iby(self, ibypath):
        global IBY_SOURCE_PREFIX, IBY_TARGET_PREFIX, EXIT_STATUS
        outpath = os.path.dirname(ibypath)
        if not os.path.exists(outpath):
            os.makedirs(outpath)
        out = open(ibypath, "w")
        out.write("#ifndef __%s_IBY__\n" % self.name.upper())
        out.write("#define __%s_IBY__\n" % self.name.upper())
        out.write("\n")
        out.write("#include <bldvariant.hrh>\n")
        out.write("\n")
        out.write("data=%s/%s.themeindex\t%s/%s.themeindex\n" % (IBY_SOURCE_PREFIX, self.name, IBY_TARGET_PREFIX, self.name))
        written_entries = list()
        for path, files in self.files.iteritems():
            relpath = os.path.relpath(path, INPUT_DIR).replace("\\", "/")
            for filepath in files:
                filename = os.path.basename(filepath)
                entry = posixpath.join(relpath, filename)
                if entry not in written_entries:
                    written_entries.append(filepath)
                    out.write("data=%s/%s\t%s/%s\n" % (IBY_SOURCE_PREFIX, entry, IBY_TARGET_PREFIX, entry))
                else:
                    print "ERROR: %s duplicate entry %s" % (ibypath, entry)
                    EXIT_STATUS = -1
        for path, archives in self.archives.iteritems():
            relpath = os.path.relpath(path, INPUT_DIR).replace("\\", "/")
            for archive in archives:
                files = zip_filelist(archive)
                for filepath in files:
                    entry = posixpath.join(relpath, filepath)
                    if entry not in written_entries:
                        written_entries.append(entry)
                        out.write("data=%s/%s\t%s/%s\n" % (IBY_SOURCE_PREFIX, entry, IBY_TARGET_PREFIX, entry))
                    else:
                        print "ERROR: %s duplicate entry %s" % (ibypath, entry)
                        EXIT_STATUS = -1
        out.write("\n")
        out.write("#endif __%s_IBY__\n" % self.name.upper())
        out.close()

    def _include(self, filepath):
        result = True
        if INCLUDE != None:
            for pattern in INCLUDE:
                if not fnmatch.fnmatch(filepath, pattern):
                    result = False
        if EXCLUDE != None:
            for pattern in EXCLUDE:
                if fnmatch.fnmatch(filepath, pattern):
                    result = False
        return result

def lookup_themes(path):
    themes = {}
    # base: effects, icons...
    for base in os.listdir(path):
        basepath = posixpath.join(path, base)
        if os.path.isdir(basepath):
            # theme: footheme, bartheme...
            for theme in os.listdir(basepath):
                themepath = posixpath.join(basepath, theme)
                if os.path.isdir(themepath):
                    if theme not in themes:
                        themes[theme] = Theme(theme)
                    themes[theme].paths.append(themepath)
    return themes

def write_txt(filepath, themes, prefixes):
    outpath = os.path.dirname(filepath)
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    out = open(filepath, "w")
    for name, theme in themes.iteritems():
        for prefix in prefixes:
            out.write("%s %s %s\n" % (name, prefix, prefix))
    out.close()

def write_pri(filepath, themes, prefixes, settingsfile_exists):
    outpath = os.path.dirname(filepath)
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    outpath = os.path.splitdrive(OUTPUT_DIR)[1]
    out = open(filepath, "w")

    # clean & dist clean rules
    out.write("QMAKE_CLEAN += %s\n" % filepath)
    out.write("QMAKE_CLEAN += %s\n" % (os.path.splitext(filepath)[0] + ".txt"))
    if settingsfile_exists:
        out.write("QMAKE_CLEAN += %s.iby\n" % posixpath.join(outpath, THEME_COMMON))
    for name, theme in themes.iteritems():
        out.write("QMAKE_CLEAN += %s.iby\n" % posixpath.join(outpath, name))
        for prefix in prefixes:
            out.write("QMAKE_CLEAN += %s.themeindex\n" % posixpath.join(prefix, name))

    out.write("symbian {\n")
    out.write("\tBLD_INF_RULES.prj_exports += \"$${LITERAL_HASH}include <platform_paths.hrh>\"\n")

    if settingsfile_exists:
        # exporting theme settings file
        settingsPath = os.path.splitdrive(posixpath.join(INPUT_DIR,THEME_SETTINGS_FILE))[1]
        out.write("\tBLD_INF_RULES.prj_exports += \"%s\t%s/%s\"\n" % (settingsPath, BLD_HW_TARGET_PREFIX, THEME_SETTINGS_FILE))
        out.write("\tBLD_INF_RULES.prj_exports += \"%s\t%s/%s\"\n" % (settingsPath, BLD_EMU_TARGET_PREFIX, THEME_SETTINGS_FILE))
        out.write("\tBLD_INF_RULES.prj_exports += \"%s.iby\tCORE_MW_LAYER_IBY_EXPORT_PATH(%s.iby)\"\n" % (posixpath.join(outpath, THEME_COMMON), THEME_COMMON))

    for name, theme in themes.iteritems():
        ibyfile = "%s.iby" % name
        out.write("\tBLD_INF_RULES.prj_exports += \"%s\tCORE_MW_LAYER_IBY_EXPORT_PATH(%s)\"\n" % (posixpath.join(outpath, ibyfile), ibyfile))
        for path, files in theme.files.iteritems():
            relpath = os.path.relpath(path, INPUT_DIR).replace("\\", "/")
            for filepath in files:
                filepath = os.path.splitdrive(filepath)[1]
                filename = os.path.basename(filepath)
                out.write("\tBLD_INF_RULES.prj_exports += \"%s\t%s/%s\"\n" % (filepath, BLD_HW_TARGET_PREFIX, posixpath.join(relpath, filename)))
                out.write("\tBLD_INF_RULES.prj_exports += \"%s\t%s/%s\"\n" % (filepath, BLD_EMU_TARGET_PREFIX, posixpath.join(relpath, filename)))
        for path, archives in theme.archives.iteritems():
            relpath = os.path.relpath(path, INPUT_DIR).replace("\\", "/")
            for filepath in archives:
                filepath = os.path.splitdrive(filepath)[1]
                filename = os.path.basename(filepath)
                if ARCHIVES:
                    out.write("\tBLD_INF_RULES.prj_exports += \"%s\t%s/%s\"\n" % (filepath, BLD_HW_TARGET_PREFIX, posixpath.join(relpath, filename)))
                    out.write("\tBLD_INF_RULES.prj_exports += \"%s\t%s/%s\"\n" % (filepath, BLD_EMU_TARGET_PREFIX, posixpath.join(relpath, filename)))
                else:
                    out.write("\tBLD_INF_RULES.prj_exports += \":zip %s\t%s/%s\"\n" % (filepath, BLD_HW_TARGET_PREFIX, relpath))
                    out.write("\tBLD_INF_RULES.prj_exports += \":zip %s\t%s/%s\"\n" % (filepath, BLD_EMU_TARGET_PREFIX, relpath))
    out.write("} else {\n")
    out.write("\tisEmpty(QMAKE_UNZIP):QMAKE_UNZIP = unzip -u -o\n")

    if settingsfile_exists:
        # installing theme settings file
        settingsPath = posixpath.join(INPUT_DIR,THEME_SETTINGS_FILE)
        out.write("\t%s.path += $$(HB_THEMES_DIR)/themes\n" % THEME_COMMON)
        out.write("\t%s.files += %s\n" % (THEME_COMMON, settingsPath))
        out.write("\tINSTALLS += %s\n" % THEME_COMMON)

    for name, theme in themes.iteritems():
        for path, files in theme.files.iteritems():
            target = make_target(path)
            relpath = os.path.relpath(path, INPUT_DIR).replace("\\", "/")
            out.write("\t%s.CONFIG += no_build\n" % target)
            out.write("\t%s.path += $$(HB_THEMES_DIR)/themes/%s\n" % (target, relpath))
            out.write("\t%s.files += %s\n" % (target, " ".join(files)))
            out.write("\tINSTALLS += %s\n" % target)
        for path, archives in theme.archives.iteritems():
            target = make_target(path)
            relpath = os.path.relpath(path, INPUT_DIR).replace("\\", "/")
            out.write("\t%s_zip.CONFIG += no_build\n" % target)
            out.write("\t%s_zip.path += $$(HB_THEMES_DIR)/themes/%s\n" % (target, relpath))
            if ARCHIVES:
                out.write("\t%s_zip.files += %s\n" % (target, " ".join(archives)))
            else:
                commands = []
                for archive in archives:
                    commands.append("$$QMAKE_UNZIP %s -d $$(HB_THEMES_DIR)/themes/%s" % (archive, relpath))
                out.write("\t%s_zip.commands += %s\n" % (target, " && ".join(commands)))
                out.write("\t%s_zip.uninstall += -$(DEL_FILE) $$(HB_THEMES_DIR)/themes/%s/*\n" % (target, relpath))
            out.write("\tINSTALLS += %s_zip\n" % target)
    out.write("}\n")
    out.close()


def write_common_iby(path):
    global VERBOSE, IBY_SOURCE_PREFIX, IBY_TARGET_PREFIX, OUTPUT_DIR, INPUT_DIR 
    global THEME_COMMON, THEME_SETTINGS_FILE

    # Create iby file for theme.theme if it is there
    theme_theme = posixpath.join(INPUT_DIR,THEME_SETTINGS_FILE)
    if os.path.isfile(theme_theme):
        if VERBOSE:
            print "Writing:  %s.iby" % THEME_COMMON
        ibypath = posixpath.join(OUTPUT_DIR, THEME_COMMON + ".iby")
        outpath = os.path.dirname(ibypath)
        if not os.path.exists(outpath):
            os.makedirs(outpath)
        out = open(ibypath, "w")
        out.write("#ifndef __%s_IBY__\n" % THEME_COMMON.upper())
        out.write("#define __%s_IBY__\n" % THEME_COMMON.upper())
        out.write("\n")
        out.write("#include <bldvariant.hrh>\n")
        out.write("\n")
        out.write("data=%s/%s\t%s/%s\n" % (IBY_SOURCE_PREFIX, THEME_SETTINGS_FILE, IBY_TARGET_PREFIX, THEME_SETTINGS_FILE))
        out.write("\n")
        out.write("#endif __%s_IBY__\n" % THEME_COMMON.upper())
        return True

    # theme common iby not written, return false
    return False

# ============================================================================
# main()
# ============================================================================
def main():
    global VERBOSE, ARCHIVES, INPUT_DIR, OUTPUT_DIR, INCLUDE, EXCLUDE, SYMBIAN, NAME, NVG
    global IBY_SOURCE_PREFIX, IBY_TARGET_PREFIX
    global BLD_HW_TARGET_PREFIX, BLD_EMU_TARGET_PREFIX, BLD_TARGET_PREFIXES

    parser = OptionParser()
    (options, args) = parser.parse_args()

    if options.verbose != None:
        VERBOSE = options.verbose
    if options.symbian != None:
        SYMBIAN = options.symbian
    if options.nvg != None:
        NVG = options.nvg
    if options.name != None:
        NAME = options.name
    if options.archives != None:
        ARCHIVES = options.archives
    if options.include != None:
        INCLUDE = options.include
    if options.exclude != None:
        EXCLUDE = options.exclude
    if options.input != None:
        INPUT_DIR = options.input
    if options.output != None:
        OUTPUT_DIR = options.output
    if options.ibysourceprefix != None:
        IBY_SOURCE_PREFIX = options.ibysourceprefix
    if options.ibytargetprefix != None:
        IBY_TARGET_PREFIX = options.ibytargetprefix
    if options.bldhwtargetprefix != None:
        BLD_HW_TARGET_PREFIX = options.bldhwtargetprefix
    if options.bldemutargetprefix != None:
        BLD_EMU_TARGET_PREFIX = options.bldemutargetprefix
    if options.bldtargetprefixes != None:
        BLD_TARGET_PREFIXES = options.bldtargetprefixes

    settingsfile_exists = write_common_iby(INPUT_DIR)

    themes = lookup_themes(INPUT_DIR)
    for name, theme in themes.iteritems():
        theme.initialize()
        if SYMBIAN and NVG:
            theme.encode()
        if VERBOSE:
            print "Writing:  %s/hbcolorgroup.css" % name
        theme.write_css(posixpath.join(OUTPUT_DIR, "style/%s/variables/color/hbcolorgroup.css" % name))
        if VERBOSE:
            print "Writing:  %s.iby" % name
        theme.write_iby(posixpath.join(OUTPUT_DIR, "%s.iby" % name))

    if SYMBIAN:
        prefixes = [BLD_HW_TARGET_PREFIX, BLD_EMU_TARGET_PREFIX]
        prefixes += BLD_TARGET_PREFIXES
    else:
        prefixes = [posixpath.join(os.environ["HB_THEMES_DIR"], "themes")]

    if VERBOSE:
        print "Writing:  %s.pri" % NAME
    write_pri(posixpath.join(OUTPUT_DIR, "%s.pri" % NAME), themes, prefixes, settingsfile_exists)
    if VERBOSE:
        print "Writing:  %s.txt" % NAME
    write_txt(posixpath.join(OUTPUT_DIR, "%s.txt" % NAME), themes, prefixes)

    return EXIT_STATUS

if __name__ == "__main__":
    sys.exit(main())
