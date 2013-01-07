#Reddit Mail Notifier


##Description

Hooks into Gnome's Notification system and displays unread Reddit messages.

Updated for Gnome3, so it will no longer work on older Gnome systems.

Before running, input username and password into a file
  (see accounts.config.example). The different options (like timeout) can be
  seen with `python reddit-notify.py --help`.


##Installation

Requires the Python Reddit API located at https://github.com/praw-dev/praw.
If you want the Reddit icon installed, run:
  `xdg-icon-resource install --novendor --size 48 reddit.png`
