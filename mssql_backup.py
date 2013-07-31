#*****************************************************************#
#                                                                 #
# Filename:             mssql_backup.py                           #
# Author:               Natalie Metzger                           #
# Date Written:         11/12/2008                                #
# Modifications:        09/22/2009 - Added SFTP and MD5           #
#                       verification.                             #
#                       07/30/2013 - Modified for current         #
#                                                                 #
# Purpose:              Compresses lastest SQL backup to ZIP,     #
#                       Purges old backup, zip, and log files,    #
#                       and sends email of status.                #
#                                                                 #
# OS:          	Windows Sever 2010, 2003, 7, XP,          #
# NOTE: client.py for Paramiko module is buggy on Windows. Fixed  #
# file can be found in the Python directory Paramiko module       #
# directory on the network.                                       #
# Paramiko is a non-standard module. Manual install required.     #
# Uses 7zip.                                                      #
#                                                                 #
#*****************************************************************#

import os, sys, time, smtplib, string, popen2, subprocess, re, datetime, MimeWriter, StringIO, base64, getopt, paramiko, md5, win32wnet
from win32netcon import RESOURCETYPE_DISK as DISK

#paramiko.util.log_to_file('paramiko.log') #uncomment if logging of SFTP session is required

###################GLOBAL VARIABLES#######################################

day = time.strftime("%d", time.localtime())
today = datetime.date.today()
mydate = today.strftime("%Y%m%d")
myyear = today.strftime("%Y")
mymonth = today.strftime("%m")
myday = today.strftime("%d")
mytime = time.strftime("%H:%M:%S", time.localtime())
port = 22
error_state = ""

# Edit these values
zip_file = "DBbackup_" + myyear + "_" + mymonth + "_" + myday + "_" + "0000.zip"
#zpassword = "password"         # uncomment if zip password is required - flags will need to be added to zip call

keep_num_files = 5		# number of zip files to retain locally

local_dir = "W:"                # local directory files will be save to
drive_path = "\\\\host\\backup-dir"
dmp_file = "DBbackup_" + myyear + "_" + mymonth + "_" + myday + "_" + "0000.bak"
dmp_path = "W:\\"		# path to database backup (.bak) files on database server

log_file = "DBbackup_" + myyear + "_" + mymonth + "_" + myday + "_" + "0000.log"
log_path = "logs"       # local path to exp and zip files
logging = log_path + "\\" + log_file

SMTP_server = "mail-server-name"  #SMTP email server
email_to = "recipient@some-domain.com"   
email_from = "sender@csome-domain.com"

ftp_url = "some-domain.com"         #assuming ftp and ssh use the same url
ftp_user = "username"
ftp_pass = "password"

ssh_user = "username"
ssh_pass = "password"

###################FUNCTIONS#######################################
def usage():
    print """
mssql_backup.py [options]

  -z         Skip zip file creation.
  -d         Skip purge of old files.
  -m         Skip sending status email.
  -h         This usage page.
"""
    sys.exit()

def findcurrentbak():
    listcmd = local_dir + "\ndir\nexit\n"
    fromchild, tochild = popen2.popen4("cmd") 
    print "Running:" + listcmd
    tochild.write(listcmd)
    tochild.close()
    out = fromchild.read()
    output = string.split(out)
    fromchild.close()

    # process the output
    matchobj = ""
    for line in output:
        matchobj = re.match("(^DBbackup_" + myyear + "_" + mymonth + "_" + myday + "_" + "[0-9]+_[0-9]+\.bak)", line) #custom file format, change for your env.
        if matchobj:
            print "Found a match: " + line
            return line


def sumfile(fobj):
    '''Returns an md5 hash for an object with read() method.'''
    m = md5.new()
    while True:
        d = fobj.read(8096)
        if not d:
            break
        m.update(d)
    return m.hexdigest()


def md5sum(fname):
    '''Returns an md5 hash for file fname, or stdin if fname is "-".'''
    if fname == '-':
        ret = sumfile(sys.stdin)
    else:
        try:
            f = file(fname, 'rb')
        except:
            return 'Failed to open file'
        ret = sumfile(f)
        f.close()
    return ret

def parse_argv():    
    if len (sys.argv) > 1:
        flag = sys.argv[1]
        return flag

def print_status(mystatus):
    LF.write(mystatus)
    print mystatus

def zip_exp(skip_zip):
    #check if the database backup file exists, if so, compress
    if os.path.exists(dmp_path + "\\" + dmp_file):
        zip_call = "\"C:\\Program Files (x86)\\7-Zip\\7z.exe\" a -tzip " + log_path + "\\" + zip_file + " -p " + dmp_path + "\\" + dmp_file
        if skip_zip:
            print_status("ZIP: Skipping zip " + zip_call + "\n")
        else:
            print_status("ZIP: Compressing " + zip_call + "\n")
            p = subprocess.Popen(zip_call, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.stdin.write(zpassword + "\n")
            zip_read = p.stdout.read()
            p.stdin.close()
            p.stdout.close()
            print_status("ZIP: " + zip_file + " created\n")
    else:
        print_status("ZIP: " + dmp_path + "\\" + dmp_file + " doesn't exist, skipping zip. Check login status. Login to server is required for mapped drive detection.\n")
        error_state = " - Errors encountered (see log file for details)"

def sftp_file():
    #grab the md5sum for the logs
    localmd5 = md5sum(log_path + "\\" + zip_file)
    print_status("MD5: Local md5sum is - " + localmd5 + "\n")

    #sftp to offsite host and transfer backup ZIP file
    transport = paramiko.Transport((ftp_url, port))
    transport.connect(username = ftp_user, password = ftp_pass)
    sftp = paramiko.SFTPClient.from_transport(transport)
    sftp.put(log_path + "\\" + zip_file, "archive/" + zip_file)
    print_status("SFTP: Transfered " + zip_file + "\n")
    sftp.close()
    transport.close()
    return localmd5
    
def ssh_to_host():
    remote_cmd = "md5sum backup/db/archive/" + zip_file         # customize path for your env.
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ftp_url, username=ssh_user, password=ssh_pass)
    stdin, stdout, stderr = ssh.exec_command(remote_cmd)
    cmdout = stdout.read()
    remotemd5 = cmdout[0:32]
    ssh.close()
    print_status("MD5: Remote md5sum is - " + remotemd5 + "\n")
    return remotemd5

def prune(delfiles):
    for file in delfiles:
        #remove the files locally
        prune_cmd = "del /F /Q " + dmp_path + "\\" + file
        print_status("PRUNE: Deleteing: " + prune_cmd + "\n")
        prune_fd = os.popen(prune_cmd)
        prune_fd.close()
        
        zfile = file.replace('bak', 'zip', 1)
        if os.path.exists(log_path + "\\" + zfile):
            zprune_cmd = "del /F /Q " + log_path + "\\" + zfile
            print_status("PRUNE: Deleteing: " + zprune_cmd + "\n")
            lprune_fd = os.popen(zprune_cmd)
            lprune_fd.close()
        else:
            print_status("PRUNE: " + zfile + " does not exist, skipping\n")
            error_state = " - Errors encountered (see log file for details)"

        lfile = file.replace('bak', 'log', 1)
        if os.path.exists(log_path + "\\" + lfile):
            lprune_cmd = "del /F /Q " + log_path + "\\" + lfile
            print_status("PRUNE: Deleteing: " + lprune_cmd + "\n")
            lprune_fd = os.popen(lprune_cmd)
            lprune_fd.close()
        else:
            print_status("PRUNE: " + lfile + " does not exist, skipping\n")
            error_state = " - Errors encountered (see log file for details)"

        #remove the files remotely (customize path for your env.)
        transport = paramiko.Transport((ftp_url, port))
        transport.connect(username = ftp_user, password = ftp_pass)
        sftp = paramiko.SFTPClient.from_transport(transport)
        for item in sftp.listdir("archive/"):
            if item == zfile:
                sftp.remove("archive/" + zfile)
                print_status("PRUNE: Deleteing Remotely: " + zfile + "\n")
         
        sftp.close()
        transport.close()

      
def mail(serverURL=None, sender='', to='', subject='', text=''):
    message = StringIO.StringIO()
    writer = MimeWriter.MimeWriter(message)
    writer.addheader('Subject', subject)
    writer.startmultipartbody('mixed')

    # start off with a text/plain part
    part = writer.nextpart()
    body = part.startbody('text/plain')
    body.write(text)

    # now add an attachment
    part = writer.nextpart()
    part.addheader('Content-Transfer-Encoding', 'base64')
    body = part.startbody('text/plain; name=%s' % log_file)
    base64.encode(open(logging, 'rb'), body)

    # finish off
    writer.lastpart()

    # send the mail
    smtp = smtplib.SMTP(serverURL)
    smtp.sendmail(sender, to, message.getvalue())
    smtp.quit()
   

###################MAIN############################################

win32wnet.WNetAddConnection2(DISK,local_dir,drive_path) # connect to drive

# process argv
flag = parse_argv()
skip_zip, skip_delete, skip_mail = 0, 0, 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "zdmh", ["zip","delete","mail","help"])

    for o, a in opts:
        if o in ("-z", "--zip"):
            skip_zip = 1
        if o in ("-d", "--delete"):
            skip_delete = 1
        if o in ("-m", "--mail"):
            skip_mail = 1
        if o in ("-h", "--help"):
            usage()
 
except getopt.GetoptError, err:
    print "ERROR!\nIncorrect options"
    usage()

# open log file
LF = open(logging, 'w')
print_status("TIME: Starting at " + mytime + "\n")
error_state = ""

dmp_file = findcurrentbak()

#create the zip file from the export file
zip_exp(skip_zip)

#get local MD5 and SFTP the ZIP file to remote host
localmd5 = sftp_file()

#get remote MD5
remotemd5 = ssh_to_host()

#compare MD5 checksums
if localmd5 == remotemd5:
    print_status("MD5: Checksums match.\n")
else:
    print_status("MD5: Checksums do not match" + localmd5 + "!=" + remotemd5 + "\n")
    error_state = " - Errors encountered (see log file for details)"
    
listcmd = dmp_path + "\nchdir " + dmp_path + "\ndir\nexit\n"
fromchild, tochild = popen2.popen4("cmd") 
tochild.write(listcmd)
tochild.close()
out = fromchild.read()
output = string.split(out)
fromchild.close()

# process the output
if skip_delete:
    print_status ("PRUNE: Skipping file parsing and pruning\n")
else:
    matchobj = ""
    allzipfiles = []
    for line in output:
        matchobj = re.match("(^CADET7_backup_[0-9]+\.bak)", line)
        if matchobj:
            zipfiles = matchobj.groups()
            allzipfiles.append(zipfiles[0])

    #get the length of the zip file list, if it is > 5, delete old files
    #sort to make sure they are in the correct order
    allzipfiles.sort()
    listlen = len(allzipfiles)

    delfiles=[]
    if listlen > 5:
        numfiles = listlen - 5
        delfiles = allzipfiles[0:numfiles]
    
    #remove these files 
    if delfiles:
        print_status("PRUNE: Found files to prune\n")
        prune(delfiles)

# close the log file when done
mytime = time.strftime("%H:%M:%S", time.localtime())
print_status("TIME: Completed at " + mytime + "\n")

# email a notification
if skip_mail:
    print_status("MAIL: Skipping sending status email\n")
    LF.close()
else:
    print_status("MAIL: Status email sent\n")
    LF.close()
    mail(SMTP_server,email_from,email_to,'Database ZIP of BAK Complete' + error_state,'DB zip and ftp of database dump is complete\n')

# disconnect the drive
win32wnet.WNetCancelConnection2(local_dir, 0, 0)
