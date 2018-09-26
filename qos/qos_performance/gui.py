# -*- coding: utf-8 -*-
#
# gui.py
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
import base64

import netifaces
import os
import sys
import logging
import signal
import json
import time
import socket
import tempfile
import inspect
import subprocess
from itertools import chain

try:
    import cPickle as pickle
except ImportError:
    import pickle



from multiprocessing import Pool, Queue
from distutils.version import LooseVersion
from qos_performance.resultset import ResultSet
from qos_performance.build_info import VERSION
from plainbox.impl.session import state
from tkinter.constants import DISABLED
from qos_performance.settings import new, Settings,plot_group

from qos_performance import  resultset,util,batch,plotters
from qos_performance.settings import new as new_settings, plot_group
from qos_performance.util import clean_path, format_date,token_split
from qos_performance.loggers import  add_log_handler, remove_log_handler, \
    set_queue_handler

from qos_performance.loggers import get_logger
logger = get_logger(__name__)
print("logger",logger)
mswindows = (sys.platform == "win32")

# Python 2/3 compatibility
from qos_performance import batch, settings
from qos_performance.settings import *
try:
    from os import cpu_count
except ImportError:
    from multiprocessing import cpu_count

try:
    CPU_COUNT = cpu_count()
except NotImplementedError:
    CPU_COUNT = 1


FORCE_QT4 = False
try:
    import matplotlib
    ver = tuple([int(i) for i in matplotlib.__version__.split(".")[:2]])
    if ver < (1, 4):
        logger.debug("Forcing fallback to Qt4 because of old matplotlib v%s.",
                     matplotlib.__version__)
        FORCE_QT4 = True
    matplotlib.use("Agg")
except ImportError:
    raise RuntimeError("The GUI requires matplotlib.")

try:
    if FORCE_QT4:
        raise ImportError("Force fallback to Qt4")

    from PyQt5 import QtCore, QtGui, uic
    from PyQt5.QtWidgets import QTableWidgetItem
    from PyQt5.QtWidgets import QMessageBox, QFileDialog, QTreeView, \
        QAbstractItemView, QMenu, QAction, QTableView, QHeaderView, \
        QVBoxLayout, QApplication, QPlainTextEdit, QMainWindow

    from PyQt5.QtGui import QFont, QCursor, QMouseEvent, QKeySequence, \
        QResizeEvent, QDesktopServices,QPixmap,QStandardItemModel,QGuiApplication
    from PyQt5.Qt import QWidget



    get_clipboard = QGuiApplication.clipboard
    
    from PyQt5.QtCore import Qt, QIODevice, QByteArray, \
        QDataStream, QSettings, QTimer, QEvent, pyqtSignal, \
        QAbstractItemModel, QAbstractTableModel, QModelIndex, \
        QItemSelectionModel, QStringListModel, QUrl

    from PyQt5.QtNetwork import QLocalSocket, QLocalServer

    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg \
        as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT \
        as NavigationToolbar
    QTVER = 5
    from PyQt5.Qt import QPushButton
except ImportError:
    try:
        from PyQt4 import QtCore, QtGui, uic
        from PyQt4.QtWidgets import QTableWidgetItem
        from PyQt4.QtGui import QMessageBox, QFileDialog, QTreeView, \
            QAbstractItemView, QMenu, QAction, QFont, QTableView, QCursor, \
            QHeaderView, QVBoxLayout, QItemSelectionModel, QMouseEvent, \
            QApplication, QStringListModel, QKeySequence, QResizeEvent, \
            QPlainTextEdit, QDesktopServices,QStandardItemModel
            
        get_clipboard = QApplication.clipboard
        
        from PyQt4.QtCore import Qt, QIODevice, QByteArray, \
            QDataStream, QSettings, QTimer, QEvent, pyqtSignal, \
            QAbstractItemModel, QAbstractTableModel, QModelIndex, QUrl

        from PyQt4.QtNetwork import QLocalSocket, QLocalServer

        from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg \
            as FigureCanvas
        from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT \
            as NavigationToolbar

        QTVER = 4
        from PyQt5.Qt import QPushButton
        if not FORCE_QT4:
            logger.warning("Falling back to Qt4 for the GUI. "
                           "Please consider installing PyQt5.\n")
    except ImportError:
        raise RuntimeError("PyQt must be installed to use the GUI.")
try :
    ## for python 3.x
    from configparser import ConfigParser
    
except ImportError :
    ## for python 2.x
    from ConfigParser import ConfigParser

from qos_performance.build_info import DATA_DIR, VERSION


if hasattr(QtGui, "qt_mac_set_native_menubar"):
    FILE_SELECTOR_STRING = "Flent data files " \
                           "(*.flent *.flnt *.flent.gz *.flent.bz2 *.json.gz)"
    osx = True
else:
    FILE_SELECTOR_STRING = "Flent data files (*.flent *.flent.gz *.flent.bz2);;" \
                           "Flent data files - " \
                           "deprecated extensions (*.flnt *.json.gz)"
    osx = False
FILE_SELECTOR_STRING += ";;All files (*.*)"

            
            
SOCKET_NAME_PREFIX = "flent-socket-"
SOCKET_DIR = tempfile.gettempdir()
WINDOW_STATE_VERSION = 1
# IPC socket parameters
#SOCKET_NAME_PREFIX = "flent-socket-"
#SOCKET_DIR = tempfile.gettempdir()
#WINDOW_STATE_VERSION = 1

ABOUT_TEXT = """<p>QoS-Performance version {version}.<br>
Copyright &copy; 2017 Telnet.<br>
Released under the GNU GPLv3.</p>

<p>To report a bug, please <a href="https://github.com/AliJaafar47/QoS-Performance/issues">
file an issue on Github<a>.</p>"""

def getUiClass(filename):
    """
    Helper method to dynamically load a .ui file, construct a class
    inheriting from the ui class and the associated base class, and return
    that constructed class.

    This allows subclasses to inherit from the output of this function.
    :param filename:
    """

    try:
        ui, base = uic.loadUiType(os.path.join(DATA_DIR, 'ui', filename))
    except Exception as e:
        raise RuntimeError("While loading ui file '%s': %s" % (filename, e))

    class C(ui, base):

        def __init__(self, *args):
            base.__init__(self, *args)
            self.setupUi(self)
    return C
#added 12/09
def pool_init_func(settings, queue):
    plotters.init_matplotlib("-", settings.USE_MARKERS,
                             settings.LOAD_MATPLOTLIBRC)
    set_queue_handler(queue)



class MainWindow(getUiClass("mainwindow.ui")):
    def __init__(self,settings):
        super(MainWindow, self).__init__()
        self.settings = settings
        Ui_MainWindow, QtBaseClass = uic.loadUiType(os.path.join(DATA_DIR, 'ui', "mainwindow.ui"))
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        #set the main ui icons 
        main_icon = QtGui.QPixmap("ui/static/qos_web.png")
        setting_icon = QtGui.QIcon()
        setting_icon.addPixmap(QtGui.QPixmap("ui/static/configure.jpg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
        new_test_icon = QtGui.QIcon()
        new_test_icon.addPixmap(QtGui.QPixmap("ui/static/service.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
        import_icon = QtGui.QIcon()
        import_icon.addPixmap(QtGui.QPixmap("ui/static/open-folder.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
        help_icon = QtGui.QIcon()
        help_icon.addPixmap(QtGui.QPixmap("ui/static/help.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
        
        #set icons to the buttons
        self.ui.main_icon.setPixmap(main_icon)
        self.ui.setting_button.setIcon(setting_icon)
        self.ui.new_test_button.setIcon(new_test_icon)
        self.ui.import_button.setIcon(import_icon)
        self.ui.help_button.setIcon(help_icon)
        logger.info("GUI loaded. Running on PyQt v%s.", QtCore.PYQT_VERSION_STR)
        
        # button handlers
        self.ui.setting_button.clicked.connect(self.handler_setting_button)
        # button help handler
        self.ui.help_button.clicked.connect(self.handler_help_button)
        
        # button new test handler
        self.ui.new_test_button.clicked.connect(self.handler_new_test_button)
        
        # other window setting 
        self.configwindow = ConfigWindow()
        self.helpwindow = HelpWindow()
        self.newTestWindow = NewTestWindow(self.settings)
    
    def handler_new_test_button(self):
        self.newTestWindow.show()
        #print("help")
        
    def handler_help_button(self):
        self.helpwindow.show()
        #print("help")
        
    def handler_setting_button(self):
        #print("setting_button clicked")
        self.configwindow.show()

    def center(self):
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())
        
class ConfigWindow(getUiClass("configwindow.ui")):
    def __init__(self):
        super(ConfigWindow, self).__init__()
        Ui_MainWindow, QtBaseClass = uic.loadUiType(os.path.join(DATA_DIR, 'ui', "configwindow.ui"))
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        #set the add icons
        add_new_host_icon = QtGui.QIcon()
        add_new_host_icon.addPixmap(QtGui.QPixmap("ui/static/add.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.add_new_host.setIcon(add_new_host_icon)
        
        #set the refresh icons 
        refresh_icon = QtGui.QIcon()
        refresh_icon.addPixmap(QtGui.QPixmap("ui/static/refresh.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.refresh_button.setIcon(refresh_icon)
        
        
        ## add new host button handler
        self.ui.add_new_host.clicked.connect(self.handler_add_new_host_button)
        
        ## add a handler to ok button
        self.ui.ok_button.clicked.connect(self.handler_ok_button)
        ## add a handler to cancel button
        self.ui.cancel_button.clicked.connect(self.handler_cancel_button)
        
        ## add a handler to refresh button
        self.ui.refresh_button.clicked.connect(self.handler_refresh_button)
 
        #config file 
        # TODO : import a config file (passing config name as parameter)
        self.configfile="config.ini"
        self.set_config_table()
    
    
    
    ## refresh button handler
    def handler_refresh_button(self):
        #print("refrech button clicked")
        #self.ui.cancel_button.setVisible(False)
        allRows = self.ui.tableWidget.rowCount()
        for row in range(0,allRows): 
            ip = self.ui.tableWidget.item(row,1).text()## ip
            host_name = self.ui.tableWidget.item(row,2).text()## host name
            password = self.ui.tableWidget.item(row,3).text()## password
            set = get_settings_check_installed_tools(ip,host_name,password)
            settings = load(set)
            try :
                b = batch.new(settings)
            except :
                 self.ui.tableWidget.setItem(row,7, QTableWidgetItem("Authentication failed."))
                 
            installed_icon = QtGui.QIcon()
            installed_icon.addPixmap(QtGui.QPixmap("ui/static/installed.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            
            not_installed_icon = QtGui.QIcon()
            not_installed_icon.addPixmap(QtGui.QPixmap("ui/static/not_installed.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            
            try : 
                result = b.check_installed_tools()
            except :
                print("Enable to establish connection")
                self.ui.tableWidget.setItem(row,7, QTableWidgetItem("Enable to connect to remote host"))
                
                #self.ui.tableWidget.setColumnWidth(row, self.ui.tableWidget.columnWidth(row) + 30)
                #self.ui.tableWidget.resizeColumnsToContents()
                continue
            res=""
            not_installed = 1
            for i in result :
                res = res+str(i)+"\n"
                self.ui.tableWidget.setItem(row,7, QTableWidgetItem(res))
                self.ui.tableWidget.resizeColumnsToContents()
                self.ui.tableWidget.setColumnWidth(row, self.ui.tableWidget.columnWidth(row) + 10)
                self.ui.tableWidget.setRowHeight(row,  80)
                
                
                
                
                if "Not" in i.split(":")[1] :
                    print("found one")
                    not_installed = 2
                    self.ui.tableWidget.setItem(row,5, QTableWidgetItem(not_installed_icon,""))
                    
                
            
            print(not_installed)
            if not_installed == 1 :
                    #print("False")
                self.ui.tableWidget.setItem(row,5, QTableWidgetItem(installed_icon,""))
                    

        # Stretch Vertical Header
        #self.ui.tableWidget.resizeColumnsToContents()
        #headerVertical = self.ui.tableWidget.verticalHeader()
        #headerVertical.setStretchLastSection(True)

    def handler_ok_button(self):
        number = self.get_config_hosts_number()
        allRows = self.ui.tableWidget.rowCount()
        #print(allRows)
        #print("Ok button clicked")
        configuration = []
        for row in range(0,allRows):
            twi0 = self.ui.tableWidget.item(row,0).text()
            #print(twi0)
            if twi0 in configuration :
                QMessageBox.warning(self, "Message", "Invalid data input: 2 or more hosts are having the same host_name") 
                return 0 
            else :
                configuration.append(twi0)
        
                
        config = ConfigParser()
        for row in range(0,allRows): 
            try :
                config[self.ui.tableWidget.item(row,0).text()] = {'host_name': self.ui.tableWidget.item(row,0).text(),'host_ip': self.ui.tableWidget.item(row,1).text(),'user_name': self.ui.tableWidget.item(row,2).text(),'password': self.ui.tableWidget.item(row,3).text(),'tools_status': self.ui.tableWidget.item(row,5).text()}
            except :
                config.add_section(self.ui.tableWidget.item(row,0).text())
                config.set(self.ui.tableWidget.item(row,0).text(), 'host_name', self.ui.tableWidget.item(row,0).text())
                config.set(self.ui.tableWidget.item(row,0).text(), 'host_ip', self.ui.tableWidget.item(row,1).text())
                config.set(self.ui.tableWidget.item(row,0).text(), 'user_name', self.ui.tableWidget.item(row,2).text())
                config.set(self.ui.tableWidget.item(row,0).text(), 'password', self.ui.tableWidget.item(row,3).text())
                config.set(self.ui.tableWidget.item(row,0).text(), 'tools_status', self.ui.tableWidget.item(row,5).text())
        
        with open('config/'+self.configfile, 'w') as configfile:
            config.write(configfile)
        self.close()

    def handler_cancel_button(self):
        #print("closing..")
        self.close()
        
    def handler_add_new_host_button(self):
        j= self.ui.tableWidget.rowCount()
        self.ui.tableWidget.setRowCount(j+1)
        for k in range(0,8):
            if k == 0 :
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 1 : 
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 2 : 
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 3 :
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 4 : 
                ## button Tools
                self.btn = QPushButton('Install Tools')
                self.btn.setObjectName("install")
                self.ui.tableWidget.setCellWidget(j,k, self.btn)
                self.btn.clicked.connect(self.handler_install_button(j))
            if k == 5 : 
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem("unknown"))
            if k == 6 : 
                self.btn = QPushButton('Delete')
                self.btn.setObjectName("install")
                self.ui.tableWidget.setCellWidget(j,k, self.btn)
                self.btn.clicked.connect(self.handler_delete_button(j))
            if k == 7 : 
                ## button option
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem("N/A"))

    def get_config_data(self):
        cfg = ConfigParser()
        cfg.read('config/'+self.configfile)
        config = []
        for section in cfg.sections():
            x = {}
            for name, value in cfg.items(section):
                x[name] = value
            config.append(x)
        return (config)
    
    def get_config_hosts_number(self):
        cfg = ConfigParser()
        cfg.read('config/'+self.configfile)
        i=0
        for section in cfg.sections():
            i=i+1
        return i
    
    def set_config_table(self):
        ## Get the config file 
        config = self.get_config_data()
        #print(config)
        # Set Horizontal Header
        self.ui.tableWidget.setColumnCount(8)
        self.ui.tableWidget.setHorizontalHeaderLabels(['Host name','Host IP','User Name*','Password','Tools','Tools Status','Option','Details'])
        
        headerHorizontal = self.ui.tableWidget.horizontalHeader()
        headerHorizontal.setStretchLastSection(True)      
        #headerHorizontal.resizeColumnsToContents()

        # Set Vertical Header
        self.ui.tableWidget.setRowCount(self.get_config_hosts_number())


        # Print the keys and values
        j = 0
        k = 0
        for i in config:
            for k in range(0,8):
                if k == 0 :
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"host_name")))
                if k == 1 : 
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"host_ip")))
                if k == 2 : 
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"user_name")))
                if k == 3 :
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"password")))
                if k == 4 : 
                    ## button Tools
                    self.btn = QPushButton('Install Tools')
                    self.btn.setObjectName("install")
                    self.ui.tableWidget.setCellWidget(j,k, self.btn)
                    self.btn.clicked.connect(self.handler_install_button(j))
                if k == 5 : 
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"tools_status")))
                if k == 6 :
                    #
                    self.btn = QPushButton('Delete')
                    self.btn.setObjectName("install")
                    self.ui.tableWidget.setCellWidget(j,k, self.btn)
                    self.btn.clicked.connect(self.handler_delete_button(j))
                if k == 7 : 
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem('N/A'))
                    ## button option

            j = j+1
            
    def handler_install_button(self, index):
        def calluser():
            #print("handler_button")
            ip = self.ui.tableWidget.item(index,1).text()## ip
            host_name = self.ui.tableWidget.item(index,2).text()## host name
            password = self.ui.tableWidget.item(index,3).text()## password
            set = get_settings_install_tools(ip,host_name,password)
            settings = load(set)
            try :
                b = batch.new(settings)
            except :
                self.ui.tableWidget.setItem(index,7, QTableWidgetItem("Authentication failed."))
            try : 
                result = b.run_install_tools()
            except :
                print("Enable to establish connection")
                self.ui.tableWidget.setItem(index,7, QTableWidgetItem("Enable to connect to remote host"))
                
            
            self.handler_refresh_button()
        return calluser
            
    def handler_delete_button(self, index):
        def calluser():
            self.ui.tableWidget.removeRow(index)
        return calluser

    
class HelpWindow(getUiClass("helpwindow.ui")):
    def __init__(self):
        super(HelpWindow, self).__init__()
        Ui_MainWindow, QtBaseClass = uic.loadUiType(os.path.join(DATA_DIR, 'ui', "helpwindow.ui"))
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        #about text 
        self.ui.aboutText.setText(ABOUT_TEXT.format(version=VERSION))
        # button close handler
        self.ui.close_button.clicked.connect(self.handler_close_button)
        
    def handler_close_button(self):
        self.close()

def get_value_from_json(dict_doc,key_att):
    for (key, value) in dict_doc.items():
        if  key == key_att :
            return value
        
class NewTestWindow(getUiClass("run_new_test.ui")):
    def __init__(self,settings):
        super(NewTestWindow, self).__init__()
        self.settings = settings
        Ui_MainWindow, QtBaseClass = uic.loadUiType(os.path.join(DATA_DIR, 'ui', "run_new_test.ui"))
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        #Tests name 
        print(DATA_DIR)
        self.ui.comboBox.insertItem(0,"QoS-Remarquing tests")
        self.ui.comboBox.insertItem(1,"WMM Tests")
        self.ui.comboBox.insertItem(2,"Performance tests")
        
        # handlers names 
        self.ui.ok_button.clicked.connect(self.handler_ok_button)
        self.ui.cancel_button.clicked.connect(self.handler_cancel_button)
        self.qosRemarquing=QosRemarquing()
        self.performance=performance()
        self.wmm_test= wmm_test()

        
        
    def handler_ok_button(self):
        if str(self.ui.comboBox.currentText()) == "QoS-Remarquing tests":
            print("QoS-Remarquing tests")
            
            self.qosRemarquing.show()
            
        elif str(self.ui.comboBox.currentText()) == "WMM Tests":
            self.wmm_test.show()
            print("WMM Tests")
            
#Niwar
#17/07/2018
        else:
            print("Performance tests")
            self.performance.show()
                
            '''self.performance.show()'''
        self.close()
#end        
        
    def handler_cancel_button(self):
        print("cancel")
        self.close()
        
        
class QosRemarquing(getUiClass("qos_remarquing.ui")):
    def __init__(self):
        self.configfile="config.ini"
        super(QosRemarquing, self).__init__()
        Ui_MainWindow, QtBaseClass = uic.loadUiType(os.path.join(DATA_DIR, 'ui', "qos_remarquing.ui"))
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        #Traffic Type name 
        self.ui.traffic_type.insertItem(0,"TCP")
        self.ui.traffic_type.insertItem(1,"UDP")
        
        #Destination hosts 
        conf = self.get_config_data()
        
        for i in range(0,self.get_config_hosts_number()):
            self.ui.dest_host.insertItem(i,conf[i]["host_ip"])
    
            
    def get_config_data(self):
        cfg = ConfigParser()
        cfg.read('config/'+self.configfile)
        config = []
        for section in cfg.sections():
            x = {}
            for name, value in cfg.items(section):
                x[name] = value
            config.append(x)
        return (config)
    
    def get_config_hosts_number(self):
        cfg = ConfigParser()
        cfg.read('config/'+self.configfile)
        i=0
        for section in cfg.sections():
            i=i+1
        return i
        
class LoadedResultset(dict):
    pass


def results_load_helper(filename):
    try:
        r = ResultSet.load_file(filename)
        s = new_settings()
        s.update(r.meta())
        s.load_test(informational=True)
        s.compute_missing_results(r)
        return LoadedResultset(results=r,
                               plots=s.PLOTS,
                               data_sets=s.DATA_SETS,
                               defaults=s.DEFAULTS,
                               description=s.DESCRIPTION,
                               title=r.title)
    except Exception as e:
        logger.exception("Unable to load file '%s': '%s'", filename, e)
        return None



class ResultsetStore(object):

    def __init__(self):
        self._store = {}
        self._order = []
        self._sort_key = 'DATA_FILENAME'
        self._sort_rev = False

    def __len__(self):
        return sum([len(i) for i in self._store.values()])

    def __contains__(self, itm):
        for v in self._store.values():
            if itm in v:
                return True
        return False

    def __getitem__(self, idx):
        offset = 0
        for k in self._order:
            v = self._store[k]
            if idx < len(v) + offset:
                return v[idx - offset]
            offset += len(v)
        raise IndexError()

    def sort(self, key=None, reverse=False, only=None):
        if key is None:
            key = self._sort_key
            reverse = self._sort_rev

        def get_key(itm):
            try:
                return unicode(itm.meta(key))
            except KeyError:
                return ''
        if only:
            only.sort(key=get_key, reverse=reverse)
        else:
            self._sort_key, self._sort_rev = key, reverse
            for v in self._store.values():
                v.sort(key=get_key, reverse=reverse)

    def update_order(self, active):
        self._order = [active] + sorted([i for i in self._order if i != active])

    def append(self, itm):
        k = itm.meta('NAME')
        if k in self._store:
            self._store[k].append(itm)
            self.sort(only=self._store[k])
        else:
            self._store[k] = [itm]
            self._order.append(k)





class OpenFilesModel(QAbstractTableModel):
    test_name_role = Qt.UserRole

    def __init__(self, parent):
        QAbstractTableModel.__init__(self, parent)
        self._parent = parent
        self.open_files = ResultsetStore()
        self.columns = [(None, 'Act'),
                        ('DATA_FILENAME', 'Filename'),
                        ('TITLE', 'Title')]
        self.active_widget = None

    @property
    def ctrl_pressed(self):
        return bool(QApplication.keyboardModifiers() & Qt.ControlModifier)

    def save_columns(self):
        return base64.b64encode(pickle.dumps(self.columns, protocol=0)).decode()

    def restore_columns(self, data):
        try:
            cols = pickle.loads(base64.b64decode(data))
        except:
            return
        if len(cols) > len(self.columns):
            self.beginInsertColumns(
                QModelIndex(), len(self.columns), len(cols) - 1)
            self.columns = cols
            self.endInsertColumns()
        elif len(cols) < len(self.columns):
            self.beginRemoveColumns(
                QModelIndex(), len(cols), len(self.columns) - 1)
            self.columns = cols
            self.endRemoveColumns()
        else:
            self.columns = cols
        self.update()

    @property
    def has_widget(self):
        return self.active_widget is not None and self.active_widget.is_active

    def is_active(self, idx):
        if not self.has_widget:
            return False
        return self.active_widget.has(self.open_files[idx])

    def update_order(self):
        if self.has_widget:
            self.open_files.update_order(self.active_widget.results.meta("NAME"))

    def set_active_widget(self, widget):
        self.active_widget = widget
        self.update()

    def on_click(self, idx):
        if not self.is_active(idx.row()) or self.ctrl_pressed:
            self.activate(idx.row())
        else:
            self.deactivate(idx.row())

    def update(self):
        self.update_order()
        self.dataChanged.emit(self.index(0, 0), self.index(len(self.open_files),
                                                           len(self.columns)))

    def activate(self, idx, new_tab=False):
        if new_tab or not self.has_widget or self.ctrl_pressed:
            self._parent.load_files([self.open_files[idx]])
            return True
        ret = self.active_widget.add_extra(self.open_files[idx])
        self.update()
        return ret

    def deactivate(self, idx):
        if not self.has_widget:
            return False
        ret = self.active_widget.remove_extra(self.open_files[idx])
        self.update()
        return ret

    def is_primary(self, idx):
        if not self.has_widget:
            return False
        return self.active_widget.results == self.open_files[idx]

    def add_file(self, r):
        if r in self.open_files:
            return
        self.beginInsertRows(QModelIndex(), len(
            self.open_files), len(self.open_files))
        self.open_files.append(r)
        self.endInsertRows()
        self.update()

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.open_files)

    def columnCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.columns)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.columns[section][1]
        if role == Qt.DisplayRole and orientation == Qt.Vertical:
            return section + 1
        if role == Qt.ToolTipRole and \
           orientation == Qt.Horizontal and \
           section > 0:
            return "Metadata path: %s.\nRight click to add or remove columns." \
                % self.columns[section][0]
        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter

    def flags(self, idx):
        flags = super(OpenFilesModel, self).flags(idx)
        if idx.column() == 0:
            flags |= Qt.ItemIsUserCheckable
        if (self.has_widget and
            self.active_widget.results.meta("NAME") !=
            self.open_files[idx.row()].meta("NAME"))\
           or (self.is_primary(idx.row()) and
               len(self.active_widget.extra_results) == 0):
            flags &= ~Qt.ItemIsEnabled
        return flags

    def get_metadata(self, idx, name):
        try:
            return unicode(self.open_files[idx].meta(name))
        except KeyError:
            return None

    def removeColumn(self, col, parent):
        if col == 0:
            return False
        self.beginRemoveColumns(parent, col, col)
        self.columns[col:col + 1] = []
        self.endRemoveColumns()

    def add_column(self, pos, path, name):
        self.beginInsertColumns(QModelIndex(), pos, pos)
        self.columns.insert(pos, (path, name))
        self.endInsertColumns()

    def data(self, idx, role=Qt.DisplayRole):
        if role == self.test_name_role:
            return self.open_files[idx.row()].meta('NAME')
        if idx.column() == 0:
            value = self.is_active(idx.row())
            if role == Qt.CheckStateRole:
                return Qt.Checked if value else Qt.Unchecked
            else:
                return None
        if role == Qt.ToolTipRole:
            if not self.has_widget:
                return "Click to open in new tab."
            elif self.is_primary(idx.row()) and len(
                    self.active_widget.extra_results) == 0:
                return "Can't deselect last item. Ctrl+click to open in new tab."
            elif self.flags(idx) & Qt.ItemIsEnabled:
                return "Click to select/deselect. Ctrl+click to open in new tab."
            else:
                return "Ctrl+click to open in new tab."
        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter
        if role == Qt.DisplayRole:
            return self.get_metadata(idx.row(), self.columns[idx.column()][0])
        if role == Qt.FontRole:
            font = QFont()
            if self.is_primary(idx.row()) and font is not None:
                font.setBold(True)
            return font

    def sort(self, column, order):
        if column == 0:
            return
        key = self.columns[column][0]
        self.open_files.sort(key, (order == Qt.DescendingOrder))
        self.update()


#Niwar Benjeddy
#16/07/2018
class performance(getUiClass("performanceTest.ui")):   
    def __init__(self,
):
        self.configfile="config_performanceTest.ini"
        super(performance, self).__init__()
        self.settings = settings
        self.settings.INPUT = []
        self.load_queue = []
        self.log_queue = Queue()
        self.pid = None
        self.aborted = False
        self.settings.GUI = False
        self.last_dir = os.getcwd()
        #added since 12/09
        settings.LOAD_MATPLOTLIBRC =True
        self.settings.USE_MARKERS =True
        self.load_timer = QTimer(self)
        

        #end add

        Ui_MainWindow, QtBaseClass = uic.loadUiType(os.path.join(DATA_DIR, 'ui', "performanceTest.ui"))
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.ui.viewArea.tabCloseRequested.connect(self.close_tab)
        self.ui.viewArea.currentChanged.connect(self.activate_tab)

        self.ui.combobox_perf.insertItem(0,"Flent_Http: http latency test")
        self.ui.combobox_perf.insertItem(1,"PPING_Http: http latency test")
        self.ui.combobox_perf.insertItem(2,"Performance with user experience estimation")
        
        setting_icon1 = QtGui.QIcon()
        setting_icon1.addPixmap(QtGui.QPixmap("ui/static/configure.jpg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
        self.ui.trafficsetting_button.setIcon(setting_icon1)
        self.ui.trafficsetting_button.clicked.connect(self.handler_customize2_button)
        
        
        self.server = QLocalServer()
        self.sockets = []
        self.server.newConnection.connect(self.new_connection)
        self.server.listen(os.path.join(SOCKET_DIR, "%s%d" %
                                        (SOCKET_NAME_PREFIX, os.getpid())))
        
        self.ui.trafficsetting_button.clicked.connect(self.handler_customize2_button)
 
        
        self.ui.setting_button.setIcon(setting_icon1)
        self.worker_pool = Pool(initializer=pool_init_func,
                                initargs=(self.settings, self.log_queue))
        #select directory
        self.ui.outputDir.setText("/home/niwar/Bureau/ppa")
        self.ui.selectOutputDir.clicked.connect(self.select_output_dir)
        
       
        self.ui.setting_button.clicked.connect(self.handler_customize_button)
        self.customize = TestConfguration()
        
        #self.ui.actionOpen.clicked.connect(self.on_open)
        #checkbox are by default disabled
        self.ui.checkBox_NTP.setEnabled(False)
        self.ui.setting_button.setEnabled(False)
        self.ui.trafficsetting_button.setEnabled(False)
         
        self.ui.combobox_perf.currentIndexChanged['QString'].connect(self.enableConbobox)
        
        
        #Run test
        self.ui.combobox_perf.setCurrentIndex(self.ui.combobox_perf.currentIndex())
        
        self.customize2 = TrafficConfguration()
        
        self.ui.runButton.clicked.connect(self.run_or_abort)
        self.load_timer.timeout.connect(self.load_one)
        self.open_files = OpenFilesModel(self)
        self.monitor_timer = QTimer()
        self.monitor_timer.setInterval(500)
        self.monitor_timer.setSingleShot(False)
        self.monitor_timer.timeout.connect(self.update_progress)
        self.logEntries = QPlainTextLogger(self,
                                           level=logging.DEBUG,
                                           widget=self.ui.logTextEdit)
    
    def new_connection(self):
        sock = self.server.nextPendingConnection()
        self.sockets.append(sock)
        sock.readyRead.connect(self.data_ready)
    
        
    def shorten_titles(self, titles):
        new_titles = []
        substr = util.long_substr(titles)
        prefix = util.long_substr(titles, prefix_only=True)

        for t in titles:
            if len(substr) > 0:
                text = t.replace(substr, "...")
            if len(prefix) > 0 and prefix != substr:
                text = text.replace(prefix, "...").replace("......", "...")
            if len(substr) == 0 or text == "...":
                text = t
            new_titles.append(text)

        return new_titles    
    
    def shorten_tabs(self):
        """Try to shorten tab labels by filtering out common substrings.

        Approach: Find longest common substring and replace that with ellipses
        in the name. Also, find longest common *prefix* and filter that out as
        well.

        Since tab titles start with the test name, and several tests are
        commonly loaded as well, this double substring search helps cut off the
        (common) test name in the case where the longest substring is in the
        middle of the tab name."""

        titles = []
        long_titles = []
        indexes = []
        for i in range(self.ui.viewArea.count()):
            if self.ui.viewArea.widget(i).title == ResultWidget.default_title:
                continue
            titles.append(self.ui.viewArea.widget(i).title)
            long_titles.append(self.ui.viewArea.widget(i).long_title)
            indexes.append(i)

        titles = self.shorten_titles(titles)

        for i, t, lt in zip(indexes, titles, long_titles):
            self.ui.viewArea.setTabText(i, t)
            self.ui.viewArea.setTabToolTip(i, lt)

    def close_tab(self, idx=None):
        self.busy_start()
        if idx in (None, False):
            idx = self.ui.viewArea.currentIndex()
        widget = self.ui.viewArea.widget(idx)
        if widget is not None:
            widget.setUpdatesEnabled(False)
            widget.disconnect_all()
            self.ui.viewArea.removeTab(idx)
            widget.setParent(None)
            widget.deleteLater()
            self.shorten_tabs()
        self.busy_end()

    def close_all(self):
        self.busy_start()
        widgets = []
        for i in range(self.ui.viewArea.count()):
            widgets.append(self.ui.viewArea.widget(i))
        self.ui.viewArea.clear()
        for w in widgets:
            w.setUpdatesEnabled(False)
            w.disconnect_all()
            w.setParent(None)
            w.deleteLater()
        self.busy_end()

    def move_tab(self, move_by):
        count = self.ui.viewArea.count()
        if count:
            idx = self.ui.viewArea.currentIndex()
            self.ui.viewArea.setCurrentIndex((idx + move_by) % count)

    def next_tab(self):
        self.move_tab(1)

    def prev_tab(self):
        self.move_tab(-1)

    def move_plot(self, move_by):
        model = self.ui.plotView.model()
        if not model:
            return

        count = model.rowCount()
        if count:
            idx = self.ui.plotView.currentIndex()
            row = idx.row()
            self.ui.plotView.setCurrentIndex(model.index((row + move_by) % count))

    def next_plot(self):
        self.move_plot(1)

    def prev_plot(self):
        self.move_plot(-1)
    
    
    def redraw_near(self, idx=None):
        if idx is None:
            idx = self.ui.viewArea.currentIndex()

        rng = (CPU_COUNT + 1) // 2
        # Start a middle, go rng steps in either direction (will duplicate the
        # middle idx, but that doesn't matter, since multiple redraw()
        # operations are no-op.
        for i in chain(*[(idx+i, idx-i) for i in range(rng + 1)]):
            while i < 0:
                i += self.ui.viewArea.count()
            w = self.ui.viewArea.widget(i)
            if w:
                w.redraw()
    
    def busy_start(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)   
        
    def busy_end(self):
        QApplication.restoreOverrideCursor()
            
    
        
    def activate_tab(self, idx=None):
        if idx is None:
            return
        widget = self.ui.viewArea.widget(idx)
        if widget is None:
            self.open_files.set_active_widget(None)
            return

        self.redraw_near(idx)

        self.ui.plotView.setModel(widget.plotModel)
        if widget.plotSelectionModel is not None:
            self.ui.plotView.setSelectionModel(widget.plotSelectionModel)
        '''self.metadataView.setModel(widget.metadataModel)
        if widget.metadataSelectionModel is not None:
            self.metadataView.setSelectionModel(widget.metadataSelectionModel)
        self.update_checkboxes()'''
        self.update_settings(widget)
        self.update_save(widget)
        widget.activate()
        self.open_files.set_active_widget(widget)
    
    def update_save(self, widget=None):
        if widget is None:
            widget = self.ui.viewArea.currentWidget()
        '''if widget:
            self.actionSavePlot.setEnabled(widget.can_save)'''

    def update_settings(self, widget=None):
        if widget is None:
            widget = self.ui.viewArea.currentWidget()
        '''if widget:
            widget.update_settings(self.plotSettingsWidget.values())'''
    
    
    def handler_customize2_button(self):
        self.customize2.show()
    
    
    
    def store_in_file(self): 
        print ("***open file" ) 
        out = open('output.txt','w') 
        print ("file opend")
        
        print ("write in file")
        out.write(str(5*5+9))
        print ("function written")
        print (inspect.getfile(inspect.currentframe()) )# script filename (usually with path)
        print (os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))) # script directory
        out = open('output.txt','w') 
        p = subprocess.Popen(["ls", "-l", "/etc/resolv.conf"], stdout=subprocess.PIPE)
        output, err = p.communicate()
        out.write(p.communicate())
        print ("*** Running ls -l command ***\n", output)
        out.close()
        print ("file closed")
    #added 12/09 open data file as a plot
    def on_open(self):
        filenames = self.get_opennames()
        self.load_files(filenames)   
    def get_opennames(self):
        filenames = QFileDialog.getOpenFileNames(self,
                                                 "Select data file(s)",
                                                 self.last_dir,
                                                 FILE_SELECTOR_STRING)

        if isinstance(filenames, tuple):
            filenames = filenames[0]
        if filenames:
            self.last_dir = os.path.dirname(unicode(filenames[0]))
    def load_files(self, filenames, set_last_dir=True):
        if not filenames:
            return

        #self.update_tabs = self.viewArea.currentWidget() is not None

        self.busy_start()

        if isinstance(filenames[0], ResultSet):
            results = filenames
            titles = self.shorten_titles([r.title for r in results])
        else:
            results = list(filter(None, self.worker_pool.map(results_load_helper,
                                                             map(unicode,
                                                                 filenames))))

            titles = self.shorten_titles([r['title'] for r in results])

        self.focus_new = True

        self.load_queue.extend(zip(results, titles))
        self.load_timer.start()
        print("load_timer.start()") 

        if set_last_dir:
            self.last_dir = os.path.dirname(unicode(filenames[-1]))      
            
        #ResultWidget.show()   
        
    def load_one(self):
        if not self.load_queue:
            self.load_timer.stop()
            print(".111load_timer.stop()")
            return

        r, t = self.load_queue.pop(0)

        widget = self.ui.viewArea.currentWidget()
        print("widget",widget)
        if widget is not None:
            current_plot = widget.current_plot
        else:
            current_plot = None

        try:
            if widget is None or widget.is_active:
                widget = self.add_tab(r, t, current_plot, focus=False)
            else:
                widget.load_results(r, plot=current_plot)
            self.open_files.add_file(widget.results)
        except Exception as e:
            logger.exception("Error while loading data file: '%s'. Skipping.",
                             str(e))

        if not self.load_queue:
            #self.openFilesView.resizeColumnsToContents()
            #self.metadata_column_resize()
            '''if self.update_tabs:
                self.shorten_tabs()'''
            self.load_timer.stop()
            print(".2222load_timer.stop()")
            self.redraw_near()
            self.busy_end()
    
    
                
    def read_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            logging.getLogger().handle(msg)

    def get_last_dir(self):
        if 'savefig.directory' in matplotlib.rcParams:
            return matplotlib.rcParams['savefig.directory']
        return self._last_dir

    def set_last_dir(self, value):
        if 'savefig.directory' in matplotlib.rcParams:
            matplotlib.rcParams['savefig.directory'] = value
        else:
            self._last_dir = value
    last_dir = property(get_last_dir, set_last_dir)

    def read_settings(self):
        settings = QSettings("Flent", "GUI")
        if settings.contains("mainwindow/geometry"):
            geom = settings.value("mainwindow/geometry")
            if hasattr(geom, 'toByteArray'):
                geom = geom.toByteArray()
            self.restoreGeometry(geom)

        if settings.contains("mainwindow/windowState"):
            winstate = settings.value("mainwindow/windowState")
            if hasattr(winstate, 'toByteArray'):
                winstate = winstate.toByteArray()

            version = settings.value("mainwindow/windowStateVersion", 0)
            if hasattr(version, "toInt"):
                version = version.toInt()[0]
            version = int(version)

            if version == WINDOW_STATE_VERSION:
                self.restoreState(winstate)
                self.metadata_visibility()
                self.plot_visibility()
                self.plot_settings_visibility()
                self.open_files_visibility()
            else:
                logger.debug("Discarding old window state (version %d!=%d)",
                             version, WINDOW_STATE_VERSION)

        if settings.contains("open_files/columns"):
            value = settings.value("open_files/columns")
            if hasattr(value, 'toString'):
                value = value.toString()
            self.open_files.restore_columns(value)

        if settings.contains("open_files/column_order"):
            value = settings.value("open_files/column_order")
            if hasattr(value, 'toByteArray'):
                value = value.toByteArray()
            self.openFilesView.horizontalHeader().restoreState(value)
            self.openFilesView.setSortingEnabled(True)

    def closeEvent(self, event):
        # Cleaning up matplotlib figures can take a long time; disable it when
        # the application is exiting.
        for i in range(self.ui.viewArea.count()):
            widget = self.ui.viewArea.widget(i)
            widget.setUpdatesEnabled(False)
            widget.disable_cleanup()
        settings = QSettings("Flent", "GUI")
        settings.setValue("mainwindow/geometry", self.saveGeometry())
        settings.setValue("mainwindow/windowState", self.saveState())
        settings.setValue("mainwindow/windowStateVersion", WINDOW_STATE_VERSION)
        settings.setValue("open_files/columns", self.open_files.save_columns())
        #settings.setValue("open_files/column_order",self.openFilesView.horizontalHeader().saveState())

        self.worker_pool.terminate()

        event.accept()

    def keyPressEvent(self, event):
        widget = self.ui.viewArea.currentWidget()
        text = unicode(event.text())
        if widget and text in ('x', 'X', 'y', 'Y'):
            a = text.lower()
            d = 'in' if a == text else 'out'
            widget.zoom(a, d)
            event.accept()
        else:
            super(performance, self).keyPressEvent(event)

    # Helper functions to update menubar actions when dock widgets are closed
    def plot_visibility(self):
        self.actionPlotSelector.setChecked(not self.plotDock.isHidden())

    def plot_settings_visibility(self):
        self.actionPlotSettings.setChecked(not self.plotSettingsDock.isHidden())

    def metadata_visibility(self):
        self.actionMetadata.setChecked(not self.metadataDock.isHidden())

    def open_files_visibility(self):
        self.actionOpenFiles.setChecked(not self.openFilesDock.isHidden())

    def log_entries_visibility(self):
        self.actionLogEntries.setChecked(not self.logEntriesDock.isHidden())

    def metadata_column_resize(self):
        self.metadataView.resizeColumnToContents(0)

    def update_checkboxes(self):
        for i in range(self.ui.viewArea.count()):
            widget = self.ui.viewArea.widget(i)
            if widget is not None:
                widget.highlight(self.checkHighlight.isChecked())

        self.log_settings(self.checkDebugLog.isChecked(),
                          self.checkExceptionLog.isChecked())

        idx = self.ui.viewArea.currentIndex()
        if idx >= 0:
            self.redraw_near(idx)

    def log_settings(self, debug=False, exceptions=False):
        self.logEntries.setLevel(loggers.DEBUG if debug else loggers.INFO)
        self.logEntries.format_exceptions = exceptions

        if self.new_test_dialog is not None:
            self.new_test_dialog.log_settings(debug, exceptions)

   

    def data_ready(self):
        for s in self.sockets:
            if s.isReadable():
                stream = QDataStream(s)
                filenames = stream.readQStringList()
                self.load_files(filenames)
                self.sockets.remove(s)
                self.raise_()
                self.activateWindow()

    def update_statusbar(self, idx):
        self.statusBar().showMessage(
            self.metadataView.model().data(idx, Qt.StatusTipRole), 1000)          
    #end open data file        
                    
    def abort_test(self):
        if QMessageBox.question(self, "Abort test?",
                                "Are you sure you want to abort "
                                "the current test?",
                                QMessageBox.Yes | QMessageBox.No) \
           != QMessageBox.Yes:
            return

        logger.info("Aborting test.")
        os.kill(self.pid, signal.SIGTERM)
        self.ui.runButton.setEnabled(False)
        self.aborted = True
        logger.debug("Waiting for child process with PID %d to exit.", self.pid)
    
    def reset(self):
        '''self.testConfig.setEnabled(True)'''
        self.ui.runButton.setText("&Run test")
        self.ui.runButton.setDefault(True)
        self.ui.runButton.setEnabled(True)
        self.ui.progressBar.setValue(0)
        self.monitor_timer.stop()
        print ("self.monitor_timer.stop()") 
        self.pid = None
        self.aborted = False

    
    def show(self):
        super(performance, self).show()
        add_log_handler(self.logEntries, replay=False)


    def update_progress(self):
           
        ''''p, s = os.waitpid(self.pid, os.WNOHANG)
        if (p, s) == (0, 0):
            print(p,s)
            if not self.aborted:
                elapsed = time.time() - self.start_time
                print("elapsed",elapsed)
                print("self.start_time",self.start_time)
                print("self.total_time",self.total_time)
                self.ui.progressBar.setValue(100 * elapsed / self.total_time)
        else:
            print("**********************************in the else for loading file")          
            self.reset()
            fn = os.path.join(self.settings.DATA_DIR,
                              self.settings.DATA_FILENAME)
            if os.path.exists(fn):
                
                self.load_files([fn])           '''
        
        if not self.aborted:
                elapsed = time.time() - self.start_time
                #print("elapsed",elapsed)
                #print("self.start_time",self.start_time)
                #print("self.total_time",self.total_time)
                self.ui.progressBar.setValue(100 * elapsed / self.total_time)
                
                fn = os.path.join(self.settings.DATA_DIR,
                              self.settings.DATA_FILENAME)
                #print("befor os.path.exists(fn")
                if os.path.exists(fn):
                    print("in the os.path.exists(fn")
                    print(fn)
                    self.reset()
                    self.load_files([fn])     
                
        else:
            print("**********************************in the else for loading file")          
            self.reset()
                 
         
                    
    def update_plots(self, testname, plotname):
        for i in range(self.ui.viewArea.count()):
            widget = self.ui.viewArea.widget(i)
            if widget and widget.settings.NAME == testname:
                widget.change_plot(plotname)

        idx = self.ui.viewArea.currentIndex()
        if idx >= 0:
            self.redraw_near(idx)
    
    def add_tab(self, results=None, title=None, plot=None, focus=True):
        widget = ResultWidget(self.ui.viewArea, self.settings, self.worker_pool)
        widget.update_start.connect(self.busy_start)
        widget.update_end.connect(self.busy_end)
        widget.update_end.connect(self.update_save)
        widget.plot_changed.connect(self.update_plots)
        widget.name_changed.connect(self.shorten_tabs)
        if results:
            widget.load_results(results, plot)
        if title is None:
            title = widget.title
        idx = self.ui.viewArea.addTab(widget, title)
        if hasattr(widget, "long_title"):
            self.ui.viewArea.setTabToolTip(idx, widget.long_title)
        if focus or self.focus_new:
            self.ui.viewArea.setCurrentWidget(widget)
            self.focus_new = False

        return widget
    
    
            
    def run_or_abort(self):
        if self.pid is None:
            print("run on abort")
            self.run_test()
        else:
            self.abort_test()
         
#RUN TEST PART  
#23/07/2018  
    def run_test(self):
        self.settings.INDEX = str(self.ui.combobox_perf.currentIndex())
        index = str(self.ui.combobox_perf.currentIndex())        
        index = self.ui.combobox_perf.currentIndex()
        if (index == 0):
            test='http'
        elif (index == 1):
            test='ping'
        elif (index == 2):
            test = 'dns'
        
        
        print ("running test")
        print (test)
        
        if hasattr(test, 'toString'):
            test = test.toString()
        host = self.ui.hostName.text()
        print(host)
        path = self.ui.outputDir.text()
        print(path)
        if not test :
            logger.error("You must select a test to run .")
            return
        
        netifaces.interfaces()
        print("netifaces.interfaces()")
        if not host:
            logger.error("You must set a "
                         "hostname to connect to.")
            return
            #host ='eth0'
            
        if not os.path.isdir(path):
            logger.error("Output directory does not exist.")
            return
        
        
        if not (self.ui.test_title.text()):
            
            logger.error("Test title is missing .")
            return
        
        test = unicode(test)
        host = unicode(host)
        path = unicode(path)
        index = unicode(index)
        config = self.settings.config
        
        
        self.log_queue = Queue()
        self.settings=Settings(DEFAULT_SETTINGS).copy()
        self.settings.INPUT = []
        self.settings.BATCH_NAMES = []
        self.settings.HOSTS = [host]
        self.settings.NAME = test
        self.settings.TITLE = unicode(self.ui.test_title.text())
        self.settings.LENGTH = self.ui.testLength.value()
        #self.settings.TITLE = unicode(self.testTitle.text())
        
        self.settings.DATA_DIR = path
        self.settings.STEP_SIZE = 0.2
        self.settings.TEST_PARAMETERS = {}
        #self.settings.EXTENDED_METADATA = self.extendedMetadata.isChecked()
        self.settings.load_test(informational=True)
        self.settings.FORMATTER = "null"
        self.settings.TIME = datetime.utcnow()

        self.settings.DATA_FILENAME = None
        res = resultset.new(self.settings)
        self.settings.DATA_FILENAME = res.dump_filename

        self.total_time = self.settings.TOTAL_LENGTH
        self.start_time = time.time()
        self.settings.config = config
        self.settings.INDEX = index
        

        '''self.testConfig.setEnabled(False)'''
        self.ui.runButton.setText("&Abort test")
        self.ui.runButton.setDefault(False)

        b = batch.new(self.settings)
        print ("this is the famous b")
        print(b)
        if (self.ui.checkBox_NTP.isChecked()):
                print('true tt')
                os.system("ntpdate  0.africa.pool.ntp.org")
                print("ntpdate command executed")
                logger.debug("ntpdate host synchronised")
                
        self.pid = b.fork_and_run(self.log_queue)
        self.monitor_timer.start()
        print ("self.monitor_timer.start()")
        
        ''' 
        self.settings.INDEX = str(self.ui.combobox_perf.currentIndex())
        index = str(self.ui.combobox_perf.currentIndex())
        
        if index == "0" :#user experience selected
            test='http'
            print ("running test")
            print (test)
            
            if hasattr(test, 'toString'):
                test = test.toString()
            host = self.ui.hostName.text()
            print(host)
            path = self.ui.outputDir.text()
            print(path)
            if not test :
                logger.error("You must select a test to run .")
                return
            
            netifaces.interfaces()
            print("netifaces.interfaces()")
            if not host:
                logger.error("You must set a "
                             "hostname to connect to.")
                return
                #host ='eth0'
                
            if not os.path.isdir(path):
                logger.error("Output directory does not exist.")
                return
            
            
            if not (self.ui.test_title.text()):
                
                logger.error("Test title is missing .")
                return
            
            test = unicode(test)
            host = unicode(host)
            path = unicode(path)
            index = unicode(index)
            config = self.settings.config
            
            self.log_queue = Queue()
            self.settings=Settings(DEFAULT_SETTINGS).copy()
            self.settings.INPUT = []
            self.settings.BATCH_NAMES = []
            self.settings.HOSTS = [host]
            self.settings.NAME = test
            self.settings.TITLE = unicode(self.ui.test_title.text())
            self.settings.LENGTH = self.ui.testLength.value()
            #self.settings.TITLE = unicode(self.testTitle.text())
            
            self.settings.DATA_DIR = path
            self.settings.STEP_SIZE = 0.2
            self.settings.TEST_PARAMETERS = {}
            #self.settings.EXTENDED_METADATA = self.extendedMetadata.isChecked()
            self.settings.load_test(informational=True)
            self.settings.FORMATTER = "null"
            self.settings.TIME = datetime.utcnow()
    
            self.settings.DATA_FILENAME = None
            res = resultset.new(self.settings)
            self.settings.DATA_FILENAME = res.dump_filename
    
            self.total_time = self.settings.TOTAL_LENGTH
            self.start_time = time.time()
    
            #self.testConfig.setEnabled(False)
            self.ui.runButton.setText("&Abort test")
            self.ui.runButton.setDefault(False)
    
            b = batch.new(self.settings)
            print ("this is the famous b")
            print(b)
            self.pid = b.fork_and_run(self.log_queue)
            self.monitor_timer.start()
            print ("self.monitor_timer.start()") 
            
        elif index == "1" :
            test='ping'

            print ("running test")
            print (test)
            
            if hasattr(test, 'toString'):
                test = test.toString()
            host = self.ui.hostName.text()
            print(host)
            path = self.ui.outputDir.text()
            print(path)
            if not test :
                logger.error("You must select a test to run .")
                return
            
            netifaces.interfaces()
            print("netifaces.interfaces()")
            if not host:
                logger.error("You must set a "
                             "hostname to connect to.")
                return
                #host ='eth0'
                
            if not os.path.isdir(path):
                logger.error("Output directory does not exist.")
                return
            
            
            if not (self.ui.test_title.text()):
                
                logger.error("Test title is missing .")
                return
            
            test = unicode(test)
            host = unicode(host)
            path = unicode(path)
            index = unicode(index)
            config = self.settings.config
            
            
            self.log_queue = Queue()
            self.settings=Settings(DEFAULT_SETTINGS).copy()
            self.settings.INPUT = []
            self.settings.BATCH_NAMES = []
            self.settings.HOSTS = [host]
            self.settings.NAME = test
            self.settings.TITLE = unicode(self.ui.test_title.text())
            self.settings.LENGTH = self.ui.testLength.value()
            #self.settings.TITLE = unicode(self.testTitle.text())
            
            self.settings.DATA_DIR = path
            self.settings.STEP_SIZE = 0.2
            self.settings.TEST_PARAMETERS = {}
            #self.settings.EXTENDED_METADATA = self.extendedMetadata.isChecked()
            self.settings.load_test(informational=True)
            self.settings.FORMATTER = "null"
            self.settings.TIME = datetime.utcnow()
            self.settings.config = config
            self.settings.INDEX = index
            
            self.settings.DATA_FILENAME = None
            res = resultset.new(self.settings)
            self.settings.DATA_FILENAME = res.dump_filename
    
            self.total_time = self.settings.TOTAL_LENGTH
            self.start_time = time.time()
    
            #self.testConfig.setEnabled(False)
            self.ui.runButton.setText("&Abort test")
            self.ui.runButton.setDefault(False)
    
            b = batch.new(self.settings)
            print ("this is the famous b")
            print(b)
            self.pid = b.fork_and_run(self.log_queue)
            self.monitor_timer.start()
            print ("self.monitor_timer.start()") 
        elif index == "2" :
             
            test = "dns"
            print ("running test")
            print (test)
            
            if hasattr(test, 'toString'):
                test = test.toString()
            host = self.ui.hostName.text()
            print(host)
            path = self.ui.outputDir.text()
            print(path)
            if not test or not host:
                logger.error("You must select a test to run and a "
                             "hostname to connect to.")
                return
            if not os.path.isdir(path):
                logger.error("Output directory does not exist.")
                return
    
            test = unicode(test)
            host = unicode(host)
            path = unicode(path)
            index = unicode(index)
            config = self.settings.config
            
            self.log_queue = Queue()
            self.settings=Settings(DEFAULT_SETTINGS).copy()
            self.settings.INPUT = []
            self.settings.BATCH_NAMES = []
            self.settings.HOSTS = [host]
            self.settings.NAME = test
            self.settings.STEP_SIZE = 1
            self.settings.TEST_PARAMETERS = {}
            self.settings.TITLE = unicode(self.ui.test_title.text())
            self.settings.LENGTH = self.ui.testLength.value()
            self.settings.DATA_DIR = path
            self.settings.load_test(informational=True)
            self.settings.FORMATTER = "null"
            self.settings.TIME = datetime.utcnow()
            self.settings.index = str(self.ui.combobox_perf.currentIndex())
            self.settings.DATA_FILENAME = None
            res = resultset.new(self.settings)
            self.settings.DATA_FILENAME = res.dump_filename

            self.total_time = self.settings.TOTAL_LENGTH
            self.start_time = time.time()
            self.settings.config = config
            self.settings.INDEX = index
            
            #self.testConfig.setEnabled(False)
            self.ui.runButton.setText("&Abort test")
            self.ui.runButton.setDefault(False)
    
            b = batch.new(self.settings)
            
            print ("this is the famous b")
            print(b)
            
            if (self.ui.checkBox_NTP.isChecked()):
                print('true tt')
                os.system("ntpdate  0.africa.pool.ntp.org")
                print("ntpdate command executed")
                logger.debug("ntpdate host synchronised")
        
            self.pid = b.fork_and_run(self.log_queue)
            self.monitor_timer.start()'''   
#END RUN TEST    
    def select_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self,
                                                     "Select output directory",
                                                     self.ui.outputDir.text())
        if directory:
            self.ui.outputDir.setText(directory)
    
    
    def handler_customize_button(self):
        self.customize.show()
    
    def chekboxDisable(self):
        if str(self.ui.combobox_perf.currentText()) == "PPING_Http: http latency test":
            print("disable conbobox")
            self.checkBox_NTP(state=DISABLED)
    #enable and disable checkbox dependent on dropBox Selection   
    def enableConbobox (self):
        index = str(self.ui.combobox_perf.currentIndex())
        #print(index)
        if index == "2" :#user experience selected
            self.ui.checkBox_NTP.setEnabled(True)
            self.ui.trafficsetting_button.setEnabled(True)
            self.ui.setting_button.setEnabled(True)
        else:
            self.ui.checkBox_NTP.setEnabled(False)
            self.ui.trafficsetting_button.setEnabled(False)
            self.ui.setting_button.setEnabled(False)
    
    
class OpenFilesView(QTableView):

    def __init__(self, parent):
        super(OpenFilesView, self).__init__(parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setAlternatingRowColors(True)

        self.setSortingEnabled(True)
        self.sortByColumn(1, Qt.AscendingOrder)

        #self.setHorizontalHeader(OpenFilesHeader(self))

        #self.setContextMenuPolicy(Qt.DefaultContextMenu)

    def remove_column(self, col):
        self.model().removeColumn(col, QModelIndex())

    def close_file(self, row):
        self.model().removeRow(row, QModelIndex())

    def mouseReleaseEvent(self, event):
        # Prevent clicked() from being emitted on right click
        if event.button() == Qt.LeftButton:
            super(OpenFilesView, self).mouseReleaseEvent(event)
        else:
            event.ignore()

    def contextMenuEvent(self, event):
        idx = self.indexAt(event.pos())
        menu = QMenu()

        def opn():
            self.model().activate(idx.row(), True)
        act_opn = QAction("&Open in new tab", menu, triggered=opn)

        sep = QAction(menu)
        sep.setSeparator(True)
        menu.addActions([act_opn, sep])
        menu.addActions(self.horizontalHeader(
        ).column_actions(idx.column(), menu))
        menu.exec_(event.globalPos())
        event.accept()    
        
        
        
'''class OpenFilesHeader(QHeaderView):

    def __init__(self, parent):
        super(OpenFilesHeader, self).__init__(Qt.Horizontal, parent)
        self._parent = parent
        try:
            self.setSectionsMovable(True)
        except AttributeError:
            self.setMovable(True)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)

    def column_actions(self, col, parent):
        actions = []
        if col > 0:
            def rem():
                self._parent.remove_column(col)
            name = self.model().headerData(col, Qt.Horizontal, Qt.DisplayRole)
            actions.append(QAction("&Remove column '%s'" %
                                   name, parent, triggered=rem))

        def add():
            self.add_column(col)
        actions.append(QAction("&Add new column", parent, triggered=add))

        return actions

    def add_column(self, col=None, path=None):
        if col is None:
            col = self.model().columnCount(QModelIndex())
        dialog = AddColumnDialog(self, path)
        if not dialog.exec_() or not dialog.get_path():
            return
        vis_old = self.visualIndex(col)
        self.model().add_column(col + 1, dialog.get_path(), dialog.get_name())
        vis_new = self.visualIndex(col + 1)
        self.moveSection(vis_new, vis_old + 1)
        self._parent.resizeColumnToContents(col + 1)

    def contextMenuEvent(self, event):
        idx = self.logicalIndexAt(event.pos())
        menu = QMenu()
        menu.addActions(self.column_actions(idx, menu))
        menu.exec_(event.globalPos())
        event.accept()
'''
        
'''class AddColumnDialog(getUiClass("addcolumn.ui")):

    def __init__(self, parent, path=None):
        super(AddColumnDialog, self).__init__(parent)

        self.metadataPathEdit.textChanged.connect(self.update_name)
        self.columnNameEdit.textEdited.connect(self.name_entered)
        self.name_entered = False

        if path is not None:
            self.metadataPathEdit.setText(path)

    def name_entered(self):
        self.name_entered = True

    def update_name(self, text):
        if self.name_entered:
            return
        parts = text.split(":")
        self.columnNameEdit.setText(parts[-1])

    def get_path(self):
        return unicode(self.metadataPathEdit.text())

    def get_name(self):
        return unicode(self.columnNameEdit.text())   '''     
        

        
class MetadataView(QTreeView):

    def __init__(self, parent, openFilesView):
        super(MetadataView, self).__init__(parent)
        self.setAlternatingRowColors(True)
        self.setMouseTracking(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.pinned_entries = set()
        self.openFilesView = openFilesView

    def contextMenuEvent(self, event):
        idx = self.indexAt(event.pos())
        menu = QMenu()

        def pin():
            self.add_pin(idx)

        def col():
            self.add_open_files_col(idx)

        def copy():
            self.copy_value(idx)

        menu.addActions([
            QAction("&Pin expanded", menu, triggered=pin),
            QAction("&Add open files column", menu, triggered=col),
            QAction("&Copy value to clipboard", menu, triggered=copy)
        ])
        menu.exec_(event.globalPos())
        event.accept()

    def get_metadata_path(self, idx):
        path = []
        while idx.isValid():
            name = self.model().data(self.model().index(idx.row(),
                                                        0,
                                                        idx.parent()),
                                     Qt.DisplayRole)
            path.insert(0, name or idx.row())
            idx = idx.parent()

        return tuple(path)

    def add_pin(self, idx):
        pin = self.get_metadata_path(idx)
        if pin in self.pinned_entries:
            self.pinned_entries.remove(pin)
        else:
            self.pinned_entries.add(pin)

    def add_open_files_col(self, idx):
        path = self.get_metadata_path(idx)
        self.openFilesView.horizontalHeader().add_column(None,
                                                         ":".join(map(str, path)))

    def copy_value(self, idx):
        val = self.model().data(self.model().index(idx.row(),
                                                   1,
                                                   idx.parent()),
                                Qt.DisplayRole)
        get_clipboard().setText(val)

    def setModel(self, model):
        super(MetadataView, self).setModel(model)
        self.restore_pinned()

    def restore_pinned(self):
        if not self.model():
            return
        for pin in self.pinned_entries:
            parent = QModelIndex()
            for n in pin:
                try:
                    if isinstance(n, int):
                        idx = self.model().index(n, 0, parent)
                    else:
                        idx = self.model().match(self.model().index(
                            0, 0, parent), Qt.DisplayRole, n)[0]
                    self.setExpanded(idx, True)
                    parent = idx
                except IndexError:
                    logger.warning("Could not find pinned entry '%s'.",
                                   ":".join(map(str, pin)))
                    break
                except Exception as e:
                    logger.exception("Restoring pin '%s' failed: %s.",
                                     ":".join(map(str, pin)), e)
                    break
     
class TestConfguration (getUiClass("TestConfiguration.ui")):
    def __init__(self):
        self.configfile="config_performanceTest.ini"
        super(TestConfguration, self).__init__()
        
        Ui_MainWindow, QtBaseClass = uic.loadUiType(os.path.join(DATA_DIR, 'ui', "TestConfiguration.ui"))
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
            #set the add icons
        add_new_host_icon = QtGui.QIcon()
        add_new_host_icon.addPixmap(QtGui.QPixmap("ui/static/add.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.add_new_host.setIcon(add_new_host_icon)
        
        #set the refresh icons 
        refresh_icon = QtGui.QIcon()
        refresh_icon.addPixmap(QtGui.QPixmap("ui/static/refresh.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.refresh_button.setIcon(refresh_icon)
        ## add a handler to cancel button
        self.ui.cancel_button.clicked.connect(self.handler_cancel_button)
            ## add a handler to ok button
        self.ui.ok_button.clicked.connect(self.handler_ok_button)
        ## add new host button handler
        self.ui.add_new_host.clicked.connect(self.handler_add_new_host_button)
        self.configfile="config_performanceTest.ini"
        self.set_config_table()
      
    
        
    
    
    def handler_ok_button(self):
        number = self.get_config_hosts_number()
        allRows = self.ui.tableWidget.rowCount()
        #print(allRows)
        #print("Ok button clicked")
        configuration = []
        for row in range(0,allRows):
            twi0 = self.ui.tableWidget.item(row,0).text()
            #print(twi0)
            if twi0 in configuration :
                QMessageBox.warning(self, "Message", "Invalid data input: 2 or more hosts are having the same host_name") 
                return 0 
            else :
                configuration.append(twi0)
        
                
        config = ConfigParser()
        for row in range(0,allRows): 
            try :
                config[self.ui.tableWidget.item(row,0).text()] = {'Traffic': self.ui.tableWidget.item(row,0).text(),'DSCP_Value': self.ui.tableWidget.item(row,1).text(),'Protocol': self.ui.tableWidget.item(row,2).text(),'Bandwidth': self.ui.tableWidget.item(row,3).text(),'Option': self.ui.tableWidget.item(row,5).text()}
            except :
                config.add_section(self.ui.tableWidget.item(row,0).text())
                config.set(self.ui.tableWidget.item(row,0).text(), 'Traffic', self.ui.tableWidget.item(row,0).text())
                config.set(self.ui.tableWidget.item(row,0).text(), 'DSCP_Value', self.ui.tableWidget.item(row,1).text())
                config.set(self.ui.tableWidget.
                           item(row,0).text(), 'Protocol', self.ui.tableWidget.item(row,2).text())
                config.set(self.ui.tableWidget.item(row,0).text(), 'Bandwidth', self.ui.tableWidget.item(row,3).text())
                #config.set(self.ui.tableWidget.item(row,0).text(), 'Option', self.ui.tableWidget.item(row,4).text())
        
        with open('config/'+self.configfile, 'w') as configfile:
            config.write(configfile)
        self.close()

    def handler_cancel_button(self):
        #print("closing..")
        self.close()
        
    def handler_add_new_host_button(self):
        j= self.ui.tableWidget.rowCount()
        self.ui.tableWidget.setRowCount(j+1)
        for k in range(0,8):
            if k == 0 :
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 1 : 
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 2 : 
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 3 :
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
    
            if k == 4 : 
                self.btn = QPushButton('Delete')
                self.btn.setObjectName("install")
                self.ui.tableWidget.setCellWidget(j,k, self.btn)
                self.btn.clicked.connect(self.handler_delete_button(j))
           

    
            
    def handler_delete_button(self, index):
        def calluser():
            self.ui.tableWidget.removeRow(index)
        return calluser            
    def set_config_table(self):
        ## Get the config file 
        config = self.get_config_data()
        #print(config)
        # Set Horizontal Header
        self.ui.tableWidget.setColumnCount(5)
        self.ui.tableWidget.setHorizontalHeaderLabels(['Traffic','DSCP value','Protocol','Bandwidth \n (Mbit/s)','Option'])
        
        headerHorizontal = self.ui.tableWidget.horizontalHeader()
        headerHorizontal.setStretchLastSection(True)      
        #headerHorizontal.resizeColumnsToContents()  def get_config_data(self):
        cfg = ConfigParser()
        cfg.read('config/'+self.configfile)
        config = []
        for section in cfg.sections():# IPC socket parameters

            x = {}
            for name, value in cfg.items(section):
                x[name] = value
            config.append(x)
        #return (config)

        # Set Vertical Header
        self.ui.tableWidget.setRowCount(self.get_config_hosts_number())

        # Print the keys and values
        j = 0
        k = 0
        print(config)
        for i in config:
            for k in range(0,5):
                if k == 0 :
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"traffic")))
                    print(get_value_from_json(i,"traffic"))
                if k == 1 : 
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"dscp_value")))
                if k == 2 : 
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"protocol")))
                if k == 3 :
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"bandwidth")))
                
                if k == 4 :
                    #
                    self.btn = QPushButton('Delete')
                    self.btn.setObjectName("Delete")
                    self.ui.tableWidget.setCellWidget(j,k, self.btn)
                    self.btn.clicked.connect(self.handler_delete_button(j))
            

            j = j+1
    
    def get_config_data(self):
        cfg = ConfigParser()
        cfg.read('config/'+self.configfile)
        config = []
        for section in cfg.sections():
            x = {}
            for name, value in cfg.items(section):
                x[name] = value
            config.append(x)
        return (config)
    
    def get_config_hosts_number(self):
        cfg = ConfigParser()
        cfg.read('config/'+self.configfile)
        i=0
        for section in cfg.sections():
            i=i+1
        return i  


#traffic rimeh
class TrafficConfguration (getUiClass("TrafficConfiguration.ui")):
    def __init__(self):
        self.configfile1="configtraffic.ini"
        super(TrafficConfguration, self).__init__()
        
        Ui_MainWindow, QtBaseClass = uic.loadUiType(os.path.join(DATA_DIR, 'ui', "TrafficConfiguration.ui"))
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings
            #set the add icons
        add_new_host_icon = QtGui.QIcon()
        add_new_host_icon.addPixmap(QtGui.QPixmap("ui/static/add.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.add_new_host.setIcon(add_new_host_icon)
        
        #set the refresh icons 
        refresh_icon = QtGui.QIcon()
        refresh_icon.addPixmap(QtGui.QPixmap("ui/static/refresh.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.refresh_button.setIcon(refresh_icon)
        ## add a handler to cancel button
        self.ui.cancel_button.clicked.connect(self.handler_cancel_button)
            ## add a handler to ok button
        self.ui.ok_button.clicked.connect(self.handler_ok_button)
        ## add new host button handler
        self.ui.add_new_host.clicked.connect(self.handler_add_new_host_button)
        self.configfile1="configtraffic.ini"
        
        self.set_config_table()
      
    
    def handler_ok_button(self):
        number = self.get_config_hosts_number()
        allRows = self.ui.tableWidget.rowCount()
        configuration = []
        for row in range(0,allRows):
            twi0 = self.ui.tableWidget.item(row,0).text()
            if twi0 in configuration :
                QMessageBox.warning(self, "Message", "Invalid data input: 2 or more hosts are having the same host_name") 
                return 0 
            else :
                configuration.append(twi0)
          
        config1 = ConfigParser()
        for row in range(0,allRows): 
            try :
                config1[self.ui.tableWidget.item(row,0).text()] = {'Traffic': self.ui.tableWidget.item(row,0).text(),'Port': self.ui.tableWidget.item(row,1).text(),'Buffer_length': self.ui.tableWidget.item(row,2).text(),'Number \n of  streams': self.ui.tableWidget.item(row,3).text(),'Protocol': self.ui.tableWidget.item(row,4).text(),'Bandwidth': self.ui.tableWidget.item(row,5).text(),'Option': self.ui.tableWidget.item(row,6).text()}
            except :
                config1.add_section(self.ui.tableWidget.item(row,0).text())
                config1.set(self.ui.tableWidget.item(row,0).text(), 'Traffic', self.ui.tableWidget.item(row,0).text())
                config1.set(self.ui.tableWidget.item(row,0).text(), 'Port', self.ui.tableWidget.item(row,1).text())
                config1.set(self.ui.tableWidget.item(row,0).text(), 'Buffer_length', self.ui.tableWidget.item(row,2).text())
                config1.set(self.ui.tableWidget.item(row,0).text(), 'Number_of_streams', self.ui.tableWidget.item(row,3).text())
                config1.set(self.ui.tableWidget.item(row,0).text(), 'Protocol', self.ui.tableWidget.item(row,4).text())
                config1.set(self.ui.tableWidget.item(row,0).text(), 'Bandwidth', self.ui.tableWidget.item(row,5).text())
        with open('config/'+self.configfile1, 'w') as configfile1:
            config1.write(configfile1)
        self.close()

    def handler_cancel_button(self):
        self.close()
                
    def handler_add_new_host_button(self):
        j= self.ui.tableWidget.rowCount()
        self.ui.tableWidget.setRowCount(j+1)
        for k in range(0,7):
            if k == 0 :
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 1 : 
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 2 : 
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 3 :
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 4 :
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 5 :
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 6 : 
                self.btn = QPushButton('Delete')
                self.btn.setObjectName("install")
                self.ui.tableWidget.setCellWidget(j,k, self.btn)
                self.btn.clicked.connect(self.handler_delete_button(j))
           
    def handler_delete_button(self, index):
        def calluser():
            self.ui.tableWidget.removeRow(index)
        return calluser   
             
    def set_config_table(self):
        ## Get the config file 
        config1 = self.get_config_data()
        self.ui.tableWidget.setColumnCount(7) 
        self.ui.tableWidget.setHorizontalHeaderLabels(['Traffic','Port','Buffer length','Number of \n streams','Protocol','Bandwidth \n (Mbit/S)','Option'])
        
        headerHorizontal = self.ui.tableWidget.horizontalHeader()
        headerHorizontal.setStretchLastSection(True)      
        cfg = ConfigParser()
        cfg.read('config/'+self.configfile1)
        config1 = []
        for section in cfg.sections():# IPC socket parameters

            x = {}
            for name, value in cfg.items(section):
                x[name] = value
            config1.append(x)
        self.ui.tableWidget.setRowCount(self.get_config_hosts_number())

        # Print the keys and values
        j = 0
        k = 0
        self.settings.config = config1
        print("lala:", self.settings.config)
        for i in config1:
            for k in range(0,7):
                if k == 0 :
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"traffic")))
                if k == 1 : 
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"port")))
                if k == 2 : 
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"buffer_length")))
                if k == 3 :
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"number_of_streams")))
                if k == 4 :
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"protocol")))
                if k == 5 :
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"bandwidth")))    
                if k == 6 :
                    self.btn = QPushButton('Delete')
                    self.btn.setObjectName("Delete")
                    self.ui.tableWidget.setCellWidget(j,k, self.btn)
                    self.btn.clicked.connect(self.handler_delete_button(j))
            j = j+1 
            
    def get_config_data(self):
        cfg = ConfigParser()
        cfg.read('config/'+self.configfile1)
        config1 = []
        for section in cfg.sections():
            x = {}
            for name, value in cfg.items(section):
                x[name] = value
            config1.append(x)
        return (config1)
    
    def get_config_hosts_number(self):
        cfg = ConfigParser()
        cfg.read('config/'+self.configfile1)
        i=0
        for section in cfg.sections():
            i=i+1
        return i  
def check_running(settings):
    """Check for a valid socket of an already running instance, and if so,
    connect to it and send the input file names."""
    if settings.NEW_GUI_INSTANCE or mswindows:
        return False

    files = os.listdir(SOCKET_DIR)
    for f in files:
        if f.startswith(SOCKET_NAME_PREFIX):
            try:
                pid = int(f.split("-")[-1])
                os.kill(pid, 0)
                logger.info(
                    "Found a running instance with pid %d. "
                    "Trying to connect... ", pid)
                # Signal handler did not raise an error, so the pid is running.
                # Try to connect
                sock = QLocalSocket()
                sock.connectToServer(os.path.join(
                    SOCKET_DIR, f), QIODevice.WriteOnly)
                if not sock.waitForConnected(1000):
                    continue

                # Encode the filenames as a QStringList and pass them over the
                # socket
                block = QByteArray()
                stream = QDataStream(block, QIODevice.WriteOnly)
                stream.setVersion(QDataStream.Qt_4_0)
                stream.writeQStringList([os.path.abspath(f)
                                         for f in settings.INPUT])
                sock.write(block)
                ret = sock.waitForBytesWritten(1000)
                sock.disconnectFromServer()

                # If we succeeded in sending stuff, we're done. Otherwise, if
                # there's another possibly valid socket in the list we'll try
                # again the next time round in the loop.
                if ret:
                    logger.info("Success!\n")
                    return True
                else:
                    logger.info("Error!\n")
            except (OSError, ValueError):
                # os.kill raises OSError if the pid does not exist
                # int() returns a ValueError if the pid is not an integer
                pass
    return False


class QPlainTextLogger(loggers.Handler):

    def __init__(self, parent, level=logging.NOTSET, widget=None,
                 statusbar=None, timeout=5000):

        super(QPlainTextLogger, self).__init__(level=level)

        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)

        self.widget = widget or QPlainTextEdit(parent)
        self.widget.setFont(font)
        self.widget.setReadOnly(True)

        self.statusbar = statusbar
        self.timeout = timeout

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)

        if self.statusbar:
            self.statusbar.showMessage(record.message, self.timeout)

    def write(self, p):
        pass


#12/09 plot
class PlotModel(QStringListModel):

    def __init__(self, parent, plots):
        QStringListModel.__init__(self, parent)

        self.keys = list(plots.keys())

        strings = []
        for k, v in plots.items():
            strings.append("%s (%s)" % (k, v['description']))
        self.setStringList(strings)

    def index_of(self, plot):
        return self.index(self.keys.index(plot))

    def name_of(self, idx):
        return self.keys[idx.row()]

class TreeItem(object):

    def __init__(self, parent, name, value):
        self.parent = parent
        self.name = name
        self.children = []

        if isinstance(value, list):
            self.value = ""
            for v in value:
                self.children.append(TreeItem(self, "", v))
        elif isinstance(value, dict):
            self.value = ""
            for k, v in sorted(value.items()):
                self.children.append(TreeItem(self, k, v))
        else:
            self.value = value
            self.children = []

    def __len__(self):
        return len(self.children)
class MetadataModel(QAbstractItemModel):

    header_names = [u"Name", u"Value"]

    def __init__(self, parent, datadict):
        QAbstractItemModel.__init__(self, parent)
        self.root = TreeItem(None, "root", datadict)

    def columnCount(self, parent):
        return 2

    def rowCount(self, parent):
        if parent.isValid():
            return len(parent.internalPointer())
        return len(self.root)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Vertical or role != Qt.DisplayRole:
            return None
        return self.header_names[section]

    def data(self, idx, role=Qt.DisplayRole):
        if role not in (Qt.DisplayRole, Qt.StatusTipRole, Qt.ToolTipRole):
            return None

        item = idx.internalPointer()
        if role in (Qt.StatusTipRole, Qt.ToolTipRole):
            if item.name:
                return "%s: %s" % (item.name, item.value)
            else:
                return item.value
        if idx.column() == 0:
            return item.name
        elif idx.column() == 1:
            return unicode(item.value)

    def parent(self, idx):
        item = idx.internalPointer()
        if item is None or item.parent in (None, self.root):
            return QModelIndex()
        parent = item.parent
        row = parent.parent.children.index(parent)
        return self.createIndex(row, 0, parent)

    def index(self, row, column, parent):
        item = parent.internalPointer()
        if item is None:
            item = self.root
        return self.createIndex(row, column, item.children[row])

class UpdateDisabler(object):

    def __init__(self, widget):
        self.widget = widget

    def __enter__(self):
        self.widget.setUpdatesEnabled(False)

    def __exit__(self, *ignored):
        self.widget.setUpdatesEnabled(True)
        self.widget.update()

class FigureManager(matplotlib.backend_bases.FigureManagerBase):
    def __init__(self, widget, canvas):
        super(FigureManager, self).__init__(canvas, 0)
        self.widget = widget

    def get_window_title(self):
        return self.widget.title
    
class ResultWidget(getUiClass("resultwidget.ui")):

    update_start = pyqtSignal()
    update_end = pyqtSignal()
    plot_changed = pyqtSignal('QString', 'QString')
    new_plot = pyqtSignal()
    name_changed = pyqtSignal()
    default_title = "New tab"

    def __init__(self, parent, settings, worker_pool):
        super(ResultWidget, self).__init__(parent)
        self.results = None
        self.settings = settings.copy()
        self.dirty = True
        self.settings.OUTPUT = "-"

        self.extra_results = []
        self.title = self.default_title

        self.plotModel = None
        self.plotSelectionModel = None
        self.metadataModel = None
        self.metadataSelectionModel = None
        self.toolbar = None
        self.plotter = None
        self.canvas = None
        self.needs_resize = False

        self.new_plot.connect(self.get_plotter)
        self.async_fig = None
        self.async_timer = QTimer(self)
        self.async_timer.setInterval(100)
        self.async_timer.timeout.connect(self.get_plotter)

        self.worker_pool = worker_pool

    @property
    def is_active(self):
        return self.results is not None

    def init_plotter(self):

        if not self.results:
            return

        try:
            self.plotter = plotters.new(self.settings)
        except Exception as e:
            logger.exception("Plot '%s' failed: %s. "
                             "Falling back to default plot '%s'.",
                             self.settings.PLOT, e,
                             self.settings.DEFAULTS['PLOT'])

            self.settings.PLOT = self.settings.DEFAULTS['PLOT']
            self.plotter = plotters.new(self.settings)

        if self.settings.GUI_NO_DEFER:
            self.redraw()

    def init_canvas(self):

        self.canvas = FigureCanvas(self.plotter.figure)
        self.canvas.setParent(self.graphDisplay)
        self.toolbar = NavigationToolbar(self.canvas, self.graphDisplay)
        self.manager = FigureManager(self, self.canvas)

        vbl = QVBoxLayout()
        vbl.addWidget(self.canvas)
        vbl.addWidget(self.toolbar)
        self.graphDisplay.setLayout(vbl)

    def has(self, resultset):
        return resultset in chain([self.results], self.extra_results)

    def load_results(self, results, plot=None):
        if isinstance(results, LoadedResultset):
            self.results = results['results']
            self.settings.DEFAULTS = results['defaults']
            self.settings.DATA_SETS = results['data_sets']
            self.settings.PLOTS = results['plots']
            self.settings.DESCRIPTION = results['description']
            self.settings.update_defaults()
        elif isinstance(results, ResultSet):
            self.results = results
        else:
            self.results = ResultSet.load_file(unicode(results))
            self.settings.compute_missing_results(self.results)

        if plot and plot in self.settings.PLOTS:
            self.settings.PLOT = plot

        self.settings.update(self.results.meta())

        if not self.settings.PLOTS:
            self.settings.load_test(informational=True)

        self.title = self.results.title
        self.long_title = self.results.long_title

        self.init_plotter()

        self.plotModel = PlotModel(self, self.settings.PLOTS)
        self.plotSelectionModel = QItemSelectionModel(self.plotModel)
        self.plotSelectionModel.setCurrentIndex(
            self.plotModel.index_of(self.settings.PLOT),
            QItemSelectionModel.SelectCurrent)
        self.plotSelectionModel.currentChanged.connect(self.change_plot)

        self.metadataModel = MetadataModel(self, self.results.meta())
        self.metadataSelectionModel = QItemSelectionModel(self.metadataModel)

        return True

    def disconnect_all(self):
        for s in (self.update_start, self.update_end, self.plot_changed):
            s.disconnect()

    def disable_cleanup(self):
        if self.plotter is not None:
            self.plotter.disable_cleanup = True

    def load_files(self, filenames):
        added = 0
        for f in filenames:
            if self.add_extra(ResultSet.load_file(unicode(f))):
                self.update(False)
                added += 1
        self.redraw()
        return added

    def add_extra(self, resultset):
        if self.results is None:
            return self.load_results(resultset)
        if resultset in self.extra_results:
            return False
        if resultset.meta('NAME') == self.settings.NAME:
            self.extra_results.append(resultset)
            self.update()
            return True
        return False

    def remove_extra(self, resultset):
        if resultset not in self.extra_results:
            if resultset == self.results and self.extra_results:
                self.results = self.extra_results.pop(0)
                self.update()
                return True
            return False
        self.extra_results.remove(resultset)
        self.update()
        return True

    def clear_extra(self):
        self.extra_results = []
        self.update()

    @property
    def can_save(self):
        # Check for attribute to not crash on a matplotlib version that does not
        # have the save action.
        return hasattr(self.toolbar, 'save_figure')

    def save_plot(self):
        if self.can_save:
            self.toolbar.save_figure()

    def highlight(self, val=None):
        if val is not None and val != self.settings.HOVER_HIGHLIGHT:
            self.settings.HOVER_HIGHLIGHT = val
            self.update()
        return self.settings.HOVER_HIGHLIGHT

    def zoom(self, axis, direction='in'):
        if self.plotter:
            self.plotter.zoom(axis, direction)

    def update_settings(self, values):
        if not self.results:
            t = self.default_title
        elif values['OVERRIDE_TITLE']:
            t = "%s - %s" % (self.results.meta('NAME'), values['OVERRIDE_TITLE'])
        else:
            t = self.results.title

        if t != self.title:
            self.title = t
            self.name_changed.emit()

        if self.settings.update(values):
            self.update()

    def change_plot(self, plot_name):
        if not self.plotter:
            return
        if isinstance(plot_name, QModelIndex):
            plot_name = self.plotModel.name_of(plot_name)
        plot_name = unicode(plot_name)
        if plot_name != self.settings.PLOT and plot_name in self.settings.PLOTS:
            self.settings.PLOT = plot_name
            self.plotSelectionModel.setCurrentIndex(
                self.plotModel.index_of(self.settings.PLOT),
                QItemSelectionModel.SelectCurrent)
            self.plot_changed.emit(self.settings.NAME, self.settings.PLOT)
            self.update()
            return True
        return False

    @property
    def current_plot(self):
        if not self.is_active:
            return None
        return self.settings.PLOT

    def updates_disabled(self):
        return UpdateDisabler(self)

    def update(self, redraw=True):
        self.dirty = True
        if redraw and ((self.isVisible() and self.updatesEnabled()) or
                       self.settings.GUI_NO_DEFER):
            self.redraw()

    def activate(self):
        self.get_plotter()

        if self.async_fig:
            self.async_timer.start()

        if not self.canvas:
            return

        if self.needs_resize:
            self.canvas.resizeEvent(QResizeEvent(self.canvas.size(),
                                                 self.canvas.size()))
            self.needs_resize = False

        try:
            self.canvas.blit(self.canvas.figure.bbox)
        except AttributeError:
            pass

        # Simulate a mouse move event when the widget is activated. This ensures
        # that the interactive plot highlight will get updated correctly.
        pt = self.canvas.mapFromGlobal(QCursor.pos())
        evt = QMouseEvent(QEvent.MouseMove, pt, Qt.NoButton,
                          Qt.NoButton, Qt.NoModifier)
        self.canvas.mouseMoveEvent(evt)

    def redraw(self):
        if not self.dirty or not self.is_active:
            return
        self.settings.SCALE_MODE=False
        if self.settings.SCALE_MODE:
            self.settings.SCALE_DATA = self.extra_results
            res = [self.results]
        else:
            self.settings.SCALE_DATA = []
            res = [self.results] + self.extra_results

        self.async_fig = self.worker_pool.apply_async(
            plotters.draw_worker,
            (self.settings, res),
            callback=self.recv_plot)

        if self.isVisible():
            self.async_timer.start()

        self.plotter.disconnect_callbacks()

        self.dirty = False
        self.setCursor(Qt.WaitCursor)

    def recv_plot(self, fig):
        self.new_plot.emit()

    def get_plotter(self):
        if not self.async_fig or not self.async_fig.ready():
            return

        try:
            fig = self.async_fig.get()

            self.plotter = fig

            if not self.canvas:
                self.init_canvas()
            else:
                self.canvas.figure = self.plotter.figure
                self.plotter.figure.set_canvas(self.canvas)

            self.plotter.connect_interactive()

            if self.isVisible():
                self.canvas.resizeEvent(QResizeEvent(self.canvas.size(),
                                                     self.canvas.size()))
            else:
                self.needs_resize = True

        except Exception as e:
            logger.exception("Aborting plotting due to error: %s", str(e))
        finally:
            self.async_fig = None
            self.async_timer.stop()
            self.setCursor(Qt.ArrowCursor)
            self.update_end.emit()

    def setCursor(self, cursor):
        super(ResultWidget, self).setCursor(cursor)
        if self.canvas:
            self.canvas.setCursor(cursor)
        if self.toolbar:
            self.toolbar.setCursor(cursor)
            
    def show(self):
        super(ResultWidget, self).show()
        add_log_handler(self.logEntries, replay=False)
        
##########################################################################################################

#ahmed_test
class wmm_test(getUiClass("wmmTests.ui")):   
    def __init__(self):
        self.configfile="config_WMM_test.ini"
        super(wmm_test, self).__init__()
       
        Ui_MainWindow, QtBaseClass = uic.loadUiType(os.path.join(DATA_DIR, 'ui', "wmmTests.ui"))
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        setting_icon1 = QtGui.QIcon()
        setting_icon1.addPixmap(QtGui.QPixmap("ui/static/configure.jpg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
        self.ui.setting_button.setIcon(setting_icon1)

        self.ui.setting_button.clicked.connect(self.handler_customize_button)
        self.customize = config_wmmTest()
        
    def handler_customize_button(self):
        self.customize.show()

class config_wmmTest (getUiClass("Wmm_Configuration.ui")):
    def __init__(self):
        self.configfile="config_WMM_test.ini"
        super(config_wmmTest, self).__init__()
        
        Ui_MainWindow, QtBaseClass = uic.loadUiType(os.path.join(DATA_DIR, 'ui', "Wmm_Configuration.ui"))
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
            #set the add icons
        add_new_host_icon = QtGui.QIcon()
        add_new_host_icon.addPixmap(QtGui.QPixmap("ui/static/add.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.add_new_host.setIcon(add_new_host_icon)
        
         ## add a handler to cancel button
        self.ui.cancel_button.clicked.connect(self.handler_cancel_button)
            ## add a handler to ok button
        self.ui.ok_button.clicked.connect(self.handler_ok_button)
        ## add new host button handler
        self.ui.add_new_host.clicked.connect(self.handler_add_new_host_button)
        self.set_config_table()
        
        
      
    
        
    
    
    def handler_ok_button(self):
        number = self.get_config_hosts_number()
        allRows = self.ui.tableWidget.rowCount()
        #print(allRows)
        #print("Ok button clicked")
        configuration = []
        for row in range(0,allRows):
            twi0 = self.ui.tableWidget.item(row,0).text()
            #print(twi0)
            if twi0 in configuration :
                QMessageBox.warning(self, "Message", "Invalid data input: 2 or more hosts are having the same host_name") 
                return 0 
            else :
                configuration.append(twi0)
        
                
        config = ConfigParser()
        for row in range(0,allRows): 
            try :
                config[self.ui.tableWidget.item(row,0).text()] = {'Traffic': self.ui.tableWidget.item(row,0).text(),'DSCP_Value': self.ui.tableWidget.item(row,1).text(),'Protocol': self.ui.tableWidget.item(row,2).text(),'Option': self.ui.tableWidget.item(row,3).text()}
            except :
                config.add_section(self.ui.tableWidget.item(row,0).text())
                config.set(self.ui.tableWidget.item(row,0).text(), 'Traffic', self.ui.tableWidget.item(row,0).text())
                config.set(self.ui.tableWidget.item(row,0).text(), 'DSCP_Value', self.ui.tableWidget.item(row,1).text())
                config.set(self.ui.tableWidget.item(row,0).text(), 'Protocol', self.ui.tableWidget.item(row,2).text())
                #config.set(self.ui.tableWidget.item(row,0).text(), 'Option', self.ui.tableWidget.item(row,4).text())
        
        with open('config/'+self.configfile, 'w') as configfile:
            config.write(configfile)
        self.close()

    def handler_cancel_button(self):
        #print("closing..")
        self.close()
        
    def handler_add_new_host_button(self):
        j= self.ui.tableWidget.rowCount()
        self.ui.tableWidget.setRowCount(j+1)
        for k in range(0,8):
            if k == 0 :
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 1 : 
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 2 : 
                self.ui.tableWidget.setItem(j,k, QTableWidgetItem(""))
            if k == 3 :
                self.btn = QPushButton('Delete')
                self.btn.setObjectName("install")
                self.ui.tableWidget.setCellWidget(j,k, self.btn)
                self.btn.clicked.connect(self.handler_delete_button(j))
           

    
            
    def handler_delete_button(self, index):
        def calluser():
            self.ui.tableWidget.removeRow(index)
        return calluser            
    def set_config_table(self):
        ## Get the config file 
        config = self.get_config_data()
        #print(config)
        # Set Horizontal Header
        self.ui.tableWidget.setColumnCount(4)
        self.ui.tableWidget.setHorizontalHeaderLabels(['Traffic','DSCP value','Protocol','Option'])
        
        headerHorizontal = self.ui.tableWidget.horizontalHeader()
        headerHorizontal.setStretchLastSection(True)      
        #headerHorizontal.resizeColumnsToContents()  def get_config_data(self):
        cfg = ConfigParser()
        cfg.read('config/'+self.configfile)
        config = []
        for section in cfg.sections():
            x = {}
            for name, value in cfg.items(section):
                x[name] = value
            config.append(x)
        #return (config)

        # Set Vertical Header
        self.ui.tableWidget.setRowCount(self.get_config_hosts_number())

        # Print the keys and values
        j = 0
        k = 0
        print(config)
        for i in config:
            for k in range(0,5):
                if k == 0 :
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"traffic")))
                    print(get_value_from_json(i,"traffic"))
                if k == 1 : 
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"dscp_value")))
                if k == 2 : 
                    self.ui.tableWidget.setItem(j,k, QTableWidgetItem(get_value_from_json(i,"protocol")))
                if k == 3 :
                    self.btn = QPushButton('Delete')
                    self.btn.setObjectName("Delete")
                    self.ui.tableWidget.setCellWidget(j,k, self.btn)
                    self.btn.clicked.connect(self.handler_delete_button(j))
            

            j = j+1
    
    def get_config_data(self):
        cfg = ConfigParser()
        cfg.read('config/'+self.configfile)
        config = []
        for section in cfg.sections():
            x = {}
            for name, value in cfg.items(section):
                x[name] = value
            config.append(x)
        return (config)
    
    def get_config_hosts_number(self):
        cfg = ConfigParser()
        cfg.read('config/'+self.configfile)
        i=0
        for section in cfg.sections():
            i=i+1
        return i   
##########################################################################################################
       

__all__ = ['run_gui']
    
def run_gui(settings):
    if check_running(settings):
        return 0
    print("USE_MARKERS",settings.USE_MARKERS)
    print("LOAD_MATPLOTLIBRC",settings.LOAD_MATPLOTLIBRC)
    plotters.init_matplotlib("-", settings.USE_MARKERS,
                             settings.LOAD_MATPLOTLIBRC)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    # Start up the Qt application and exit when it does
    app = QApplication(sys.argv[:1])
    mainwindow = MainWindow(settings)
    mainwindow.center()
    mainwindow.show()
    sys.exit(app.exec_())
    

