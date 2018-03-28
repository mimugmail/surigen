# surigen
Suricata Rulegenerator

This software is forked from bl2ru2 https://github.com/conix-security/bl2ru2

Feel free to fork, push PRs or do whatever with it! 


How to build the OPNsense rules:

surigen.py -o opnsense.social-media.rules -s 51000000 -e OPN_Social_Media social-media.lst
surigen.py -o opnsense.messaging.rules -s 52000000 -e OPN_Messaging messaging.lst
surigen.py -o opnsense.file-transfer.rules -s 53000000 -e OPN_File_Transfer file-transfer.lst
surigen.py -o opnsense.mail.rules -s 54000000 -e OPN_Mail mail.lst
