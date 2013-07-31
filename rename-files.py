import os, time, operator, sys, getopt, stat, re, fnmatch
gmt = time.gmtime(time.time())
thisyear = time.strftime('%Y',gmt)
matches = []
path, cutoff, sortby, verbose, check, newpath, newname = "", 0, "", 0, 0, "", ""
badchars = '#\\/:*?"<>|{}~#%&'

#These are the invalid characters for SharePoint:
#o  Folder Names and File Names
#o	Do not use: " # % & * : < > ? \ / { | } ~
#o	File names cannot be longer than 128 characters
#o	Do not use the period character consecutively in the middle of a file name.  For example, "file..name.docx" is invalid.
#o	You cannot use the period character at the end of a file name
#o	You cannot start a file name with the period character

print badchars + "\n"

def rename_recursive(srcpath):
    srcpath = os.path.normpath(srcpath)
    if os.path.isdir(srcpath):
        newpath = rename_file(srcpath)
                 
        # recurse to the contents
        for entry in os.listdir(newpath): #FIXME newpath
            nextpath = os.path.join(newpath, entry)
            rename_recursive(nextpath)
    elif os.path.isfile(srcpath): # base case
        rename_file(srcpath)
    else: # error
        print "bad arg: " + srcpath
        sys.exit()

def rename_file(srcpath):
    srcdir, srcname = os.path.split(srcpath)
    print "Checking file: " + srcname
    newname = re.sub("#|&|%|\"|\||/|:|\*|\?|\(|\)|~|>|<|(.{128,500})","",srcname)
    ### UNCOMMENT THIS TO OVERWRITE MATCHED FILENAMES
    #toolong = re.search("(.{128,500})",srcname)
    #if toolong:
    #    print "found a toolong: " + toolong.group(1)
    #    save_results.write(srcpath + "\n")
    if newname == srcname:
        return srcpath
    newpath = os.path.join(srcdir, newname)
    print "Renamed " + srcpath + " to " + newpath
    save_results.write(srcpath + "\n")
    ### UNCOMMENT THIS TO OVERWRITE MATCHED FILENAMES
    #os.rename(srcpath, newpath)
    return srcpath

arg = sys.argv[1]
arg = os.path.expanduser(arg)
save_results = open('Found_files.txt','w')
rename_recursive(arg)
save_results.close()
