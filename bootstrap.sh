#!/usr/bin/env bash

# install base packages
yum install -y epel-release git gzip tar
yum install -y wget bzip2 bzip2-utils bzip2-devel gcc gcc-c++ hdf5 hdf5-devel 
yum install -y httpd httpd-devel 
yum install -y lzo lzo-devel cmake
yum install -y policycoreutils-python setroubleshoot

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

wget https://github.com/Blosc/c-blosc/archive/1.15.1.tar.gz
tar -zxf 1.15.1.tar.gz
rm -f 1.15.1.tar.gz
pushd c-blosc-1.15.1
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr
cmake --build . --target install
popd
rm -rf c-blosc-1.15.1

conda install -y -c conda-forge python-igraph
conda install -y -c anaconda flask
conda install -y -c conda-forge flask-restplus 

# install mod_wsgi for apache
pip install mod_wsgi

# install ndex2-client
git clone -b 'chrisdev' --single-branch --depth 1 https://github.com/ndexbio/ndex2-client.git
pushd ndex2-client
python setup.py bdist_wheel
pip install dist/ndex2-*whl
popd
rm -rf ndex2-client

# install nbgwas
git clone -b 'v0.4.1.chrisdev' --single-branch --depth 1 https://github.com/shfong/nbgwas.git
pushd nbgwas
python setup.py build
python setup.py install
popd

# install nbgwas_rest
# TODO this should install the version in /vagrant
git clone -b 'chrisdev' --single-branch --depth 1 https://github.com/idekerlab/nbgwas_rest.git
pushd nbgwas_rest
make dist
pip install dist/nbgwas*whl
# copy the http configuration file
cp nbgwas.httpconf /etc/httpd/conf.d/nbgwas.conf
popd

# install latest nodejs and npm
curl -sL https://rpm.nodesource.com/setup_10.x | sudo bash -
yum install -y nodejs

# install NBGWAS-Frontend
git clone -b 'gh-pages' --single-branch --depth 1 https://github.com/BrettJSettle/NBGWAS-Frontend.git
pushd NBGWAS-Frontend
npm install .
cat package.json | sed "s/\"homepage\":.*/\"homepage\": \"http:\/\/localhost\"/" > package.tmp
mv -f package.tmp package.json
npm run build
cp -a build/* /var/www/html/.
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
mkdir -p /var/www/nbgwas_rest/tasks/delete_requests

chown -R apache.apache /var/www/nbgwas_rest/tasks

mod_wsgi-express module-config > /etc/httpd/conf.modules.d/02-wsgi.conf

# https://www.serverlab.ca/tutorials/linux/web-servers-linux/configuring-selinux-policies-for-apache-web-servers/
# and tell SElinux its okay if apache writes to the directory
semanage fcontext -a -t httpd_sys_rw_content_t "/var/www/nbgwas_rest/tasks(/.*)?"
restorecon -Rv /var/www/nbgwas_rest/tasks

service httpd start

echo "Visit http://localhost:8081/rest/v1 in your browser"

