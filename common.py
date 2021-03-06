from datetime import datetime
import json
import logging
import sys

class GDrive_File(object):
  def __init__(self, name=None, id=None, mimeType=None, size=None, parents=None, createdTime=None):
    self.name = name
    self.id = id
    self.mimeType = mimeType
    self.isDirectory = mimeType == 'application/vnd.google-apps.folder'
    self.size = size
    self.parents = parents[0] if parents != None else []
    self.createdTime = datetime.strptime(createdTime, '%Y-%m-%dT%H:%M:%S.%fZ') if createdTime != None else None

  def __str__(self):
    return str(self.__dict__)

  def __repr__(self):
    return self.__str__()

class FTPstate(object):
  def __init__(self, root_object, cwd_path='', cwd_id=None):
    self.cwd_id = cwd_id if cwd_id != None else root_object.id
    self.cwd_path = cwd_path
    self.root_object = root_object

  def updateCWD(self, id, path):
    self.cwd_id = id

    if path == None or path == '':
      self.cwd_path = '/'
    else:
      self.cwd_path = self.cwd_path + '/' + path if path[0] != '/' else self.cwd_path + '/'

  def __str__(self):
    return str(self.__dict__)

  def __repr__(self):
    return self.__str__()

class FakeBytesIO(object):
  def __init__(self):
    self.data = None
    self.total_bytes = 0

  def write(self, bytes):
    self.total_bytes += len(bytes)
    self.data = bytes

  def read(self, n_bytes):
    return_data = self.data
    self.data = None
    return return_data

  def tell(self):
    return self.total_bytes

def getConfig(config_file='config.json'):
    with open(config_file) as json_config_file:
      return json.load(json_config_file)

def getLogger(config, level=logging.INFO):
  log_file = config['logging']['file']
  logging.basicConfig( filename=log_file, level=level )
  logging.getLogger().addHandler(logging.StreamHandler())
  return logging
