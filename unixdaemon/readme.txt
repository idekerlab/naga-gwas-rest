The instructions in this readme provide steps
to install nbgwas_taskrunner.py as a service managed by systemd.
These instructions use the files in this directory and require
a centos 7 box with superuser access.

# Requirements

* nagarunner user added to box and added to apache group
* apache user added to nagarunner group


1) Create needed log directory

mkdir /var/log/naga-taskrunner
chown nagarunner.nagarunner /var/log/naga-taskrunner

2) Create conf file

Copy naga-taskrunner.conf to /etc

3) Create systemd file

Copy naga-taskrunner.service to /lib/systemd/system
cd /lib/systemd/system
chmod 777 naga-taskrunner.service


4) Register script with systemd

systemctl daemon-reload
cd /lib/systemd/system
systemctl enable naga-taskrunner
systemctl start naga-taskrunner

5) Verify its running

ps -elf | grep ddot

# output
4 S nagarun+ 15010     1  0  80   0 - 207903 poll_s 11:43 ?       00:00:02 /opt/miniconda3/bin/python /opt/miniconda3/bin/naga_taskrunner.py --wait_time 1 --logconfig /etc/naga-taskrunner.conf /var/www/naga_rest/tasks

