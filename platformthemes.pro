#
# ============================================================================
#  Name        : platformthemes.pro
#  Part of     : platformthemes
#  Description : Project definition file for project platformthemes
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
#

NAME = platformthemes
TEMPLATE = subdirs
!symbian {
    HB_THEMES_DIR = $$(HB_THEMES_DIR)
    isEmpty(HB_THEMES_DIR) {
        win32:ENV_HELP = eg. set HB_THEMES_DIR=C:\hb\themes
        else:ENV_HELP = eg. export HB_THEMES_DIR=/usr/local/hb/themes
        error(HB_THEMES_DIR environment variable is not set. ($$ENV_HELP))
    }
} else {
    ARGS += --symbian
    nvg:ARGS += --nvg
    no_nvg:ARGS += --no-nvg
}
ARGS += -v --input $$IN_PWD/src --output $$OUT_PWD/src --name $$NAME
ARGS += --exclude \"*distribution.policy.s60\"
ARGS += --exclude \"*.orig\"
!system(python $$IN_PWD/bin/sync.py $$ARGS) {
    error(*** bin/sync.py reported an error. Stop.)
}

THEMEINDEXER = hbthemeindexer
!symbian {
    win32:!win32-g++ {
        unixstyle = false
    } else:win32-g++:isEmpty(QMAKE_SH) {
        unixstyle = false
    } else:symbian {
        unixstyle = false
    } else {
        unixstyle = true
    }

    $$unixstyle {
        DEVNULL = /dev/null
    } else {
        DEVNULL = nul
    }

    !system($$THEMEINDEXER > $$DEVNULL 2>&1) {
        error('hbthemeindexer' must be in PATH.)
    }
}

*symbian* {
    BLD_INF_RULES.prj_mmpfiles += "gnumakefile makeindex.mk"

    install.depends = default
    uninstall.depends = cleanexport
    QMAKE_EXTRA_TARGETS += install uninstall

    # central repository - exporting removed from platformthemes
#    BLD_INF_RULES.prj_exports += "$$section(PWD, ":", 1)/centralrepository/20022E82.txt $${EPOCROOT}epoc32/data/z/private/10202BE9/20022E82.txt"
#    BLD_INF_RULES.prj_exports += "$$section(PWD, ":", 1)/centralrepository/20022E82.txt $${EPOCROOT}epoc32/release/winscw/udeb/z/private/10202BE9/20022E82.txt"
#    BLD_INF_RULES.prj_exports += "$$section(PWD, ":", 1)/centralrepository/20022E82.txt $${EPOCROOT}epoc32/release/winscw/urel/z/private/10202BE9/20022E82.txt"
}
index.path = .
index.commands = $$THEMEINDEXER -f $$OUT_PWD/src/$${NAME}.txt
QMAKE_EXTRA_TARGETS += index

message(Run \'make install\')

include($$OUT_PWD/src/$${NAME}.pri)

# NOTE: must be after .pri include above!
INSTALLS += index
