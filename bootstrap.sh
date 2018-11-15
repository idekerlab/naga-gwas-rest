#!/usr/bin/env bash

# install base packages
yum install -y epel-release git gzip tar

# open port 5000 for http
firewall-cmd --permanent --add-port=5000/tcp

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
conda install -y -c conda-forge flask-restful

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

git clone https://github.com/coleslaw481/nbgwas_rest.git
pushd nbgwas_rest
python setup.py install
popd
