# Reboot a remote server

import os, subprocess, sys, time
  
if __name__=='__main__':
    AllMachines = ['server1','server2','server3']
    
    # Create output log file
    outFile = os.path.join(os.curdir, "output.log")
    outptr = file(outFile, "w")

    # Create error log file
    errFile = os.path.join(os.curdir, "error.log")
    errptr = file(errFile, "w")

    
    for machine in AllMachines:
        Command = ["shutdown", "-r", "-m \\", machine]
        print 'rebooting ' + machine
        subprocess.call( Command, 0, None, None, outptr, errptr ) 

    # Close log handles
    errptr.close()
    outptr.close()
