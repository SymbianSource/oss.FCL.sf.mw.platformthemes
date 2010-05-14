#
# Copyright (c) 2008-2010 Nokia Corporation and/or its subsidiary(-ies).
# All rights reserved.
# This component and the accompanying materials are made available
# under the terms of "Eclipse Public License v1.0"
# which accompanies this distribution, and is available
# at the URL "http://www.eclipse.org/legal/epl-v10.html".
#
# Initial Contributors:
# Nokia Corporation - initial contribution.
#
# Contributors:
#
# Description:  Project definition file for project platformthemes
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
!system(python $$IN_PWD/bin/sync.py $$ARGS) {
    error(*** bin/sync.py reported an error. Stop.)
}

*symbian* {
    THEMEINDEXER = bin\hbthemeindexer_symbian.exe
} else {

    win32:!win32-g++ {
        unixstyle = false
    } else:win32-g++:isEmpty(QMAKE_SH) {
        unixstyle = false
    } else {
        unixstyle = true
    }

    $$unixstyle {
        DEVNULL = /dev/null
    } else {
        DEVNULL = nul
    }
    THEMEINDEXER = hbthemeindexer
    !system($$THEMEINDEXER > $$DEVNULL 2>&1) {
        error('hbthemeindexer' must be in PATH.)
    }
}

*symbian* {
    BLD_INF_RULES.prj_mmpfiles += "gnumakefile makeindex.mk"

    install.depends = default
    uninstall.depends = cleanexport
    QMAKE_EXTRA_TARGETS += install uninstall

    # central repository
    BLD_INF_RULES.prj_exports += "$$section(PWD, ":", 1)/centralrepository/20022E82.txt $${EPOCROOT}epoc32/data/z/private/10202BE9/20022E82.txt"
    BLD_INF_RULES.prj_exports += "$$section(PWD, ":", 1)/centralrepository/20022E82.txt $${EPOCROOT}epoc32/release/winscw/udeb/z/private/10202BE9/20022E82.txt"
    BLD_INF_RULES.prj_exports += "$$section(PWD, ":", 1)/centralrepository/20022E82.txt $${EPOCROOT}epoc32/release/winscw/urel/z/private/10202BE9/20022E82.txt"
}
index.path = .
index.commands = $$THEMEINDEXER -f $$OUT_PWD/src/$${NAME}.txt
QMAKE_EXTRA_TARGETS += index

message(Run \'make install\')

include($$OUT_PWD/src/$${NAME}.pri)

# NOTE: must be after .pri include above!
INSTALLS += index
