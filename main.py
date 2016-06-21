import socket

import ftpserver
import drive

local_ip = '0.0.0.0'
ftp_port = 21

#TODO Logging

if __name__=='__main__':
  drive.get_credentials()

  ftp=ftpserver.FTPserver(drive, local_ip, ftp_port, allow_delete=True)
  ftp.daemon=True
  ftp.start()
  raw_input('Enter to end...\n')
  ftp.stop()