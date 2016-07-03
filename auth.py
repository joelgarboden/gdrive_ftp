class Auth(object):
  def __init__(self, users_list):
    self.users_list = users_list

  def isValid(self, user_name, password):
    if len(self.users_list) == 0:
      print 'No users configured, configured for anonymous'
      return True

    try:
      return self.users_list[user_name] == password
    except KeyError:
      return False
