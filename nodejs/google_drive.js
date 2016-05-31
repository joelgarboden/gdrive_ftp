var google = require('googleapis');
var OAuth2 = google.auth.OAuth2;
var fs = require('fs');
var readline = require('readline');
var Promise = require('bluebird');
var oauth2Client = new OAuth2('425787237453-qdp1dn83e4ie8at30cuj5u4vvfce4n5k.apps.googleusercontent.com', '55qOpEHkovg6KH7FYYs-Qfzo', 'urn:ietf:wg:oauth:2.0:oob');

var auth_options = {
  access_type: 'offline', // 'online' (default) or 'offline' (gets refresh_token)
  scope: 'https://www.googleapis.com/auth/drive'
};

var authenticate = function _authenticate() {
  var authorization_token = process.argv[2];
  try {
    var tokens = JSON.parse(fs.readFileSync('token.cache').toString().trim());

    oauth2Client.setCredentials(tokens);
    var drive = google.drive({ version: 'v2', auth: oauth2Client });

    return Promise.resolve(drive);

  } catch (e) {
    console.error("Unable to parse token.cache, authenticating");

    return new Promise(function (resolve, reject) {
      var url = oauth2Client.generateAuthUrl(auth_options);

      return resolve(url);
    })
    .then(function _thenGenerateAuthUrl(url){
      return new Promise(function (resolve, reject){
        console.log(url);

        var rl = readline.createInterface({
          input: process.stdin,
          output: process.stdout
        });

        rl.question("After opening URL and authenticating, copy-paste value into console: " , function _readAuthTokenPrompt(auth_token){
          rl.close();
          return resolve(auth_token);
        });
      });
    })
    .then(function _thenAuthTokenPrompt(auth_token){
      console.log("Auth token ", auth_token);

      return new Promise(function (resolve, reject){
        oauth2Client.getToken(auth_token, function(err, tokens) {
          if(err) return reject(err);

          console.log("Successful auth");
          fs.writeFileSync('token.cache', JSON.stringify(tokens));

          return resolve(tokens);
        });
      });
    })
    .then(function _thenGotTokens(tokens){
      oauth2Client.setCredentials(tokens);
      var drive = google.drive({ version: 'v2', auth: oauth2Client });

      return Promise.resolve(drive);
    });

  }
}

var upload = function _upload(path, filename) {
  return new Promise(function (resolve, reject) {
    try {
      drive.files.insert({
        resource: {
          title: path.basename(file_path),
        },
        media: {
          body: datastream
        },
      }, function(err, response) {
        if (err) {
          return resolve("Unable to upload file" + file_path);
        }
        GLOBAL.logger.info("Uploaded file", file_path);

        return resolve(file_path);
      });
    } catch (e) {
      GLOBAL.logger.warn("Problem uploading " + file_path, { error: e, stack: e.stack });
      return resolve("Problem uploading " + file_path);
    }
  });
}

module.exports = { 
  authenticate: authenticate,
  upload: upload
};
