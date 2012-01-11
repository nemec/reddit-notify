#!/usr/bin/env python

import gobject
import gtk
import time
import os
import pynotify
import subprocess
import urllib2
import argparse
import indicate
import indicatoraccount

# For debugging
#import sys
#sys.path.insert(0, "../../src/reddit_api")

import reddit


INSTALL_PATH = os.path.dirname(os.path.abspath(__file__))
desktop_file = "%s/reddit.desktop" % INSTALL_PATH
icon_path = "%s/reddit.png" % INSTALL_PATH

class RedditAccount(indicatoraccount.IndicatorAccount):

  def __init__(self, username, password):
    super(RedditAccount, self).__init__(username)
    self.api = reddit.Reddit(user_agent="reddit-notify")
    self.username = username.strip()
    self.password = password.strip()

  def login(self):
    self.api.login(username=self.username, password=self.password)

  def get_new_messages(self):
    return self.api.user.get_unread(limit=None)


def get_executable_path(name):
    path = "%s/%s" % (os.getcwd(), name)
    if os.path.exists(path) and os.access(path, os.X_OK): return path
    path = "/usr/local/bin/" + name
    if os.path.exists(path) and os.access(path, os.X_OK): return path
    path = "/usr/bin/" + name
    if os.path.exists(path) and os.access(path, os.X_OK): return path
    raise PathNotFound("%s not found" % name)


class RedditNotify(indicatoraccount.IndicatorAccountManager):
  """ RedditNotify object
      users: sequence of (username, password) tuples
      bother: a boolean determining whether or not to display a notification
        box upon new messages
      quiet: a boolean determining whether or not to print information
        to stdout
  """
  def __init__(self, users, bother, quiet):
    super(RedditNotify, self).__init__(desktop_file)
    pynotify.init("Reddit Notify")
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
        delay = min(5 * retries, 60)
        if not self.quiet:
          print "Error connecting. Sleeping for %d seconds..." % delay
        time.sleep(delay)
        retries += 1
        continue
      break
    
    for account in self.accounts:
      self.add_account(account)


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
        mail = list(account.get_new_messages())
      except Exception, e:
        print "Exception occurred: %s" % e
      if len(mail) > 0:
        if not self.quiet:
          print "%d new messages for %s" % (len(mail), account.username)
        account.show_alert(len(mail))
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
        account.hide_alert()
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
    r = RedditNotify(users, args.bother, args.quiet)

    gobject.timeout_add_seconds(args.timeout, r.check_timeout)
    r.check_timeout()

    gtk.main()
  except IOError:
    print "Could not open configuration file."

