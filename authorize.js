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
    
    return Promise.resolve(tokens);

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
    });

  }
}

return authenticate();
/*
if (tokens) {
  console.log("Tokens parsed");
  oauth2Client.setCredentials(tokens);

  var drive = google.drive({ version: 'v2', auth: oauth2Client });
  drive.files.list({
    maxResults: 10,
    q: '',
    fields: 'items(id,title,description,downloadUrl)'
    },
    function(err, resp) {
      if (err) {
        console.log("Error");
        return err;
      }
      
      console.log("Success", resp);
    });

} else {
  console.log("No tokens obtained in time, try launching again");
}

module.exports = config;
*/
