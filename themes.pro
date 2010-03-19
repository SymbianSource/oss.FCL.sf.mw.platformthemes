#
# ============================================================================
#  Name        : themes.pro
#  Part of     : Hb-platformthemes
#  Description : Project definition file for project Hb-platformthemes
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
#

TEMPLATE = subdirs
!symbian {
    HB_THEMES_DIR = $$(HB_THEMES_DIR)
    isEmpty(HB_THEMES_DIR):error(HB_THEMES_DIR environment variable is not set)
}
ARGS = -v --input $$IN_PWD/src
!symbian:ARGS += --extract
system(python $$IN_PWD/bin/sync.py $$ARGS)

symbian {
    install.depends = export
    QMAKE_EXTRA_TARGETS += install
    message(Run 'make export')
} else {
    export.depends = install
    QMAKE_EXTRA_TARGETS += export
    message(Run 'make install')
}

include(themes.pri)
