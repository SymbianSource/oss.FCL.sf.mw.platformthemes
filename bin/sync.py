#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ============================================================================
#  Name        : sync.py
#  Part of     : Hb
#  Description : Hb themes sync script
#  Version     : %version: 1 %
#
#  Copyright (c) 2008-2009 Nokia.  All rights reserved.
#  This material, including documentation and any related computer
#  programs, is protected by copyright controlled by Nokia.  All
#  rights are reserved.  Copying, including reproducing, storing,
#  adapting or translating, any or all of this material requires the
#  prior written consent of Nokia.  This material also contains
#  confidential information which may not be disclosed to others
#  without the prior written consent of Nokia.
# ============================================================================

import os
import shutil
import zipfile
import optparse

# ============================================================================
# Globals
# ============================================================================
VERBOSE = False
EXTRACT = False
ARCHIVES = False
INPUT_DIR = os.getcwd()
OUTPUT_DIR = os.getcwd()
IBY_SOURCE_PREFIX = "ZRESOURCE/hb/themes"
IBY_TARGET_PREFIX = "RESOURCE_FILES_DIR/hb/themes"
BLD_TARGET_PREFIX = "/epoc32/data/z/resource/hb/themes"
BLD_2ND_TARGET_PREFIX = "/epoc32/winscw/c/resource/hb/themes"

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

        group = optparse.OptionGroup(self, "Input/output options")
        self.add_option("-i", "--input", dest="input", metavar="dir",
                        help="specify the input <dir> (default %s)" % INPUT_DIR)
        self.add_option("-o", "--output", dest="output", metavar="dir",
                        help="specify the output <dir> (default %s)" % OUTPUT_DIR)
        self.add_option("-e", "--extract", action="store_true", dest="extract",
                        help="extract archives for installation (default %s)" % EXTRACT)
        self.add_option("-a", "--archives", action="store_true", dest="archives",
                        help="export/install archives (default %s)" % ARCHIVES)
        self.add_option_group(group)

        group = optparse.OptionGroup(self, "Prefix options")
        self.add_option("--iby-source-prefix", dest="ibysourceprefix", metavar="prefix",
                        help="specify the iby source <prefix> (default %s)" % IBY_SOURCE_PREFIX)
        self.add_option("--iby-target-prefix", dest="ibytargetprefix", metavar="prefix",
                        help="specify the iby target <prefix> (default %s)" % IBY_TARGET_PREFIX)
        self.add_option("--bld-target-prefix", dest="bldtargetprefix", metavar="prefix",
                        help="specify the bld target <prefix> (default %s)" % BLD_TARGET_PREFIX)
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

def extract(path, filepath):
    if not os.path.exists(path):
        os.makedirs(path)
    
    files = list()
    if VERBOSE:
        if EXTRACT:
            print "Extracting: %s" % filepath
        else:
            print "Reading: %s" % filepath
    archive = zipfile.ZipFile(filepath)
    for entry in archive.namelist():
        if entry.endswith("/"):
            if EXTRACT:
                out = os.path.join(path, entry)
                if not os.path.exists(out):
                    os.makedirs(out)
        else:
            files.append(entry)
            if EXTRACT:
                out = open(os.path.join(path, entry), "w")
                out.write(archive.read(entry))
                out.close()
    return files

class Theme:
    def __init__(self, name):
        self.name = name
        self.paths = []
        self.archives = []
        self.verbatims = []
        self.sources = {}
        self.targets = {}

    def initialize(self):
        for path in self.paths:
            for root, dirs, files in os.walk(path):
                for file in files:
                    filepath = os.path.join(root, file)
                    extension = os.path.splitext(filepath)[1]
                    if os.path.isfile(filepath) and extension == ".zip":
                        self.archives.append(filepath)
                    if os.path.isfile(filepath) and (extension in ['.css', '.theme']):
                        self.verbatims.append(filepath)
                        if VERBOSE:
                            print "Found: %s" % filepath
        for archive in self.archives:
            path = os.path.dirname(archive)
            if path not in self.sources:
                self.sources[path] = list()
            self.sources[path] += extract(path, archive)
        for verbatim in self.verbatims:
            path = os.path.dirname(verbatim)
            if path not in self.sources:
                self.sources[path] = list()
            file = os.path.split(verbatim)[1]
            filelist = list()
            filelist.append(file)
            self.sources[path] += filelist
        for path, files in self.sources.iteritems():
            relpath = os.path.relpath(path, INPUT_DIR)
            if relpath not in self.targets:
                self.targets[relpath] = list()
            self.targets[relpath] = files

    def write_iby(self, filepath):
        global IBY_SOURCE_PREFIX, IBY_TARGET_PREFIX
        out = open(filepath, "w")
        out.write("#ifndef __%s_IBY__\n" % self.name.upper())
        out.write("#define __%s_IBY__\n" % self.name.upper())
        out.write("\n")
        out.write("#include <bldvariant.hrh>\n")
        out.write("\n")
        for path, entries in self.targets.iteritems():
            for entry in entries:
                entry = os.path.join(path, entry)
                out.write("data=%s/%s\t%s/%s\n" % (IBY_SOURCE_PREFIX, entry, IBY_TARGET_PREFIX, entry))
        out.write("\n")
        out.write("#endif __%s_IBY__\n" % self.name.upper())
        out.close()

def lookup_themes(path):
    themes = {}
    # base: effects, icons...
    for base in os.listdir(path):
        basepath = os.path.join(path, base)
        if os.path.isdir(basepath):
            # theme: footheme, bartheme...
            for theme in os.listdir(basepath):
                themepath = os.path.join(basepath, theme)
                if os.path.isdir(themepath):
                    if theme not in themes:
                        themes[theme] = Theme(theme)
                    themes[theme].paths.append(themepath)
    return themes

def write_pri(filepath, themes):
    out = open(filepath, "w")
    out.write("symbian {\n")
    out.write("\tBLD_INF_RULES.prj_exports += \"$${LITERAL_HASH}include <platform_paths.hrh>\"\n")
    for name, theme in themes.iteritems():
        ibyfile = "%s.iby" % name
        out.write("\tBLD_INF_RULES.prj_exports += \"%s\tCORE_MW_LAYER_IBY_EXPORT_PATH(%s)\"\n" % (ibyfile, ibyfile))
        for verbatim in theme.verbatims:
            filename = os.path.basename(verbatim)
            relpath = os.path.relpath(os.path.dirname(verbatim), INPUT_DIR)
            verbatim = os.path.splitdrive(verbatim)[1]
            out.write("\tBLD_INF_RULES.prj_exports += \"%s\t%s/%s\"\n" % (verbatim, BLD_TARGET_PREFIX, os.path.join(relpath, filename)))
            out.write("\tBLD_INF_RULES.prj_exports += \"%s\t%s/%s\"\n" % (verbatim, BLD_2ND_TARGET_PREFIX, os.path.join(relpath, filename)))
        for archive in theme.archives:
            filename = os.path.basename(archive)
            relpath = os.path.relpath(os.path.dirname(archive), INPUT_DIR)
            archive = os.path.splitdrive(archive)[1]
            if ARCHIVES:
                out.write("\tBLD_INF_RULES.prj_exports += \"%s\t%s/%s\"\n" % (archive, BLD_TARGET_PREFIX, os.path.join(relpath, filename)))
                out.write("\tBLD_INF_RULES.prj_exports += \"%s\t%s/%s\"\n" % (archive, BLD_2ND_TARGET_PREFIX, os.path.join(relpath, filename)))
            else:
                out.write("\tBLD_INF_RULES.prj_exports += \":zip %s\t%s/%s\"\n" % (archive, BLD_TARGET_PREFIX, relpath))
                out.write("\tBLD_INF_RULES.prj_exports += \":zip %s\t%s/%s\"\n" % (archive, BLD_2ND_TARGET_PREFIX, relpath))
    out.write("} else {\n")
    for name, theme in themes.iteritems():
        if ARCHIVES:
            i = 1
            for archive in theme.archives:
                relpath = os.path.relpath(os.path.dirname(archive), INPUT_DIR)
                out.write("\t%s%i.path = $$(HB_THEMES_DIR)/themes/%s\n" % (name, i, relpath))
                out.write("\t%s%i.files += %s\n" % (name, i, archive))
                out.write("\tINSTALLS += %s%i\n" % (name, i))
                i += 1
        else:
            i = 1
            for path, files in theme.sources.iteritems():
                relpath = os.path.relpath(path, INPUT_DIR)
                out.write("\t%s%i.path = $$(HB_THEMES_DIR)/themes/%s\n" % (name, i, relpath))
                for file in files:
                    out.write("\t%s%i.files += %s\n" % (name, i, os.path.join(path, file)))
                out.write("\tINSTALLS += %s%i\n" % (name, i))
                i += 1
    out.write("}\n")
    out.close()

# ============================================================================
# main()
# ============================================================================
def main():
    global VERBOSE, EXTRACT, ARCHIVES, INPUT_DIR, OUTPUT_DIR
    global IBY_SOURCE_PREFIX, IBY_TARGET_PREFIX, BLD_TARGET_PREFIX

    parser = OptionParser()
    (options, args) = parser.parse_args()

    if options.verbose:
        VERBOSE = options.verbose
    if options.extract:
        EXTRACT = options.extract
    if options.archives:
        ARCHIVES = options.archives
    if options.input:
        INPUT_DIR = options.input
    if options.output:
        OUTPUT_DIR = options.output
    if options.ibysourceprefix:
        IBY_SOURCE_PREFIX = options.ibysourceprefix
    if options.ibytargetprefix:
        IBY_TARGET_PREFIX = options.ibytargetprefix
    if options.bldtargetprefix:
        BLD_TARGET_PREFIX = options.bldtargetprefix

    themes = lookup_themes(INPUT_DIR)
    for name, theme in themes.iteritems():
        theme.initialize()
        if VERBOSE:
            print "Writing: %s.iby" % name
        theme.write_iby(os.path.join(OUTPUT_DIR, "%s.iby" % name))

    if VERBOSE:
        print "Writing: themes.pri"
    write_pri(os.path.join(OUTPUT_DIR, "themes.pri"), themes)

if __name__ == "__main__":
    main()
