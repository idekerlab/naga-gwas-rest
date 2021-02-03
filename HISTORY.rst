=======
History
=======

0.7.1 (2021-02-03)
------------------

* Minor changes to enable naga_taskrunner.py to run as a systemd service on centos7 boxes

0.7.0 (2019-07-01)
------------------

* Added dm6 in list of valid protein coding region files

0.6.0 (2019-05-06)
------------------

* Added mm10 and rn6 in list of valid protein coding region files

0.5.0 (2019-03-07)
------------------

* Replace infinite heat values returned from NAGA bug
  `issue #24 <https://github.com/idekerlab/naga-gwas-rest/issues/23>`_

* Add naga version used in processing to result json
  `issue #23 <https://github.com/idekerlab/naga-gwas-rest/issues/23>`_

* Rename to naga-gwas-rest
  `issue #22 <https://github.com/idekerlab/naga-gwas-rest/issues/22>`_

* Add input parameters snp_analyzer/get endpoint enhancement
  `issue #20 <https://github.com/idekerlab/naga-gwas-rest/issues/20>`_

* Modify naga_taskrunner.py to run in a daemon mode
  `issue #3 <https://github.com/idekerlab/naga-gwas-rest/issues/3>`_


0.4.1 (2018-12-20)
------------------

* Replace Association with Analysis in REST service description bug
  `issue #19 <https://github.com/idekerlab/naga-gwas-rest/issues/19>`_

0.4.0 (2018-12-19)
------------------

* Enabled DELETE rest endpoint `issue #16 <https://github.com/idekerlab/naga-gwas-rest/issues/16>`_

* Fixed problems including numpy and running under apache modwsgi bug
  `issue #15 <https://github.com/idekerlab/naga-gwas-rest/issues/15>`_

* nbgwas_taskrunner.py should remove snp level summary file after job runs
  `issue #5 <https://github.com/idekerlab/naga-gwas-rest/issues/5>`_

0.1.1 (2018-11-30)
------------------

* First release onto github
