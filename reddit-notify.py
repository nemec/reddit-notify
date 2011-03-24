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

def get_executable_path(name):
    path = "%s/%s" % (os.getcwd(), name)
    if os.path.exists(path) and os.access(path, os.X_OK): return path
    path = "/usr/local/bin/" + name
    if os.path.exists(path) and os.access(path, os.X_OK): return path
    path = "/usr/bin/" + name
    if os.path.exists(path) and os.access(path, os.X_OK): return path
    raise PathNotFound("%s not found" % name)


class redditnotify:

  def __init__(self, username, password, bother, quiet):
    server = indicate.indicate_server_ref_default()
    server.set_type("message.micro")
    server.set_desktop_file(desktop_file)
    server.connect("server-display", self.clicked)
    server.show()

    self.bother = bother
    self.quiet = quiet
    self.unread_utc = 0

    self.api = reddit.Reddit()
    retries = 1
    while True:
      try:
        self.api.login(user=username, password=password)
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
    self.inbox = self.api.get_inbox()
    
    if not self.quiet:
      print "Building indicator..."
    self.indicator = indicate.Indicator()
    self.indicator.set_property("subtype", "micro")
    self.indicator.set_property("sender", "Reddit Mail")
    self.indicator.connect("user-display", self.indicator_click)

  def indicator_click(self, indicator, identifier):
    self.clicked(None, None)
    indicator.hide()

  def raise_alert(self, count):
    self.indicator.set_property("count", str(count))
    self.indicator.show()
    self.indicator.set_property("draw-attention", "true")

  def notify(self, title, message):
    n = pynotify.Notification(title, message, icon_path)
    n.show()
    return n

  def check_timeout(self):
    mail = self.inbox.get_new_messages()
    if len(mail) > 0:
      if not self.quiet:
        print "%d new messages." % len(mail)
      self.raise_alert(len(mail))
      if self.bother:
        unread = [msg for msg in mail if msg.created_utc > self.unread_utc]
        if unread:
          self.unread_utc = max(msg.created_utc for msg in unread)
          if len(unread) > 1:
            self.notify("New Reddit Messages",
                        "You have %d new messages" % len(unread))
          else:
            self.notify("Reddit message from %s" % unread[0].author,
                        unread[0].body)
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
  parser.add_argument('user', action="store")
  parser.add_argument('password', action="store")


  args = parser.parse_args()

  r = redditnotify(args.user, args.password, args.bother, args.quiet)

  gobject.timeout_add_seconds(args.timeout, r.check_timeout)
  r.check_timeout()

  gtk.main()
