#!/usr/bin/env python
import os
from datetime import date, timedelta
import time


# for each machine, record base of disk id and number of mpt_sas options for lsiutil
host_vars = {'hostnamegoeshere':('',0),} ## format str(hostname):(str(startofWWN), int(number of sas options in lsiutil))
host = os.popen('hostname').read().split('\n')[0]
diskid_start = host_vars[host][0]
mpt_sasOption = host_vars[host][1]


# Get list of drives in zpool, these are currently installed disks
zdrives = os.popen('zpool status | grep ONLINE | grep ' + diskid_start + " | awk '{print $1}'" ).read().split('\n')

bad_drives = []
# Check iostats for disk errors
iostats = os.popen("iostat -xne | grep " + diskid_start + " | awk '{print $14, $15}'").read().split('\n')
for stat in iostats:
    s = stat.split(' ')
    error_count = s[0]
    if len(s) > 1:
        disk_id = s[1]
        if int(error_count) > 0 and disk_id in zdrives:
            bad_drives.append( ('total iostat errors: ' + error_count  , disk_id) )


# Check /var/adm/messages for scsi errors
scsi_log = '/var/adm/messages'
today = date.today().strftime("%b %d")
y = date.today() - timedelta(1)
yesterday = y.strftime("%b %d")
bad_targets = []
scsi_logs = os.popen("cat " + scsi_log + " | grep target | grep \"" + today + "\\|" + yesterday  + "\" | awk '{print $11}'").read().split('\n')
for target in scsi_logs:
    if len(target) > 0:
        t = target[:len(target)-1]
        if t not in bad_targets:
            print "found bad target " + t
            bad_targets.append(t)


# Use lsiutil.i386 to get disk id from target number
for target in bad_targets:
    for item in range(1,mpt_sasOption+1):
        os.system('rm /tmp/input.txt')
        input_file = open('/tmp/input.txt','w')
        commands = str(item) + '\ne\n20\n1\n0\n'+target+'\n0\n83\n'
        input_file.write(commands)
        input_file.close()
        serial_part = os.popen('lsiutil.i386 < /tmp/input.txt | grep "0000 :" | awk \'{print ($13)($14)($15)($16)($17)($18)}\'').read().split('\n')[0]
        if serial_part != '':
            break
    # now use the partial serial number to get full WWN
    if serial_part != '':
        for wwn in zdrives:
            if serial_part.lower() in wwn.lower():
                bad_drives.append( ('scsi error: target ' + target, wwn) )


def sendMail(recipient, sender, message, host): 
    sendmail_location = "/usr/sbin/sendmail" # sendmail location
    p = os.popen("%s -t" % sendmail_location, "w")
    p.write("From: %s\n" % sender )
    p.write("To: %s\n" % recipient)
    p.write("Subject: disk errors detected on " + host + "\n")
    p.write("\n") # blank line separating headers from body
    p.write(message)
    p.close()

# Finally, turn on the led for each bad disk, and send email notification to sysadmins
recipients = ''
message = ""
for disk in bad_drives:
    message += disk[0]+" on disk "+disk[1]+"\n"
if "target" in message:
    message += "\nNote that diskmonitor may continue reporting scsi target errors for up to one day after replacing bad disk."
if message != "":
    message += "\ndiskmonitor run at "+time.strftime("%H:%M, %b %d")
    sendMail(recipients, "diskmonitor@"+host+".colorado.edu", message, host)
