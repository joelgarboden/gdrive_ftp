import socket

import ftpserver
from drive import GDrive
import common

if __name__=='__main__':
  config = common.getConfig()
  logger = common.getLogger(config)
  drive = GDrive(config['drive'], logger)
  drive.get_credentials()

  ftp=ftpserver.FTPserver(drive, config, logger)
  ftp.daemon=True
  ftp.start()
  raw_input('Enter to end...\n')
  ftp.stop()