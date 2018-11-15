===========
nbgwas_rest
===========


.. image:: https://img.shields.io/pypi/v/nbgwas_rest.svg
        :target: https://pypi.python.org/pypi/nbgwas_rest

.. image:: https://img.shields.io/travis/coleslaw481/nbgwas_rest.svg
        :target: https://travis-ci.org/coleslaw481/nbgwas_rest

.. image:: https://readthedocs.org/projects/nbgwas-rest/badge/?version=latest
        :target: https://nbgwas-rest.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status


REST service for Network Boosted GWAS


Compatibility
-------------

 * Works with Python 3.6, 3.7

Dependencies to run
-------------------

 * `nbgwas <https://github.com/shfong/nbgwas/>`_
 * `requests <https://pypi.org/project/requests/>`_
 * `networkx <https://pypi.org/project/networkx/>`_
 * `numpy <https://pypi.org/project/numpy/>`_
 * `matplotlib <https://pypi.org/project/matplotlib/>`_
 * `pandas <https://pypi.org/project/pandas/>`_
 * `ndex2 <https://pypi.org/project/ndex2/>`_
 * `flask <https://pypi.org/project/flask/>`_
 * `flask-restful <https://pypi.org/project/flast-restful/>`_

Additional dependencies to build
--------------------------------

 * GNU make
 * `wheel <https://pypi.org/project/wheel/>`_
 * `setuptools <https://pypi.org/project/setuptools/>`_
 

Installation
------------

It is highly reccommended one use `Anaconda <https://www.anaconda.com/>`_ for Python environment

.. code:: bash

  git clone https://github.com/coleslaw481/nbgwas_rest.git
  cd nbgwas_rest
  make install

Running server in development mode
----------------------------------

.. code:: bash

  # It is assumed the application has been installed as described above
  export FLASK_APP=nbgwas_rest
  flask run # --host=0.0.0.0 can be added to allow all access from interfaces
  
  # Service will be running on http://localhost:5000/nbgwas

Example usage of service
------------------------

Below is a small quick and dirty script that leverages the nbgwas_rest service to run nbgwas on a tab delimited file passed into the script on the command line

.. code:: bash

   #!/usr/bin/env python

   import sys
   import requests

   # pass 3 column tab delimited file to this script
   networkfile = sys.argv[1]

   data_dict = {}

   data_dict['seeds']='geneone,genetwo'
   data_dict['alpha']=0.2
   files = {'network': open(networkfile, 'rb')}
   url = 'http://localhost:5000/nbgwas'
   r = requests.post(url, data=data_dict, files=files)
   sys.stdout.write(str(r.text) + '\n')
   sys.stdout.write(str(r.status_code) + '\n')

Assuming the above is saved in a file named foo.py

.. code:: bash

  ./foo.py mytsv.tsv


Running server under VM via Vagrant
-----------------------------------

These instructions will automatically install and configure nbgwas_rest and `nbgwas <https://github.com/shfong/nbgwas>`_ on a virtual machine and are the easiest way to get the system running. `Vagrant <https://https://www.vagrantup.com/>`_ and `Virtualbox <https://https://www.virtualbox.org/>`_ must installed prior to running the following commands:

.. code:: bash

  git clone https://github.com/coleslaw481/nbgwas_rest.git
  cd nbgwas_rest

  # launch Virtual Machine
  vagrant up

  # connect to Virtual Machine via ssh
  vagrant ssh

  # start nbgwas rest service
  export FLASK_APP=nbgwas_rest
  flask run --host=0.0.0.0

  # From host compute service will be running on http://localhost:5000/nbgwas
  
  # To destroy virtual machine run from nbgwas_rest directory on host computer
  vagrant destroy

Bugs
-----

Please report them `here <https://github.com/coleslaw481/nbgwas_rest/issues>`_

Acknowledgements
----------------

* Initial template created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
