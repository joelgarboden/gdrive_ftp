import httplib2
import os
import io
from io import BytesIO

from apiclient import discovery
import oauth2client
from oauth2client import client, tools
from mimetypes import guess_type
from apiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from common import GDrive_File, FakeBytesIO

class GDrive(object):
  def __init__(self, config, parent_logger):
    self.config = config
    self.logger = parent_logger.getLogger(__name__)

  def get_credentials(self):
    try:
      import argparse
      flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
    except ImportError:
      flags = None

    store = oauth2client.file.Storage(self.config['credentials_cache'])

    credentials = store.get()
    if not credentials or credentials.invalid:
      flow = client.flow_from_clientsecrets(self.config['client_secrets'], self.config['scopes'])
      flow.user_agent = self.config['app_name']
      if flags:
        credentials = tools.run_flow(flow, store, flags)
      else: # Needed only for compatibility with Python 2.6
        credentials = tools.run(flow, store)
      self.logger.info('Storing credentials to %s', self.config['credentials_cache'])

    return credentials

  def getRoot(self):
    credentials = self.get_credentials()
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

  def listFiles(self, parentDirId=None):
    dirId = parentDirId if parentDirId != None else self.getRoot().id

    credentials = self.get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    found_files = []
    page_token = None

    while True:
      response = service.files().list(
        pageSize=25,
        fields="nextPageToken, files(id, name, mimeType, size, parents, createdTime)",
        q="'{0}' in parents and trashed=false".format(dirId),
        pageToken=page_token
        ).execute()

      for item in response.get('files', []):
        found_files.append(GDrive_File(
          name=item['name'],
          id=item['id'],
          mimeType=item['mimeType'],
          size=item.get('size', 1),
          parents=item['parents'],
          createdTime=item['createdTime']
        ))
      page_token = response.get('nextPageToken', None)
      if page_token is None:
        break;

    return found_files

  def getFolderByPath(self, path, cwd_id):

    if path[0:1] == '/':
      top_dir_id = self.getRoot().id
    else:
      top_dir_id = cwd_id

    credentials = self.get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    path_array = filter(lambda a: a != '', path.split('/'))

    for path in path_array:

      results = service.files().list(
        pageSize=2,
        fields="files(id, name, mimeType, size, parents, createdTime)",
        q="'{0}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder' and name='{1}'".format(top_dir_id, path)
        ).execute().get('files', [])

      if len(results) != 1:
        return GDrive_File()

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

  def getFile(self, file_name, parentDirId=None):
    dirId = parentDirId if parentDirId != None else self.getRoot().id

    credentials = self.get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    found_files = []

    results = service.files().list(
      pageSize=2,
      fields="files(id, name, mimeType, size, parents, createdTime)",
      q="'{0}' in parents and trashed=false and mimeType!='application/vnd.google-apps.folder' and name='{1}'".format(dirId, file_name)
      ).execute()

    if len(results['files']) != 1:
      return GDrive_File()

    item = results['files'][0]

    return GDrive_File(
        name=item['name'],
        id=item['id'],
        mimeType=item['mimeType'],
        size=item.get('size', 1),
        parents=item['parents'],
        createdTime=item['createdTime']
      )

  def uploadFile(self, bytesio, dir_id, filename, mode):
    credentials = self.get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    body = {
      'name': filename,
      'parents': [dir_id]
    }

    mimeType = 'application/octet-stream' if mode == 'I' else 'text/plain'

    media = MediaIoBaseUpload(bytesio, mimetype=mimeType, chunksize=self.config['chunk_size'], resumable=True)
    request = service.files().create(body=body, media_body=media)

    response = None
    while response is None:
      status, response = request.next_chunk()
      if status:
        self.logger.info("Uploaded %s: %d%%.", filename, int(status.progress() * 100))
    self.logger.info("Upload Complete %s", filename)

    return response

  def createDirectory(self, parent_dir_id, directory_name):
    credentials = self.get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    body = {
      'name': directory_name,
      'mimeType': 'application/vnd.google-apps.folder',
      'parents': [parent_dir_id]
    }

    response = service.files().create(body=body).execute()

    return response

  def delete(self, object_id):
    credentials = self.get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    response = service.files().delete(fileId=object_id).execute()

    return response

  def getFileData(self, file_id, ftp_datasock):
    credentials = self.get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    data_request = service.files().get_media(fileId=file_id)

    gdrive_data_stream = FakeBytesIO()

    CHUNK_SIZE = self.config['chunk_size']
    downloader = MediaIoBaseDownload(gdrive_data_stream, data_request, chunksize=CHUNK_SIZE)

    done = False
    while done is False:
      status, done = downloader.next_chunk()
      data = gdrive_data_stream.read(CHUNK_SIZE)
      ftp_datasock.send(data)
      if status:
        self.logger.info("Downloaded %s: %d%%.", filename, int(status.progress() * 100))

    self.logger.info("Streamed %s bytes", gdrive_data_stream.tell())

    return done

  def exists(self, id):
    credentials = self.get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    try:
      service.files().get(fileId=id).execute()
      return True
    except HttpError:
      return False
