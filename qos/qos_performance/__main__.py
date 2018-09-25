# -*- coding: utf-8 -*-
#
# __main__.py
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
from multiprocessing import freeze_support
sys.path.append("..")
import qos_performance as q

if __name__ == "__main__":
    freeze_support()
    sys.exit(q.run_qos_performance())
