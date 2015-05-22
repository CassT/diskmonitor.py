# diskmonitor.py
Monitors health of disks in zpool by checking for iostat errors and scsi target errors.
Sends email to recipients when it finds disks with iostat or scsi errors in the zpool.
Requires lsiutil.i386 and iostat.
