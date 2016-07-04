class Auth(object):
  def __init__(self, users_list, parent_logger):
    self.users_list = users_list
    self.logger = parent_logger.getLogger(__name__)

  def isValid(self, user_name, password):
    if len(self.users_list) == 0:
      self.logger.warning('No users configured, running as anonymous')
      return True

    try:
      return self.users_list[user_name] == password
    except KeyError:
      return False
