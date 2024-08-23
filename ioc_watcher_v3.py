#author: Adi
#version: 02-23-2024 20:33

import os
import sys
import epics
from meme import names, archive
import pandas as pd
from datetime import datetime, timedelta

import pydm
from pydm import Display
from pydm.widgets.label import PyDMLabel
from pydm.widgets.base import PyDMWidget
from pydm.widgets.channel import PyDMChannel

from PyQt5.QtWidgets import QApplication, QMainWindow

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QGridLayout, QWidget, QProgressBar, QTableView, QHeaderView, QVBoxLayout, QTableWidgetItem, QStyledItemDelegate, QStyleOptionViewItem, QStyle, QSpinBox
from PyQt5.QtCore import Qt, QTimer, QModelIndex, QAbstractTableModel
from PyQt5.QtGui import QColor, QFont, QPainter

class TableModel(QAbstractTableModel):
  
  def __init__(self, data, headers):
    super().__init__()
    self._data = data
    self._headers = headers
    
  def rowCount(self, parent=QModelIndex()):
    return len(self._data)
  
  def columnCount(self, parent=QModelIndex()):
    return len(self._headers)
  
  def data(self, index, role=Qt.DisplayRole):
    if role == Qt.DisplayRole:
      return str(self._data[index.row()][index.column()])

  def headerData(self, section, orientation, role=Qt.DisplayRole):
    if orientation == Qt.Horizontal and role == Qt.DisplayRole:
      return self._headers[section]
    return None
  
  def sort(self, column, order=Qt.AscendingOrder):
    self.layoutAboutToBeChanged.emit()
    self._data = sorted(self._data, key=lambda x: x[column], reverse=order==Qt.DescendingOrder)
    self.layoutChanged.emit()

class IOC_watcher(Display):
  
  def __init__(self, parent=None, args=None):
    super(IOC_watcher, self).__init__(parent=parent, args=args)
    self.timer = QTimer(self)
    self.timer.timeout.connect(self.update_data)
    self.timer.start(5000)
    
    self.table_model = TableModel([], ["Date", "IOC"])
    self.ui.tableView.setModel(self.table_model)
    self.ui.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    self.ui.tableView.setSortingEnabled(True)
    
    self.ui.tableView.setColumnWidth(0,300)
    self.ui.tableView.setColumnWidth(1,300)
    
  def ui_filename(self):
    return 'ioc_watcher_v3.ui'

  def update_data(self):
    df = pd.DataFrame(epics.caget_many(names.list_pvs("%IOC%:HEARTBEATSUM")))
    df_names = pd.DataFrame(names.list_pvs("%IOC%:HEARTBEATSUM"))
    absent = df[df[0] == 2]
    self.bad_iocs = df_names.loc[absent.index]
    
    self.update_table(df, df_names)
    self.update_progress_bar(df)
    
  def update_table(self, df, df_names):
    data = []
    days_ago = self.ui.spinBox.value()
    
    for index in range(len(self.bad_iocs.values)):
      item_text = self.bad_iocs.values[index][0].replace(':HEARTBEATSUM', '')
      try:
        temp = archive.get_dataframe(self.bad_iocs.values[index][0], from_time = "100 day ago", to_time = "now")
        temp['diff'] = temp.diff()
        temp = temp[temp['diff'] != 0]  # removes all zeros (no change) and gives last time the status changed as the bottom row
        temp = temp.dropna()
        timestamp_str = (temp.index[-1]).to_pydatetime(warn=False).strftime("%m/%d/%y  %H:%M:%S")
        compare = datetime.now() - timedelta(days = days_ago)
        
        if datetime.strptime(timestamp_str, "%m/%d/%y %H:%M:%S") > compare:
          date = timestamp_str
        
          #print(date, item_text)
        
          data.append([date, item_text])
        else:
          pass
        
      except Exception as e:
        pass
        
    data.sort(key=lambda x:pd.to_datetime(x[0]), reverse=True)    
     
    self.ui.label_5.setText("<span style='color: rgb(59, 173, 244);'>Bad IOCs (No Hearbeat): </span>" + f"{len(data)}")
    
    self.table_model.layoutAboutToBeChanged.emit()
    self.table_model._data = data
    self.table_model.layoutChanged.emit()
    
      
  def update_progress_bar(self, df):
    non_nan_count = len(df[df[0]==0])
    self.ui.progressBar.setProperty('maximum', len(df))
    self.ui.progressBar.setProperty('value', non_nan_count)
    

if __name__ == "__main__":
  app = QApplication(sys.argv)
  window = IOC_watcher()
  window.show()
  sys.exit(app.exec_())