import os, sys, time, smtplib, string, popen2, subprocess, re, datetime, MimeWriter, StringIO, base64, paramiko
#*******************************************************************#
# SFTP File Transfer                                                #
#                                                                   #
# Author: Natalie Metzger                                           #
# Last Modified: 2011.02.15                                         #
# Purpose: Simple script to SFTP to offsite and grab the latest     #
#          files and save them                                      #
#          to a specific local network location.                    #
#          This script designed to run on a schedule controlled by  #
#          Windows task scheduler.                                  #
#*******************************************************************#

###################VARIABLES#########################################
#!!! Edit these values !!!#
#log_file = "filename_" + mydate + ".txt"   	
user = "sftp-username"              # user ID to SFTP
password = "sftp-password"          # user password to SFTP
host = "offsite-url"                # host name of offsite storage
local_dir = "X:\\somedir"           # local directory files will be save to
remote_dir = "sftp-dir"             # remote directory where new csv files are located

#!!! Do not edit these values !!!#
day = time.strftime("%d", time.localtime())
today = datetime.date.today()
mydate = today.strftime("%Y%m%d")
mytime = time.strftime("%H:%M:%S", time.localtime())

###################FUNCTIONS#########################################

def print_status(mystatus):
    #LF.write(mystatus)
    print mystatus

def sftp_connect():
    # connect to the sftp server
    print_status("SFTP: Connecting to " + host + "\n")
    transport = paramiko.Transport((host,22))
    transport.connect(username = user, password = password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    # grab all the files in the remote directory
    all_files = sftp.listdir(remote_dir)
    for file in all_files:
        local_path = local_dir + "\\" + file
        remote_path = remote_dir + "/" + file
        sftp.get(remote_path, local_path)
        print_status("SFTP: Downloaded " + file + "\n")
        # remove copy on ftp server
        sftp.remove(remote_path)
        print_status("SFTP: Removed " + file + "on remote server.\n")
        
    # close the sftp session
    sftp.close()
    transport.close()
    print_status("SFTP: Downloads complete.\n")
  
      
###################MAIN##############################################

## open log file
#LF = open(log_file, 'w')
print_status("TIME: Starting at " + mytime + "\n")

#sftp to webserver
sftp_connect()

# close the log file when done
mytime = time.strftime("%H:%M:%S", time.localtime())
print_status("TIME: Completed at " + mytime + "\n")
#LF.close()



