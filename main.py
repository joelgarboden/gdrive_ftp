import socket

import ftpserver
import drive

local_ip = '0.0.0.0' #socket.gethostbyname(socket.gethostname())
ftp_port = 21

if __name__=='__main__':
  drive.get_credentials()

  ftp=ftpserver.FTPserver(drive, local_ip, ftp_port)
  ftp.daemon=True
  ftp.start()
  raw_input('Enter to end...\n')
  ftp.stop()