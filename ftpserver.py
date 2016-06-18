#!/usr/bin/env python2
# https://gist.github.com/scturtle/1035886

import os,socket,threading,time
from pprint import pprint
from io import BytesIO
import sys
import traceback

from common import FTPstate

allow_delete = False

class FTPserverThread(threading.Thread):
    def __init__(self,(conn,addr), drive, state):
      self.conn=conn
      self.addr=addr
      self.rest=False
      self.pasv_mode=False
      self.drive=drive
      self.state=state
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

    def SYST(self,cmd):
      self.conn.send('215 UNIX Type: L8\r\n')

    def OPTS(self,cmd):
      if cmd[5:-2].upper()=='UTF8 ON':
        self.conn.send('200 OK.\r\n')
      else:
        self.conn.send('451 Sorry.\r\n')

    def USER(self,cmd):
      self.conn.send('331 OK.\r\n')

    def PASS(self,cmd):
      self.conn.send('230 OK.\r\n')
      #self.conn.send('530 Incorrect.\r\n')

    def QUIT(self,cmd):
      self.conn.send('221 Goodbye.\r\n')

    def NOOP(self,cmd):
      self.conn.send('200 OK.\r\n')

    def TYPE(self,cmd):
      self.conn.send('200 Binary mode only.\r\n')
      #TODO support Binary and ASCII toggling

    def CDUP(self,cmd):
      self.conn.send('502 Not implemented yet.\r\n')
      '''
      if not os.path.samefile(self.cwd,self.basewd):
          #learn from stackoverflow
          self.cwd=os.path.abspath(os.path.join(self.cwd,'..'))
      self.conn.send('200 OK.\r\n')
      '''

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

    def NLST(self,cmd):
      self.LIST(cmd)

    def LIST(self,cmd):
      self.conn.send('150 Here comes the directory listing.\r\n')

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
      #TODO Error if more than one '/', don't support mkdir -p

      directory_name = filter(lambda a: a != '', cmd[4:-2].split('/'))[0]

      #TODO Ensure directory doesn't exist yet
      created_dir = self.drive.createDirectory(self.state.cwd_id, directory_name)
      
      self.conn.send('257 Directory created. Path=%s/%s ID=%s\r\n'.format(self.state.cwd_path, directory_name, created_dir['id']) )
      '''
      chwd=cmd[4:-2].split('/')
      for i in chwd:
        dirs_found = 0
        for j in self.drive.listFiles(self.state.cwd_id):
          if j.name == i:
            self.state.updateCWD(j.id)
            dirs_found += 1

        if dirs_found != 0:

          self.conn.send('257 Directory created.\r\n')
      '''

    def RMD(self,cmd):
      self.conn.send('502 Not implemented yet.\r\n')
      '''
      dn=os.path.join(self.cwd,cmd[4:-2])
      if allow_delete:
          os.rmdir(dn)
          self.conn.send('250 Directory deleted.\r\n')
      else:
          self.conn.send('450 Not allowed.\r\n')
      '''

    def DELE(self,cmd):
      self.conn.send('502 Not implemented yet.\r\n')
      '''
      fn=os.path.join(self.cwd,cmd[5:-2])
      if allow_delete:
          os.remove(fn)
          self.conn.send('250 File deleted.\r\n')
      else:
          self.conn.send('450 Not allowed.\r\n')
      '''

    def RNFR(self,cmd):
      self.conn.send('502 Not implemented yet.\r\n')
      '''
      self.rnfn=os.path.join(self.cwd,cmd[5:-2])
      self.conn.send('350 Ready.\r\n')
      '''

    def RNTO(self,cmd):
      self.conn.send('502 Not implemented yet.\r\n')
      '''
      fn=os.path.join(self.cwd,cmd[5:-2])
      os.rename(self.rnfn,fn)
      self.conn.send('250 File renamed.\r\n')
      '''

    def REST(self,cmd):
      self.conn.send('502 Not implemented yet.\r\n')
      '''
      self.pos=int(cmd[5:-2])
      self.rest=True
      self.conn.send('250 File position reseted.\r\n')
      '''

    def RETR(self,cmd):
      self.conn.send('502 Not implemented yet.\r\n')
      '''
      fn=os.path.join(self.cwd,cmd[5:-2])
      #fn=os.path.join(self.cwd,cmd[5:-2]).lstrip('/')
      print 'Downloading:',fn
      if self.mode=='I':
          fi=open(fn,'rb')
      else:
          fi=open(fn,'r')
      self.conn.send('150 Opening data connection.\r\n')
      if self.rest:
          fi.seek(self.pos)
          self.rest=False
      data= fi.read(1024)
      self.start_datasock()
      while data:
          self.datasock.send(data)
          data=fi.read(1024)
      fi.close()
      self.stop_datasock()
      self.conn.send('226 Transfer complete.\r\n')
      '''

    def STOR(self,cmd):
      parameter=cmd[5:-2]
      print 'Parameter:',parameter

      file_name = parameter.split('/')[-1]

      self.conn.send('150 Opening data connection.\r\n')
      self.start_datasock()

      if parameter.find('/') == -1:
        dest_folder = self.state.cwd_id
      else:
        destination_path = parameter.replace(file_name, '')
        print "Getting path", destination_path, "from cwd", self.state.cwd_id
        dest_folder = self.drive.getFolderByPath(destination_path, self.state.cwd_id)

      print 'Dest folder', dest_folder, 'Filename', file_name

      ftp_data_stream = BytesIO()
      while True:
        data=self.datasock.recv(1024)
        if not data: break
        #TODO Write to GDrive directly
        ftp_data_stream.write(data)

      ftp_data_stream.flush()
      ftp_data_stream.seek(0)

      self.stop_datasock()

      print 'Memory buffer complete, uploading', sys.getsizeof(ftp_data_stream), 'buffer bytes to Drive'

      self.drive.uploadFile(ftp_data_stream, dest_folder.id, file_name)

      self.conn.send('226 Drive Transfer complete.\r\n')

class FTPserver(threading.Thread):
  def __init__(self, drive, ip, port):
    self.drive = drive
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.sock.bind( (ip, port) )
    threading.Thread.__init__(self)

  def run(self):
    self.sock.listen(5)
    while True:
      ftp_state = FTPstate(self.drive.getRoot())
      th=FTPserverThread(self.sock.accept(), self.drive, ftp_state)
      th.daemon=True
      th.start()

  def stop(self):
    self.sock.close()
