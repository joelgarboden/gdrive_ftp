var ftpd = require('ftpd');
var fs = require('fs');
var path = require('path');

var os = require('os');
var ifaces = os.networkInterfaces();
var ftp_bind_ip = '127.0.0.1';
var google_drive;

Object.keys(ifaces).forEach(function (ifname) {
  ifaces[ifname].forEach(function (iface) {
    if ('IPv4' !== iface.family || iface.internal !== false) {
      return;
    }

    ftp_bind_ip = iface.address;
  });
});

var keyFile;
var certFile;

var options = {
  host: process.env.IP || ftp_bind_ip,
  port: process.env.PORT || 21,
  tls: null
};

if (process.env.KEY_FILE && process.env.CERT_FILE) {
  console.log('Running as FTPS server');
  if (process.env.KEY_FILE.charAt(0) !== '/') {
    keyFile = path.join(__dirname, process.env.KEY_FILE);
  }
  if (process.env.CERT_FILE.charAt(0) !== '/') {
    certFile = path.join(__dirname, process.env.CERT_FILE);
  }
  options.tls = {
    key: fs.readFileSync(keyFile),
    cert: fs.readFileSync(certFile),
    ca: !process.env.CA_FILES ? null : process.env.CA_FILES
      .split(':')
      .map(function(f) {
        return fs.readFileSync(f);
      }),
  };
} else {
  console.log();
  console.log('*** To run as FTPS server,                 ***');
  console.log('***  set "KEY_FILE", "CERT_FILE"           ***');
  console.log('***  and (optionally) "CA_FILES" env vars. ***');
  console.log();
}

var createServer = function _createServer(gdrive){
  google_drive = gdrive;
  
  var server = new ftpd.FtpServer(options.host, {
    getInitialCwd: function() {
      return '/';
    },
    getRoot: function() {
      return process.cwd();
    },
    pasvPortRangeStart: 1025,
    pasvPortRangeEnd: 1050,
    tlsOptions: options.tls,
    allowUnauthorizedTls: true,
    useWriteFile: false,
    useReadFile: false,
    uploadMaxSlurpSize: 7000, // N/A unless 'useWriteFile' is true.
  });

  server.on('error', function(error) {
    console.error('FTP Server error:', error);
  });

  server.on('client:connected', function(connection) {
    var username = null;
    console.log('client connected: ' + connection.remoteAddress);
    connection.on('command:user', function(user, success, failure) {
      if (user) {
        username = user;
        success();
      } else {
        failure();
      }
    });

    connection.on('command:pass', function(pass, success, failure) {
      if (pass) {
        success(username, _fakeFs );
      } else {
        failure();
      }
    });
  });

  server.debugging = 4;
  server.listen(options.port);
  console.log('Listening on port ' + options.port);
};

var createWriteSteam = function _createWriteSteam(file_path, options) {
  var relative_path = file_path.replace(process.cwd(), '');

  console.log("Relative file_path", relative_path);
  
  var datastream = fs.createWriteStream(file_path, options);
  
  google_drive.files.insert({
    resource: {
      title: path.basename(relative_path + '/' + file_path),
    },
    media: {
      body: datastream
    },
  }, function(err, response) {
    if (err) {
      return err;
    }
    return response;
  });
  
  return datastream;
};

var _fakeFs = {
  createWriteStream: createWriteSteam,
  stat: fs.stat
};

module.exports = { 
  createServer: createServer
};
