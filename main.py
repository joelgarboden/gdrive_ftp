import socket

import ftpserver
from drive import GDrive
import common

#TODO Logging

if __name__=='__main__':
  config = common.getConfig()

  drive = GDrive(config['drive'])
  drive.get_credentials()

  ftp=ftpserver.FTPserver(drive, config)
  ftp.daemon=True
  ftp.start()
  raw_input('Enter to end...\n')
  ftp.stop()