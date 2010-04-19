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
# Description:  Hb make index wrapper
#

MAKE = make

do_nothing :
	echo do_nothing

MAKMAKE : do_nothing

RESOURCE : do_nothing

SAVESPACE : do_nothing

BLD :
	-$(MAKE) index

FREEZE : do_nothing

LIB : do_nothing

CLEANLIB : do_nothing

FINAL : do_nothing

CLEAN : do_nothing

RELEASABLES : do_nothing
