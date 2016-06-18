from __future__ import print_function
import httplib2
import os
import io

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools
from mimetypes import guess_type
from apiclient.http import MediaIoBaseUpload

from common import GDrive_File

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

  root_dir = service.files().get( fileId='root' ).execute()
  
  return GDrive_File(
      name=root_dir['name'],
      id=root_dir['id'],
      mimeType=root_dir['mimeType'],
      size=1,
      parents = [].append(root_dir['id'])
    )

def listFiles(parentDirId=None):
  dirId = parentDirId if parentDirId != None else getRoot().id
  
  credentials = get_credentials()
  http = credentials.authorize(httplib2.Http())
  service = discovery.build('drive', 'v3', http=http)

  found_files = []

  results = service.files().list(
    pageSize=200,
    fields="nextPageToken, files(id, name, mimeType, size, parents, createdTime)",
    q="'{0}' in parents and trashed=false".format(dirId)
    ).execute()

  for item in results.get('files', []):
    found_files.append(GDrive_File(
      name=item['name'],
      id=item['id'],
      mimeType=item['mimeType'],
      size=item.get('size', 1),
      parents=item['parents'],
      createdTime=item['createdTime']
    ))
      
  return found_files

def getFolderByPath(path, cwd_id):

  print('Evaluating',path)
  
  if path[0:1] == '/':
    top_dir_id = getRoot().id
  else:
    top_dir_id = cwd_id
    
  credentials = get_credentials()
  http = credentials.authorize(httplib2.Http())
  service = discovery.build('drive', 'v3', http=http)

  path_array = filter(lambda a: a != '', path.split('/'))

  print('Path_array', path_array)
  
  for path in path_array:

    results = service.files().list(
      pageSize=2,
      fields="files(id, name, mimeType, size, parents, createdTime)",
      q="'{0}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder' and name='{1}'".format(top_dir_id, path)
      ).execute().get('files', [])

    if len(results) != 1:
      raise Error('Results of query = ' + str(results))

    if path == path_array[-1]:
      folder = results[0]
      found_folder = GDrive_File(
        name=folder['name'],
        id=folder['id'],
        mimeType=folder['mimeType'],
        size=folder.get('size', 1),
        parents=folder['parents'],
        createdTime=folder['createdTime']
      )

      return found_folder
    else:
      top_dir_id = results[0]['id']

  
def uploadFile(bytesio, dir_id, filename):
  credentials = get_credentials()
  http = credentials.authorize(httplib2.Http())
  service = discovery.build('drive', 'v3', http=http)
  
  body = {
    'name': filename,
    'parents': [dir_id]
  }
  
  media = MediaIoBaseUpload(bytesio, mimetype='application/octet-stream', chunksize=1024*1024, resumable=True)
  response = service.files().create(body=body, media_body=media).execute()
  
  print(response)