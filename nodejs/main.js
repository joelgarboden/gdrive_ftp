var Google = require('./google_drive');

var FtpServer = require('./ftp_server');

var google_drive;

return Google.authenticate()
  .then(function _thenAuthenticate(drive){
    google_drive = drive;
    return FtpServer.createServer(google_drive);
  });

/*
ftp -n <<EOF
open 127.0.0.1
user anonymous foo
put npm-debug.log /var/tmp/
EOF


*/