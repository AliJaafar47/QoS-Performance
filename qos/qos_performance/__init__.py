# -*- coding: utf-8 -*-
#
# __init__.py
#
# Author:   Ali Jaafar
# Date:      6 Mars 2018
# Copyright (c) 2017-2018, 
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import signal
import os
import locale
from qos_performance import settings 
from qos_performance import batch
from qos_performance.settings import load
from qos_performance.gui import run_gui

def handle_sigterm(sig, frame):
    os.kill(os.getpid(), signal.SIGINT)

def run_qos_performance(gui=False):
    if sys.version_info[:3] < (2, 7, 3):
        sys.stderr.write("Sorry, Flent requires v2.7.3 or later of Python.\n")
        sys.exit(1)
    
    '''from qos_performance import batch
    from qos_performance.settings import load
    from qos_performance.loggers import setup_console, get_logger

    setup_console()
    logger = get_logger(__name__)
        
    signal.signal(signal.SIGTERM, handle_sigterm)
    settings = load(sys.argv[1:])
    if gui or len(sys.argv[1:])==0 :
        
        return run_gui(settings)
    else :
        settings = load(sys.argv[1:])
        b = batch.new(settings)
        b.run()
    return 0'''

    try:
        try:
            locale.setlocale(locale.LC_ALL, '')
        except locale.Error:
            pass
        from qos_performance import batch
        from qos_performance.settings import load
        from qos_performance.loggers import setup_console, get_logger

        setup_console()
        logger = get_logger(__name__)

        try:
            signal.signal(signal.SIGTERM, handle_sigterm)
            settings = load(sys.argv[1:])
            if gui or settings.GUI:
                from qos_performance.gui import run_gui
                return run_gui(settings)
            else:
                b = batch.new(settings)
                b.run()

        except RuntimeError as e:
            logger.exception(str(e))

    except KeyboardInterrupt:
        try:
            b.kill()
        except NameError:
            pass
        
def run_qos_performance_gui():
    return run_qos_performance(gui=True)


__all__ = ['run_qos_performance', 'run_qos_performance_gui']

