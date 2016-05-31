import socket

import ftpserver
import drive

local_ip = socket.gethostbyname(socket.gethostname())
ftp_port = 21

if __name__=='__main__':
  drive.get_credentials()

  ftp=ftpserver.FTPserver(drive)
  ftp.daemon=True
  ftp.start()
  print 'On', local_ip, ':', ftp_port
  raw_input('Enter to end...\n')
  ftp.stop()