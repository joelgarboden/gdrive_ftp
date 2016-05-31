from __future__ import print_function
import httplib2
import os

from datetime import datetime
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

try:
  import argparse
  flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
  flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Drive FTP'

def get_credentials():
  home_dir = os.path.expanduser('~')
  credential_dir = os.path.join(home_dir, '.credentials')
  if not os.path.exists(credential_dir):
    os.makedirs(credential_dir)
  credential_path = os.path.join(credential_dir,
                                 'drive-python-quickstart.json')

  store = oauth2client.file.Storage(credential_path)
  credentials = store.get()
  if not credentials or credentials.invalid:
    flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
    flow.user_agent = APPLICATION_NAME
    if flags:
      credentials = tools.run_flow(flow, store, flags)
    else: # Needed only for compatibility with Python 2.6
      credentials = tools.run(flow, store)
    print('Storing credentials to ' + credential_path)
  return credentials

def getRoot():
  credentials = get_credentials()
  http = credentials.authorize(httplib2.Http())
  service = discovery.build('drive', 'v3', http=http)

  results = service.files().get( fileId='root' ).execute()

  return results['id']

def listFiles(parentDirId=getRoot()):

  credentials = get_credentials()
  http = credentials.authorize(httplib2.Http())
  service = discovery.build('drive', 'v3', http=http)
  print("Finding files with parent: {0}".format(parentDirId))
  found_files = []

  results = service.files().list(
    pageSize=10,
    fields="nextPageToken, files(id, name, mimeType, size, parents, createdTime)",
    q="'{0}' in parents and trashed=false".format(parentDirId)
    ).execute()

  items = results.get('files', [])
  if items:
    for item in items:
      found_files.append(GDrive_File(
        name=item['name'],
        id=item['id'],
        mimeType=item['mimeType'],
        size=item.get('size', 1),
        parents=item['parents'],
        createdTime=item['createdTime']
      ))
      
  return found_files


class GDrive_File(object):
  def __init__(self, name=None, id=None, mimeType=None, size=None, parents=None, createdTime=None):
    self.name = name
    self.id = id
    self.mimeType = mimeType
    self.isDirectory = mimeType == 'application/vnd.google-apps.folder'
    self.size = size
    self.parents = parents
    self.createdTime = datetime.strptime(createdTime, '%Y-%m-%dT%H:%M:%S.%fZ')
  def __str__(self):
    return "{0},{1},{2},{3},{4},{5}".format(self.name, self.id, self.isDirectory, self.mimeType, self.parents, self.createdTime)
    
  def __repr__(self):
    return self.__str__()