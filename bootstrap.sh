#!/usr/bin/env bash

# install base packages
yum install -y epel-release git gzip tar
yum install -y wget bzip2 bzip2-utils bzip2-devel gcc gcc-c++ hdf5 hdf5-devel 
yum install -y httpd httpd-devel 
yum install -y lzo lzo-devel cmake screen
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

conda install -y scipy
conda install -y numpy
conda install -y -c conda-forge python-igraph
conda install -y -c anaconda flask
conda install -y -c conda-forge flask-restplus 

# install mod_wsgi for apache
pip install mod_wsgi

# install biothings_client cause it was not installed automatically by mygene for some reason
pip install biothings_client

# install ndex2-client
pip install ndex2

pip install naga-gwas==0.4.1

# install nbgwas_rest
# TODO this should install the version in /vagrant
git clone -b 'chrisdev' --single-branch --depth 1 https://github.com/idekerlab/nbgwas_rest.git
pushd nbgwas_rest
make dist
pip install dist/nbgwas*whl
# copy the http configuration file
cp nbgwas.httpconf /etc/httpd/conf.d/nbgwas.conf
cp -r nagadata /var/www/html/.
gunzip /var/www/html/nagadata/*.gz
gunzip /var/www/html/nagadata/protein_coding/*.gz
gunzip /var/www/html/nagadata/example_output/*.gz
popd

# install latest nodejs and npm
curl -sL https://rpm.nodesource.com/setup_10.x | sudo bash -
yum install -y nodejs

# install NBGWAS-Frontend
git clone -b 'chrisdev' --single-branch --depth 1 https://github.com/BrettJSettle/NBGWAS-Frontend.git
pushd NBGWAS-Frontend
npm install .
cat package.json | sed "s/\"homepage\":.*/\"homepage\": \"http:\/\/localhost:8081\"/" > package.tmp
mv -f package.tmp package.json
cat src/data.js | sed "s/endpoint:.*/endpoint: \"http:\/\/localhost:8081\/rest\/v1\/snp_analyzer\",/g" > data.js.tmp
mv -f data.js.tmp src/data.js
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
mkdir -p /var/www/nbgwas_rest/tasks/protein_coding_dir
cp /var/www/html/nagadata/protein_coding/hg*txt /var/www/nbgwas_rest/tasks/protein_coding_dir/.

chown -R apache.apache /var/www/nbgwas_rest/tasks

mod_wsgi-express module-config > /etc/httpd/conf.modules.d/02-wsgi.conf

# https://www.serverlab.ca/tutorials/linux/web-servers-linux/configuring-selinux-policies-for-apache-web-servers/
# and tell SElinux its okay if apache writes to the directory
semanage fcontext -a -t httpd_sys_rw_content_t "/var/www/nbgwas_rest/tasks(/.*)?"
restorecon -Rv /var/www/nbgwas_rest/tasks

service httpd start

echo "To process jobs connect via vagrant ssh and run the following as vagrant user or root:"
echo ""
echo "screen"
echo "sudo -u apache /bin/bash"
echo 'export PATH=/opt/miniconda3/bin:$PATH'
echo "nbgwas_taskrunner.py -vv --wait_time 1 --protein_coding_dir /var/www/nbgwas_rest/tasks/protein_coding_dir /var/www/nbgwas_rest/tasks"
echo "# Type <Ctrl>-a d to exit screen and screen -r to resume"
echo ""
echo ""
echo "Visit http://localhost:8081/rest/v1 in your browser"

