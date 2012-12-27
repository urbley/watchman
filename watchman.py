#!/usr/bin/python
from __future__ import print_function
import sys
import os
import re
import commands
import datetime
import subprocess
import shlex
import smtplib


# Global variables
searches = {} # dictionary to store all searches found in the conf
pwd = os.path.dirname( os.path.realpath( __file__ ) ) # I'm running from here
log = open( "/var/log/watchman_log", "a" )

# The below vars are read in from watchman.conf
server = ""
reportEmail = ""
domain = ""

# Check for a config file and load the contents
def loadConfig():
    try:
        f = open( pwd + "/watchman.conf", "r" )
    except IOError, e:
        rightNow = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
        print( rightNow + " - I could not find watchman.conf in the working directory (" + pwd + "). Error: %s" % e, file=log )

        try:
            f = open( pwd + "/watchman.conf", "w" )
            print( "[General]\n#These 3 vars MUST be set correctly for the script to work\n\n#server can get retrieved from hostname linux command\nserver=server1\n\n#this is the email where errors will be sent\nreportEmail=you@yourdomain.com\n\n#any domain that has send permissions in sendmail\ndomain=yourdomain.com\n\n[Searches]\n#You can add multiple search patterns in the key=value formation e.g.\n#Search1=searchd\n#Search2=searche", file=f )

            rightNow = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
            print( rightNow + " - It's ok.  I created a blank for you but you'll need to configure it or there's nothing for me to do!", file=log )

            f = open( pwd + "/watchman.conf", "r" )
        except IOError, e:
            rightNow = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
            print( rightNow + " - I tried to create a blank template for you but unfortunately I couldn't.  You're on your own muchacho." )
            print( rightNow + " - Error was: %s " % e, file=log )

    for line in f:
        # Skipping the rubbish
        if re.search( "^\[", line ):
            continue # Lets ignore section headers. the conf isn't complicated enough yet...

        if re.search( "^#", line ):
            continue # Lets ignore comments of course

        if line == '\n':
            continue # We don't care about blank lines do we?

        # Reading in the useful info from General section
        if re.search( "^server=.+", line ):
            global server
            server = re.search( "^server=(.+)", line ).group(1)

            if re.search( "^domain=.+", line ):
                global domain
                domain = re.search( "^domain=(.+)", line ).group(1)

            if re.search( "^reportEmail=.+", line ):
                global reportEmail
                reportEmail = re.search( "^reportEmail=(.+)", line ).group(1)

            # Read in all defined searches
            matches = re.search( "^(Search\d+)=(.+)", line )

            if matches:
                # We want the search name and the search string.
                searches[matches.group(1)] = matches.group(2)


# Function to restart a process from a failed search
def restartProcess( search, pattern ):
    x = 1
    args = shlex.split( pattern )

    while x < 4:
        rightNow = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
        print( rightNow + " - Trying to start %s: %s" % (search, pattern), file=log )

        output = subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]
        print( rightNow + " - Attempt %d output: %s" % ( x, output ), file=log )

        # After having trawled through the Sphinx documentation I can confirm that if Sphinx fails to start for ANY reason
        # it will have "FATAL" in stdout.
        if re.search( "^.+FATAL.", output, re.MULTILINE ):
            if x < 3:
                rightNow = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
                print( rightNow + " - Attempt %d failed.  Trying again" % x, file=log )
            else:
                rightNow = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
                print( rightNow + " - Attempt %d failed.  Emailing admin" % x, file=log )
        else:
            rightNow = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
            print( rightNow + " - Success! %s restarted successfully\n" % search, file=log )
            break

        x += 1

        # If we've tried 3 times without a successful restart send an email to alert whoever needs to know about this
        if x == 4:
            fromEmail = "watchman@" + server + "." + domain
            errorMessage = "From: Watchman <" + fromEmail + ">\n" +\
                           "To: Server Admin <" + reportEmail + ">\n" +\
                           "MIME-Version: 1.0\n" +\
                           "Content-type: text/html\n" +\
                           "Subject: Watchman Alert on: " + server + " with: " + search + "\n" +\
                           "\n"+\
                           "Oh dear.  I found an error when checking for your configured processes.<br />" +\
                           "<br />"+\
                           "<strong>" + search + "</strong> on server: <strong>" + server + "</strong> was not running when I checked and I could not restart it.  The search term was <strong>" + pattern + "</strong><br />" +\
                           "<br />"+\
                           "You should probably look into this right away.<br /><br />The output from the last attempt was:<br />------------------------<br /> " + output

            try:
                errorEmail = smtplib.SMTP( 'localhost' )
                errorEmail.sendmail( fromEmail, reportEmail, errorMessage )
            except Exception, e :
                rightNow = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
                print( rightNow + " - Could not send email with error: %s" % e, file=log )


# I've broken out the individual searches into a reuseable function
def runSearch( search, pattern ):
    rightNow = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
    print( "%s - Running %s.\n%s - Searching for \"%s\"." % ( rightNow, search, rightNow, pattern ), file=log )

    commOutput = commands.getstatusoutput( "pgrep -fl \"" + pattern + "\"" )

    # Bummer... The pgrep is in the list of search results causing false positives.  Need to RE them out.
    # I've tried ps and considered querying /proc using glob but they all require as much work as the grep.
    # Most Python resources recommend avoiding RE where possible (hog) but given the size of the project
    # and since I like using RE I'm going to proceed with that.

    commOutputList = commOutput[1].split( '\n' )

    for item in commOutputList:
        if re.search( "^.+pgrep.+", item ):
            commOutputList.remove( item )

    if commOutputList:
        rightNow = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
        print( rightNow + " - %s is currently running.  Nothing to do!\n" % pattern, file=log )
    else:
        rightNow = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
        print( rightNow + " - Oh dear! Restarting %s...\n" % pattern, file=log )

        restartProcess( search, pattern )


# Run the searches
def runSearches():
    if searches:
        # Log readability separator
        rightNow = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
        print( "\n------------------------ Search starting - %s ------------------------" % rightNow, file=log )

        for search, pattern in searches.iteritems():
            runSearch( search, pattern )
    else:
        rightNow = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
        print( rightNow + " - There were no searches in the config (" + pwd + "/watchman.conf).", file=log )
        sys.exit()


# Run the script
loadConfig()

runSearches()

# That's all folks!