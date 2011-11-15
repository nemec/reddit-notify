import indicate

class IndicatorAccountManager(object):

  def __init__(self, desktop_file):
    server = indicate.indicate_server_ref_default()
    server.set_type("message.micro")
    server.set_desktop_file(desktop_file)
    server.connect("server-display", self.clicked)
    server.show()
    
  def add_account(self, account):
    account.indicator.connect("user-display", self.indicator_click)
    
  def indicator_click(self, indicator, identifier):
    self.clicked(None, None)
    indicator.hide()
    
  def clicked(self, *args):
    """ Do nothing when clicked.
        Overwritten in subclass.
    """
    pass
    

class IndicatorAccount(object):

  def __init__(self, name):
    self.indicator = indicate.Indicator()
    self.indicator.set_property("subtype", "micro")
    self.indicator.set_property("sender", name)
    
  def show_alert(self, count):
    self.indicator.set_property("count", str(count))
    self.indicator.show()
    self.indicator.set_property("draw-attention", "true")
    
  def hide_alert(self):
    self.indicator.hide()
