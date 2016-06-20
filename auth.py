import json

class Auth(object):
  def __init__(self, auth_file=None):
    if auth_file != None:
      self.auth_file = auth_file
      with open(self.auth_file) as json_data_file:
        self.users_list = json.load(json_data_file)['users']
    else:
      #TODO Implement GDrive auth
      raise NotImplementedError("Only file auth is currently supported")

  def isValid(self, user_name, password):
    if len(self.users_list) == 0:
      print 'No users configured, configured for anonymous'
      return True

    try:
      return self.users_list[user_name] == password
    except KeyError:
      return False
