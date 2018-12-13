#!/usr/bin/env bash

# install base packages
yum install -y epel-release git gzip tar
yum install -y wget bzip2 bzip2-utils bzip2-devel gcc gcc-c++ hdf5 hdf5-devel httpd httpd-devel lzo lzo-devel blosc-devel blosc

# open port 5000 for http
firewall-cmd --permanent --add-port=5000/tcp

# open port 80 for http
firewall-cmd --permanent --add-port=80/tcp

# open port 8000 for http
firewall-cmd --permanent --add-port=8000/tcp

# restart firewalld
service firewalld restart

# install miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
chmod a+x Miniconda3-latest-Linux-x86_64.sh

# install miniconda
./Miniconda3-latest-Linux-x86_64.sh -p /opt/miniconda3 -b
rm ./Miniconda3-latest-Linux-x86_64.sh

# set path to miniconda -- should really add to /etc/profile.d so everyone gets it
export PATH=/opt/miniconda3/bin:$PATH
echo "export PATH=/opt/miniconda3/bin:$PATH" >> /root/.bash_profile
echo "export PATH=/opt/miniconda3/bin:$PATH" >> /root/.bashrc
sudo -u vagrant echo "export PATH=/opt/miniconda3/bin:$PATH" >> /home/vagrant/.bash_profile

conda install -y -c conda-forge python-igraph
conda install -y -c anaconda flask
conda install -y -c conda-forge flask-restplus 

pip install mod_wsgi

git clone https://github.com/ndexbio/ndex2-client.git
pushd ndex2-client
git checkout chrisdev
python setup.py bdist_wheel
pip install dist/ndex2-*whl
popd

git clone https://github.com/shfong/nbgwas.git
pushd nbgwas
git checkout api
rm -rf app
python setup.py build
python setup.py install
popd

git clone https://github.com/idekerlab/nbgwas_rest.git
pushd nbgwas_rest
git checkout taskbased
make dist
pip install dist/nbgwas*whl
cp nbgwas.httpconf /etc/httpd/conf.d/nbgwas.conf
popd

mkdir /var/www/nbgwas_rest

# write the WSGI file
cat <<EOF > /var/www/nbgwas_rest/nbgwas.wsgi
#!/usr/bin/env python

import os
os.environ['NBGWAS_REST_SETTINGS']="/var/www/nbgwas_rest/nbgwas.cfg"

from nbgwas_rest import app as application
EOF

# write the configuration file
cat <<EOF > /var/www/nbgwas_rest/nbgwas.cfg
JOB_PATH="/var/www/nbgwas_rest/tasks"
WAIT_COUNT=600
SLEEP_TIME=1
EOF


mkdir -p /var/www/nbgwas_rest/tasks/submitted
mkdir -p /var/www/nbgwas_rest/tasks/processing
mkdir -p /var/www/nbgwas_rest/tasks/done

chown -R apache.apache /var/www/nbgwas_rest/tasks

mod_wsgi-express module-config > /etc/httpd/conf.modules.d/02-wsgi.conf

# and tell SElinux its okay if apache writes to the directory

chcon -R -t httpd_sys_rw_content_t /var/www/nbgwas_rest/tasks

