#!/usr/bin/python
from __future__ import print_function

import os, sys

import argparse
import subprocess
from ConfigParser import SafeConfigParser

from getpass import getpass, getuser

from pyOlog import LogEntry, Logbook, Tag, Attachment, OlogClient

try:
  import keyring
except ImportError:
  have_keyring = False
else:
  have_keyring = True

description = """\
Command line utility for making OLog entries.

Example:
  %(prog)s -l Operations -t Data -u swilkins -a ./image.png

This makes a log entry into the 'Operations' log tagged with the
tag 'Data' from the account of 'swilkins' with an image 'image.png
attached to the log entry. The log text is taken from stdin and can
either be entered on the command line or piped in. Alternatively a 
text file can be specified with the '--file' option. 

Multiple Tags and Logbooks can be specified after the option on the
command line separated by spaces. 

Note : A password is requested on the command line unless the option
'-p' is supplied with a valid password.

Optionally commands will take default from a config file located
in the users home directory ~/.olog.cfg This can contain the base
url for the Olog and also the default logbook to use.


"""

class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, 
                      argparse.RawDescriptionHelpFormatter):
  pass

def get_option(cfg, base, opt):
  """Check if option base/opt is in config cfg"""
  if cfg.has_option(base, opt):
    return cfg.get(base, opt)
  else:
    return None

def get_screenshot(root = False, itype = 'png'):
  """Open ImageMagick and get screngrab as png."""
  if root:
    opts = '-window root'
  else:
    opts = ''
  image = subprocess.Popen('import {0} {1}:-'.format(opts,itype),
                           shell = True, 
                           stdout = subprocess.PIPE)
  return image.communicate()[0]

def olog():
  """Command line utility for making Olog entries"""

  # Get Defaults from Config File

  cfg = SafeConfigParser()
  files = ['/etc/olog.conf',
           os.path.join(os.getenv('HOME'),'.olog.conf')]
  files = cfg.read(files)

  default_url = get_option(cfg, 'olog', 'url')

  default_logbooks = get_option(cfg, 'olog', 'logbooks')
  if default_logbooks is not None:
    default_logbooks = default_logbooks.split(',')

  default_username = get_option(cfg, 'olog', 'username')
  if default_username is None:
    default_username = getuser()

  default_passwd = get_option(cfg, 'olog', 'password')

  default_tags = get_option(cfg, 'olog', 'tags')
  if default_tags is not None:
    default_tags = default_tags.split(',')

  # Parse Command Line Options

  parser = argparse.ArgumentParser(epilog = description,
                                   formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('-l', '--logbooks', dest = 'logbooks',
                    help = "Logbook Name(s)", nargs = '*',
                    default = default_logbooks)
  parser.add_argument('-t', '--tags', dest = 'tags',
                    nargs = '*', help = "OLog Tag Name(s)",
                    default = default_tags)
  parser.add_argument('-u', '--user', dest = 'user',
                    default = default_username,
                    help = "Username for Olog Access")
  parser.add_argument('-f', '--file', dest = 'text',
                    type=argparse.FileType('r'),
                    default=None,
                    help = "Filename of log entry text.")
  parser.add_argument('--url', dest = 'url',
                    help = "Base URL for Olog Access",
                    default = default_url)
  parser.add_argument('-a', '--attach', dest = 'attach',
                    nargs = '*',
                    help = "filename of attachments")
  parser.add_argument('-p', '--passwd', dest = 'passwd',
                    help = "Password for logging entry")
  group = parser.add_mutually_exclusive_group()
  group.add_argument('-s','--screenshot', dest = 'screenshot',
                    help = 'Take screenshot of whole screen', 
                    default = False,
                    action = 'store_true')
  group.add_argument('-g', '--grap', dest = 'grab',
                    help = 'Grab area of screen and add as attatchment.',
                    default = False,
                    action = 'store_true')
  group = parser.add_mutually_exclusive_group()
  group.add_argument('-v', action = 'store_true', dest = 'verbose',
                     help = "Verbose output", default = False)
  group.add_argument('-q', action = 'store_true', dest = 'quiet',
                     help = "Suppress all output", default = False)

  args = parser.parse_args()

  # Check for 

  if args.url is None:
    parser.error('The URL must be specified')
  if args.logbooks is None:
    parser.error('At least one logbook must be specified')
  if args.user is None:
    parser.error('You must specify a username')

  if args.verbose:
    for f in files:
      print("Reading config from {}".format(f))

  logbooks = [Logbook(n) for n in args.logbooks]
  if args.tags is not None:
    tags     = [Tag(n) for n in args.tags]
  else:
    tags = None

  if args.attach is not None:
    attachments = [Attachment(open(a)) for a in args.attach.split(',')]
  else:
    attachments = None

  # Grab Screenshot 

  if args.screenshot or args.grab:
    if not args.quiet and args.grab:
      print("Select area of screen to add to log entry.", 
            file = sys.stderr)
    screenshot = Attachment(get_screenshot(args.screenshot), 'screenshot.png')
    if attachments is None:
      attachments = [screenshot]
    else:
      attachments.append(screenshot)

  # Get the text for the log entry
  if args.text is not None:
    with args.text as file:
      text = file.read()
  else:
    if not args.quiet:
      print("Type log entry below (Enter -END- to end):",
            file = sys.stderr)
    sentinel = '-END-'
    text = '\n'.join(iter(raw_input, sentinel))

  # First create the log entry

  log_entry = LogEntry(text, args.user, logbooks,
                      tags = tags,
                      attachments = attachments)

  # Now get the password

  passwd = None
  if args.passwd is None:
    if default_passwd is None:
      if have_keyring:
        passwd = keyring.get_password('olog', args.user)
      if passwd is None:
        passwd = getpass('Olog Password for {}:'.format(args.user))
    else:
      passwd = default_passwd
  else:
    passwd = args.passwd
        
  # Now do the log entry

  client = OlogClient(args.url, args.user, passwd)
  client.log(log_entry)

def main():
  try:
    olog()
  except KeyboardInterrupt:
    print('\nAborted.\n')
    sys.exit()

if __name__ == '__main__':
  main()