The instructions in this readme provide steps
to install naga_taskrunner.py as a service managed by systemd.
These instructions use the files in this directory and require
a centos 7 box with superuser access.

# Requirements

* miniconda3 is installed in /opt/miniconda3 with naga and naga-gwas-rest packages installed
* nagarunner user added to box and added to apache group
* apache user added to nagarunner group
* These configuration files assume tasks will be stored in
  /var/www/nbgwas_rest/tasks directory
* set sticky bit (chmod g+s) on tasks directory and subdirectories
  (chmod -R g+s /var/www/nbgwas_rest/tasks)

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

ps -elf | grep naga

# output
4 S nagarun+ 15010     1  0  80   0 - 207903 poll_s 11:43 ?       00:00:02 /opt/miniconda3/bin/python /opt/miniconda3/bin/naga_taskrunner.py --wait_time 1 --logconfig /etc/naga-taskrunner.conf --protein_coding_dir /var/www/nbgwas_rest/tasks/protein_coding_dir /var/www/nbgwas_rest/tasks

