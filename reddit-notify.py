#!/usr/bin/python

import gobject
import gtk
import time
import os
import pynotify
import subprocess
import urllib2
import argparse
import reddit
import indicate


INSTALL_PATH = os.path.dirname(os.path.abspath(__file__))
desktop_file = "%s/reddit.desktop" % INSTALL_PATH
icon_path = "%s/reddit.png" % INSTALL_PATH

class RedditAccount(object):

  def __init__(self, username, password):
    self.api = reddit.Reddit(user_agent="reddit-notify")
    self.username = username.strip()
    self.password = password.strip()

  def login(self):
    self.api.login(user=self.username, password=self.password)

  def initialize_inbox(self):
    self.inbox = self.api.get_inbox()

  def get_new_messages(self):
    return self.inbox.get_new_messages()

  def build_indicator(self):
    self.indicator = indicate.Indicator()
    self.indicator.set_property("subtype", "micro")
    self.indicator.set_property("sender", self.username)


def get_executable_path(name):
    path = "%s/%s" % (os.getcwd(), name)
    if os.path.exists(path) and os.access(path, os.X_OK): return path
    path = "/usr/local/bin/" + name
    if os.path.exists(path) and os.access(path, os.X_OK): return path
    path = "/usr/bin/" + name
    if os.path.exists(path) and os.access(path, os.X_OK): return path
    raise PathNotFound("%s not found" % name)


class redditnotify(object):
  """ redditnotify object
      users: sequence of (username, password) tuples
      bother: a boolean determining whether or not to display a notification
        box upon new messages
      quiet: a boolean determining whether or not to print information
        to stdout
  """
  def __init__(self, users, bother, quiet):
    server = indicate.indicate_server_ref_default()
    server.set_type("message.micro")
    server.set_desktop_file(desktop_file)
    server.connect("server-display", self.clicked)
    server.show()

    self.bother = bother
    self.quiet = quiet
    self.unread_utc = 0

    self.accounts = [RedditAccount(u, p) for u, p in users]

    if not self.quiet:
      print "Logging in..."

    retries = 1
    while True:
      try:
        for account in self.accounts:
          account.login()
      except urllib2.URLError, e:
        delay = 3 ** retries
        if not self.quiet:
          print "Error connecting. Sleeping for %d seconds..." % delay
        time.sleep(delay)
        retries += 1
        continue
      break
    
    if not self.quiet:
      print "Initializing inbox..."
    for account in self.accounts:
      try:
        account.initialize_inbox()
      except urllib2.HTTPError:
        # Try once more...
        account.initialize_inbox()
    
    if not self.quiet:
      print "Building indicator..."
    for account in self.accounts:
      account.build_indicator()
      account.indicator.connect("user-display", self.indicator_click)

  def indicator_click(self, indicator, identifier):
    self.clicked(None, None)
    indicator.hide()

  def raise_alert(self, account, count):
    account.indicator.set_property("count", str(count))
    account.indicator.show()
    account.indicator.set_property("draw-attention", "true")

  def notify(self, title, message):
    n = pynotify.Notification(title, message, icon_path)
    n.show()
    return n

  def check_timeout(self):
    if not self.quiet:
      print "checking..."
    for account in self.accounts:
      mail = []
      try:
        mail = account.get_new_messages()
      except Exception, e:
        print "Exception occurred: %s" % e
      if len(mail) > 0:
        if not self.quiet:
          print "%d new messages for %s" % (len(mail), account.username)
        self.raise_alert(account, len(mail))
        if self.bother:
          unread = [msg for msg in mail if msg.created_utc > self.unread_utc]
          if unread:
            self.unread_utc = max(msg.created_utc for msg in unread)
            if len(unread) > 1:
              self.notify("%s: New Reddit Messages" % account.username,
                          "You have %d new messages" % len(unread))
            else:
              self.notify("Reddit message from %s for %s" %
                            (unread[0].author, account.username),
                          unread[0].body)
      else:
        account.indicator.hide()
    return True

  def clicked(self, server, ident):
    subprocess.call([get_executable_path("xdg-open"),
                      "http://www.reddit.com/message/inbox/"])

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description="Indicator applet that checks"
                                  " a Reddit account for new mail.")
  parser.add_argument('-t', action="store", dest="timeout", type=int,
                   default=30, help="Delay in seconds between mail checks.")
  parser.add_argument('--no-notify', action="store_false", dest="bother",
                      help="Do not pop up a notification when new mail arrives")
  parser.add_argument('-q', action="store_true", dest="quiet",
                      help="Suppress output to stdout.")
  parser.add_argument('configfile', action="store",
                 help="File containing ':' separated username, password pairs")


  args = parser.parse_args()

  try:
    f = open(args.configfile)
    data = f.readlines()
    users = [tuple(line.split(":")) for line in data]
    r = redditnotify(users, args.bother, args.quiet)

    gobject.timeout_add_seconds(args.timeout, r.check_timeout)
    r.check_timeout()

    gtk.main()
  except IOError:
    print "Could not open configuration file."

