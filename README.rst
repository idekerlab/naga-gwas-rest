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


REST service for `Network Boosted Genome Wide Association Studies (NBGWAS) <https://github.com/shfong/nbgwas/>`_

`For more information please click here to visit our wiki <https://github.com/coleslaw481/nbgwas_rest/wiki>`_

Compatibility
-------------

 * Tested with Python 3.6 in Anaconda_

Dependencies to run
-------------------

 * nbgwas_
 * `requests <https://pypi.org/project/requests/>`_
 * `networkx <https://pypi.org/project/networkx/>`_
 * `numpy <https://pypi.org/project/numpy/>`_
 * `matplotlib <https://pypi.org/project/matplotlib/>`_
 * `pandas <https://pypi.org/project/pandas/>`_
 * `ndex2 <https://pypi.org/project/ndex2/>`_
 * `flask <https://pypi.org/project/flask/>`_
 * `flask-restplus <https://pypi.org/project/flast-restplus>`_
 * `scipy <https://www.scipy.org/>`_
 * `seaborn <https://seaborn.pydata.org/>`_
 * `tables <https://pypi.org/project/tables/>`_
 * `python-igraph <http://igraph.org/python/>`_
 * `py2cytoscape <https://pypi.org/project/py2cytoscape/>`_

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


Bugs
-----

Please report them `here <https://github.com/coleslaw481/nbgwas_rest/issues>`_

Acknowledgements
----------------

* Original implementation by `Samson Fong <https://github.com/shfong>`_

* Initial template created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _nbgwas: https://github.com/shfong/nbgwas
.. _Anaconda: https://www.anaconda.com/
