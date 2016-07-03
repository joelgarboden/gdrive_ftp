#!/usr/bin/env python2
# https://gist.github.com/scturtle/1035886

import os,socket,threading,time
from pprint import pprint
from io import BytesIO
import sys
import traceback
import threading

from common import FTPstate
from auth import Auth

class FTPserverThread(threading.Thread):
    def __init__(self,(conn,addr), drive, state, auth, config):
      self.conn=conn
      self.addr=addr
      self.drive=drive
      self.state=state
      self.mode='I'
      self.auth = auth
      self.config = config
      self.allow_delete = config['allow_delete']

      self.user_name = ''
      self.rest=False
      self.pasv_mode=False
      threading.Thread.__init__(self)

    def run(self):
      self.conn.send('220 Welcome!\r\n')
      while True:

        cmd=self.conn.recv(256)
        if not cmd: break
        else:
          print 'Received:',cmd
          try:
            func=getattr(self,cmd[:4].strip().upper())
            func(cmd)
          except Exception,e:
            traceback.print_exc()
            self.conn.send('500 Unexpected error.\r\n')

    def start_datasock(self):
      if self.pasv_mode:
        self.datasock, addr = self.servsock.accept()
        print 'connect:', addr
      else:
        self.datasock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.datasock.connect((self.dataAddr,self.dataPort))

    def stop_datasock(self):
      self.datasock.close()
      if self.pasv_mode:
        self.servsock.close()

    def SYST(self,cmd):
      self.conn.send('215 UNIX Type: Google Drive\r\n')

    def OPTS(self,cmd):
      if cmd[5:-2].upper()=='UTF8 ON':
        self.conn.send('200 OK.\r\n')
      else:
        self.conn.send('451 Sorry.\r\n')

    def USER(self,cmd):
      self.user_name = cmd[5:-2]
      self.conn.send('331 OK.\r\n')

    def PASS(self,cmd):
      if self.auth.isValid(self.user_name, cmd[5:-2]):
        self.conn.send('230 OK.\r\n')
      else:
        self.conn.send('530 Incorrect.\r\n')

    def QUIT(self,cmd):
      self.conn.send('221 Goodbye.\r\n')

    def NOOP(self,cmd):
      self.conn.send('200 OK.\r\n')

    def TYPE(self,cmd):
      self.mode=cmd[5]
      self.conn.send( '200 Mode now {0}\r\n'.format(self.mode) )

    def CDUP(self,cmd):
      self.conn.send('502 Not implemented yet.\r\n')

    def PWD(self,cmd):
      self.conn.send('257 \"%s\"\r\n' % self.state.cwd_path)

    def CWD(self,cmd):
      path=cmd[4:-2]

      if path == '/':
        cd_id = self.state.root_object.id
      else:
        new_wd = self.drive.getFolderByPath(path, self.state.cwd_id)
        cd_id = new_wd.id

      if cd_id != None:
        self.state.updateCWD(cd_id, path)
        self.conn.send('250 OK.\r\n')
      else:
        self.conn.send('550 Unable to find directory \"%s\"\r\n' % path)

    def EPRT(self,cmd):
      self.conn.send('502 Not implemented yet.\r\n')

    def PORT(self,cmd):
      if self.pasv_mode:
        self.servsock.close()
        self.pasv_mode = False
      l=cmd[5:].split(',')
      self.dataAddr='.'.join(l[:4])
      self.dataPort=(int(l[4])<<8)+int(l[5])
      self.conn.send('200 Get port.\r\n')

    def PASV(self,cmd): # from http://goo.gl/3if2U
      self.pasv_mode = True
      self.servsock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
      self.servsock.bind(('0.0.0.0',0))
      self.servsock.listen(1)
      ip, port = self.servsock.getsockname()
      print 'open', ip, port
      self.conn.send('227 Entering Passive Mode (%s,%u,%u).\r\n' %
              (','.join(ip.split('.')), port>>8&0xFF, port&0xFF))

    def NLST(self,cmd):
      self.LIST(cmd)

    def LIST(self,cmd):
      self.conn.send('150 Here comes the directory listing.\r\n')

      #TODO support ls with path
      found_files = self.drive.listFiles(self.state.cwd_id)

      self.start_datasock()
      for file in found_files:
        d=file.isDirectory and 'd' or '-'

        ftime=file.createdTime.strftime('%b %m %H:%M')
        k='{0}rw------- 1 user group {1} {2} {3}'.format(d, file.size, ftime, file.name)
        self.datasock.send(k+'\r\n')

      self.stop_datasock()
      self.conn.send('226 Directory send OK.\r\n')

    def MKD(self,cmd):
      paths = filter(lambda a: a != '', cmd[4:-2].split('/'))
      if len(paths) > 1:
        self.conn.send('501 mkdir -p not supported\r\n')
        return

      directory_name = paths[0]

      dir = self.drive.getFolderByPath(directory_name, self.state.cwd_id)

      if dir.id != None:
        self.conn.send( '553 Directory exists {0}\r\n'.format(directory_name) )
        return

      created_dir = self.drive.createDirectory(self.state.cwd_id, directory_name)

      self.conn.send('257 Directory created. Path={0}/{1} ID={2}\r\n'.format(self.state.cwd_path, directory_name, created_dir['id']) )

    def RMD(self,cmd):
      folder_name = cmd[4:-2]

      if not self.allow_delete:
        self.conn.send('450 Not allowed.\r\n')
        return

      folder_id = self.drive.getFolderByPath(folder_name, self.state.cwd_id).id

      if folder_id == None:
        self.conn.send('550 Unable to find folder.\r\n')
        return

      self.drive.delete(folder_id)

      self.conn.send('250 Directory deleted.\r\n')

    def DELE(self,cmd):
      parameter = cmd[5:-2]
      file_name = parameter.split('/')[-1]

      if not self.allow_delete:
        self.conn.send('450 Not allowed.\r\n')
        return

      if parameter.find('/') == -1:
        folder_id = self.state.cwd_id
      else:
        delete_path = parameter.replace(file_name, '')
        folder_id = self.drive.getFolderByPath(delete_path, self.state.cwd_id).id

      if folder_id == None:
        self.conn.send('550 Unable to find folder.\r\n')
        return

      file = self.drive.getFile(file_name, folder_id)

      if file == None or file.id == None:
        self.conn.send('550 Unable to find file.\r\n')
        return

      self.drive.delete(file.id)

      self.conn.send('250 File deleted.\r\n')

    def RNFR(self,cmd):
      self.conn.send('502 Not implemented yet.\r\n')

    def RNTO(self,cmd):
      self.conn.send('502 Not implemented yet.\r\n')

    def REST(self,cmd):
      self.conn.send('502 Not implemented yet.\r\n')

    def RETR(self,cmd):
      parameter = cmd[5:-2]
      file_name = parameter.split('/')[-1]

      if not self.allow_delete:
        self.conn.send('450 Not allowed.\r\n')
        return

      if parameter.find('/') == -1:
        folder_id = self.state.cwd_id
      else:
        delete_path = parameter.replace(file_name, '')
        folder_id = self.drive.getFolderByPath(delete_path, self.state.cwd_id).id

      if folder_id == None:
        self.conn.send('550 Unable to find folder.\r\n')
        return

      file = self.drive.getFile(file_name, folder_id)

      if file == None or file.id == None:
        self.conn.send('550 Unable to find file.\r\n')
        return

      self.conn.send('150 Opening data connection.\r\n')

      self.start_datasock()
      upload_response = self.drive.getFileData(file.id, self.datasock)
      self.stop_datasock()

      self.conn.send('226 Transfer complete.\r\n')

    def STOR(self,cmd):
      parameter=cmd[5:-2]

      file_name = parameter.split('/')[-1]

      self.conn.send('150 Opening data connection.\r\n')
      self.start_datasock()

      if parameter.find('/') == -1:
        dest_folder_id = self.state.cwd_id
      else:
        destination_path = parameter.replace(file_name, '')
        dest_folder_id = self.drive.getFolderByPath(destination_path, self.state.cwd_id).id

      if dest_folder_id == None:
        self.conn.send('550 Unable to find folder.\r\n')
        return

      #TODO move to drive.py
      ftp_data_stream = BytesIO()
      while True:
        data=self.datasock.recv(self.config['chunk_size'])
        if not data: break
        #TODO Write to GDrive directly. TL;DR, can't without a lot of rewrite.
        ftp_data_stream.write(data)

      self.stop_datasock()

      print 'Memory buffer complete, uploading {} bytes to Drive'.format(ftp_data_stream.seek(0, 2))

      self.drive.uploadFile(ftp_data_stream, dest_folder_id, file_name, self.mode)

      self.conn.send('226 Drive Transfer complete.\r\n')

class FTPserver(threading.Thread):
  def __init__(self, drive, config):
    self.drive = drive
    self.config = config['ftp']
    self.auth = Auth(config['users'])
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.sock.bind( (self.config['bind_ip'], self.config['bind_port']) )
    threading.Thread.__init__(self)

  def run(self):
    self.sock.listen(5)
    while True:
      ftp_state = FTPstate(self.drive.getRoot())

      th=FTPserverThread(self.sock.accept(), self.drive, ftp_state, self.auth, self.config)
      th.daemon=True
      th.start()

  def stop(self):
    self.sock.close()
