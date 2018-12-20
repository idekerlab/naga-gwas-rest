===========
nbgwas_rest
===========


.. image:: https://img.shields.io/pypi/v/nbgwas_rest.svg
        :target: https://pypi.python.org/pypi/nbgwas_rest

.. image:: https://img.shields.io/travis/idekerlab/nbgwas_rest.svg
        :target: https://travis-ci.org/idekerlab/nbgwas_rest




REST service for `Network Assisted Genomic Analysis (NAGA) <https://github.com/shfong/nbgwas/>`_

`For more information please click here to visit our wiki <https://github.com/idekerlab/nbgwas_rest/wiki>`_

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

  git clone https://github.com/idekerlab/nbgwas_rest.git
  cd nbgwas_rest
  make install

Running server in development mode
----------------------------------

.. code:: bash

  # It is assumed the application has been installed as described above
  export FLASK_APP=nbgwas_rest
  flask run # --host=0.0.0.0 can be added to allow all access from interfaces
  
  # Service will be running on http://localhost:5000

  # NOTE: To have tasks processed nbgwas_taskrunner.py must be started in
  # another terminal

Example usage of service
------------------------

Below is a small quick and dirty script that leverages the nbgwas_rest service to run NAGA on the compressed **nagadata/schizophrenia.txt.gz** passed into the script on the command line

.. code:: bash

   #!/usr/bin/env python

   import sys
   import gzip
   import requests

   # pass the gzipped schizophrenia.txt.gz
   networkfile = sys.argv[1]

   data_dict = {}

   data_dict['protein_coding']='hg18'
   data_dict['window']=10000
   files = {'network': open(networkfile, 'rb')}
   url = 'http://localhost:5000/snp_analyzer'
   r = requests.post(url, data=data_dict, files=files)
   sys.stdout.write(str(r.text) + '\n')
   sys.stdout.write(str(r.status_code) + '\n')

Assuming the above is saved in a file named **foo.py** and run from base directory of this source tree

.. code:: bash

  ./foo.py nagadata/schizophrenia.txt.gz


Bugs
-----

Please report them `here <https://github.com/idekerlab/nbgwas_rest/issues>`_

Acknowledgements
----------------

* Original implementation by `Samson Fong <https://github.com/shfong>`_

* Initial template created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _nbgwas: https://github.com/shfong/nbgwas
.. _Anaconda: https://www.anaconda.com/
