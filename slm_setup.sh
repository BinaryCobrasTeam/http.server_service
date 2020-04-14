#-- File    : slm_setup.sh
#-- Author  : Eddie Florea
#-- Email   : eddie@manzama.com
#-- Version : 0.1.0
#-- Date    : 2020-04-13
#-- Company : 
#-- Credits : 
#-- License : GPLv3 
#
# --------------------------------------------------------------------------------------------------------------------------------------------

<< 'MULTILINE-COMMENT'

This script create a daemon service to run the SLM process script and execute on
sequence the 3 different sections of the SLM process. 

If you get a permission denied, don't for to :

    chmod +x slm_setup.sh    

and run as : 

    ./slm_setup.sh

MULTILINE-COMMENT

# --------------------------------------------------------------------------------------------------------------------------------------------

read -p 'Service Name: ' service_name


FILE="/lib/systemd/system/$service_name.service"

/bin/cat <<EOM >$FILE
[Unit]
Description=SLM Process Service
After=multi-user.target
Conflicts=getty@tty1.service

[Service]
Type=simple
ExecStart=/home/eddief/python-virtual-envs/mzsignals/bin/python /home/eddief/PycharmProjects/signals_test_code/slm_service.py
StandardInput=tty-force

[Install]
WantedBy=multi-user.target
EOM

# 
sudo systemctl daemon-reload

#   
sudo systemctl enable $service_name.service

#
sudo systemctl start $service_name.service