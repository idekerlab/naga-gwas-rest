==============
naga-gwas-rest
==============


.. image:: https://img.shields.io/pypi/v/naga-gwas-rest.svg
        :target: https://pypi.python.org/pypi/naga-gwas-rest

.. image:: https://img.shields.io/travis/idekerlab/naga-gwas-rest.svg
        :target: https://travis-ci.org/idekerlab/naga-gwas-rest




REST service for `Network Assisted Genomic Analysis (NAGA) <https://github.com/shfong/naga/>`_

`For more information please click here to visit our wiki <https://github.com/idekerlab/naga-gwas-rest/wiki>`_

This service is currently running here: http://nbgwas.ucsd.edu

Compatibility
-------------

 * Tested with Python 3.6 in Anaconda_

Dependencies to run
-------------------

 * `naga-gwas <https://pypi.org/project/naga-gwas/>`_
 * `ndex2 <https://pypi.org/project/ndex2/>`_
 * `python-daemon <https://pypi.org/project/python-daemon/>`_
 * `flask <https://pypi.org/project/flask/>`_
 * `flask-restplus <https://pypi.org/project/flast-restplus>`_
 * `numpy <https://pypi.org/project/numpy>`_

Additional dependencies to build
--------------------------------

 * GNU make
 * `wheel <https://pypi.org/project/wheel/>`_
 * `setuptools <https://pypi.org/project/setuptools/>`_
 

Installation
------------

It is highly reccommended one use `Anaconda <https://www.anaconda.com/>`_ for Python environment

.. code:: bash

  git clone https://github.com/idekerlab/naga-gwas-rest.git
  cd naga-gwas-rest
  make install

Running service in development mode
-----------------------------------


**NOTE:** Example below runs the REST service and not the task runner.

.. code:: bash

  # It is assumed the application has been installed as described above
  export FLASK_APP=nbgwas_rest
  flask run # --host=0.0.0.0 can be added to allow all access from interfaces
  
  # Service will be running on http://localhost:5000

  # NOTE: To have tasks processed naga_taskrunner.py must be started in
  # another terminal


`Click here for information on launching service via Vagrant VM <https://github.com/idekerlab/naga-gwas-rest/wiki/NAGA-REST-under-Vagrant-Virtual-Machine>`_


Example usage of service
------------------------

Below is a small script that leverages the nbgwas_rest service to run NAGA on the
compressed **nagadata/schizophrenia.txt.gz** passed into the script on the command line

.. code:: bash

    #!/usr/bin/env python

    import sys
    import gzip
    import time
    import requests

    # pass the gzipped schizophrenia.txt.gz
    networkfile = sys.argv[1]

    # set parameters
    data_dict = {}
    data_dict['protein_coding']='hg18'
    data_dict['window']=10000
    data_dict['ndex']='f93f402c-86d4-11e7-a10d-0ac135e8bacf'

    # set snp file
    files = {'snp_level_summary': gzip.open(networkfile, 'rb')}
    url = 'http://nbgwas.ucsd.edu/rest/v1/snp_analyzer'
    r = requests.post(url, data=data_dict, files=files,
                      timeout=30)

    # If successful the previous POST will return 202
    if r.status_code != 202:
        sys.stderr.write('Submission failed with code: ' + str(r.status_code) +
                         '\n')
        sys.stderr.write('Message: ' + str(r.text) + '\n')
        sys.exit(1)

    # If successful Location will be set to a URL that can
    # be polled for result
    if 'Location' not in r.headers:
        sys.stderr.write('Expected Location in Header, ' +
                         'but its not there: ' + str(r.headers) + '\n')
        sys.exit(2)

    resulturl = r.headers['Location']
    getres = requests.get(resulturl, timeout=30)
    json_res = getres.json()
    while getres.status_code != 200 or json_res['status'] == 'submitted' or json_res['status'] == 'processing':
       sys.stderr.write('.')
       sys.stderr.flush()
       time.sleep(5)
       getres = requests.get(resulturl, timeout=30)
       json_res = getres.json()

    sys.stderr.write('\n')
    sys.stdout.write(str(json_res) + '\n')

Assuming the above is saved in a file named **foo.py** and run from base directory of this source tree


.. code:: bash

  ./foo.py nagadata/schizophrenia.txt.gz


Example output:

.. code:: bash

   {'result': {'A1BG': 1.818739214334769, 'A1CF': 2.9679830980888413,
   'A2M': 3.9294999566765174, 'A2ML1': 1.4379620790934335, 'A3GALT2': 1.9918435374785632,
   'A4GALT': 1.8734641163972634, 'A4GNT': 1.335302470858104, 'AAAS': 2.384799543926567,
   'AACS': 2.965792987307328, 'AADAC': 1.455957465785784, 'AADACL2': 1.0156608351922358,
   'AADACL3': 0.895944981993654, 'AADACL4': 1.2458363441128992, 'AADAT': 2.689141678947707,
   'AAED1': 0.12364477699188797, 'AAGAB': 0.14237051805828474, 'AAK1': 5.652340641567231,
   'AAMDC': 0.1647736242197245, 'AAMP': 3.2927511707526884, 'AANAT': 5.654764562774087,
   'AAR2': 0.9427896961129361,
   .
   .
   , 'status': 'done'}

Bugs
-----

Please report them `here <https://github.com/idekerlab/naga-gwas-rest/issues>`_

Acknowledgements
----------------

* Original implementation by `Samson Fong <https://github.com/shfong>`_

* Initial template created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _Anaconda: https://www.anaconda.com/
