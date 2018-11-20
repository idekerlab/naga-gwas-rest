#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `nbgwas_rest` package."""


import os
import sys
import json
import unittest
import shutil
import tempfile
import re
import io
import uuid

import nbgwas_rest


class TestNbgwas_rest(unittest.TestCase):
    """Tests for `nbgwas_rest` package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        self._temp_dir = tempfile.mkdtemp()
        nbgwas_rest.app.testing = True
        nbgwas_rest.app.config[nbgwas_rest.JOB_PATH_KEY] = self._temp_dir
        nbgwas_rest.app.config[nbgwas_rest.WAIT_COUNT_KEY] = 1
        nbgwas_rest.app.config[nbgwas_rest.SLEEP_TIME_KEY] = 0
        self._app = nbgwas_rest.app.test_client()

    def tearDown(self):
        """Tear down test fixtures, if any."""
        shutil.rmtree(self._temp_dir)

    def test_baseurl(self):
        """Test something."""
        rv = self._app.get('/')
        self.assertEqual(rv.status_code, 200)
        self.assertTrue('Network Boosted' in str(rv.data))

    def test_get_submit_dir(self):
        spath = os.path.join(self._temp_dir, nbgwas_rest.SUBMIT_DIR)
        self.assertEqual(nbgwas_rest.get_submit_dir(), spath)

    def test_get_processing_dir(self):
        spath = os.path.join(self._temp_dir, nbgwas_rest.PROCESSING_DIR)
        self.assertEqual(nbgwas_rest.get_processing_dir(), spath)

    def test_get_done_dir(self):
        spath = os.path.join(self._temp_dir, nbgwas_rest.DONE_DIR)
        self.assertEqual(nbgwas_rest.get_done_dir(), spath)

    def test_get_task_basedir_none(self):
        self.assertEqual(nbgwas_rest.get_task('foo'), None)

    def test_get_task_basedir_not_a_directory(self):
        somefile = os.path.join(self._temp_dir, 'hi')
        open(somefile, 'a').close()
        self.assertEqual(nbgwas_rest.get_task('foo',basedir=somefile), None)

    def test_get_task_for_none_uuid(self):
        self.assertEqual(nbgwas_rest.get_task(None,
                                              basedir=self._temp_dir), None)

    def test_get_task_for_nonexistantuuid(self):
        self.assertEqual(nbgwas_rest.get_task(str(uuid.uuid4()),
                                              basedir=self._temp_dir), None)

    def test_get_task_for_validuuid(self):
        somefile = os.path.join(self._temp_dir, '1')
        open(somefile, 'a').close()
        theuuid_dir = os.path.join(self._temp_dir, '1.2.3.4', '1234')
        os.makedirs(theuuid_dir, mode=0o755)

        someipfile = os.path.join(self._temp_dir, '1.2.3.4', '1')
        open(someipfile, 'a').close()
        self.assertEqual(nbgwas_rest.get_task('1234',
                                              basedir=self._temp_dir),
                         theuuid_dir)

    def test_wait_for_task_uuid_none(self):
        self.assertEqual(nbgwas_rest.wait_for_task(None), None)

    def test_wait_for_task_uuid_not_found(self):
        self.assertEqual(nbgwas_rest.wait_for_task('foo'), None)

    def test_wait_for_task_uuid_found(self):
        taskdir = os.path.join(self._temp_dir, 'done', '1.2.3.4', 'haha')
        os.makedirs(taskdir, mode=0o755)
        self.assertEqual(nbgwas_rest.wait_for_task('haha'), taskdir)

    def test_delete(self):
        rv = self._app.delete('nbgwas/tasks/1')
        self.assertEqual(rv.status_code, 503)

    def test_head(self):
        rv = self._app.head('nbgwas/tasks/1')
        self.assertEqual(rv.status_code, 503)

    def test_post_missing_required_parameter(self):
        pdict = {}
        pdict[nbgwas_rest.ALPHA_PARAM] = 0.4,
        pdict[nbgwas_rest.SEEDS_PARAM] = 's1,s2'
        rv = self._app.post('nbgwas/tasks', data=pdict,
                            follow_redirects=True)
        self.assertEqual(rv.status_code, 500)

    def test_post_bigim(self):
        pdict={}
        pdict[nbgwas_rest.ALPHA_PARAM] = 0.4,
        pdict[nbgwas_rest.COLUMN_PARAM] = 'someid'
        pdict[nbgwas_rest.SEEDS_PARAM] = 's1,s2'
        rv = self._app.post('nbgwas/tasks', data=dict(
            alpha=0.4,
            seeds='s1,s2',
            column='someid'), follow_redirects=True)

        self.assertEqual(rv.status_code, 202)
        res = rv.headers['Location']
        self.assertTrue(res is not None)
        self.assertTrue('/nbgwas/tasks/' in res)

        uuidstr = re.sub('^.*\/', '', res)
        nbgwas_rest.app.config[nbgwas_rest.JOB_PATH_KEY] = self._temp_dir

        tpath = nbgwas_rest.get_task(uuidstr,
                                     basedir=nbgwas_rest.get_submit_dir())
        self.assertTrue(os.path.isdir(tpath))
        jsonfile = os.path.join(tpath, nbgwas_rest.TASK_JSON)
        self.assertTrue(os.path.isfile(jsonfile))
        with open(jsonfile, 'r') as f:
            jdata = json.load(f)

        self.assertEqual(jdata[nbgwas_rest.ALPHA_PARAM], 0.4)
        self.assertEqual(jdata[nbgwas_rest.SEEDS_PARAM], 's1,s2')
        self.assertEqual(jdata[nbgwas_rest.COLUMN_PARAM], 'someid')

    def test_post_ndex(self):
        pdict = {}
        pdict[nbgwas_rest.ALPHA_PARAM] = 0.5
        pdict[nbgwas_rest.NDEX_PARAM] = 'someid'
        pdict[nbgwas_rest.SEEDS_PARAM] = 'haha'
        rv = self._app.post('nbgwas/tasks', data=pdict,
                            follow_redirects=True)

        sys.stdout.write(str(rv.data))
        sys.stdout.flush()
        self.assertEqual(rv.status_code, 202)
        res = rv.headers['Location']
        self.assertTrue(res is not None)
        self.assertTrue('/nbgwas/tasks/' in res)

        uuidstr = re.sub('^.*\/', '', res)
        nbgwas_rest.app.config[nbgwas_rest.JOB_PATH_KEY] = self._temp_dir

        tpath = nbgwas_rest.get_task(uuidstr,
                                     basedir=nbgwas_rest.get_submit_dir())
        self.assertTrue(os.path.isdir(tpath))
        jsonfile = os.path.join(tpath, nbgwas_rest.TASK_JSON)
        self.assertTrue(os.path.isfile(jsonfile))
        with open(jsonfile, 'r') as f:
            jdata = json.load(f)

        self.assertEqual(jdata[nbgwas_rest.ALPHA_PARAM], 0.5)
        self.assertEqual(jdata[nbgwas_rest.SEEDS_PARAM], 'haha')
        self.assertEqual(jdata[nbgwas_rest.NDEX_PARAM], 'someid')

    def test_post_network(self):
        pdict = {}
        pdict[nbgwas_rest.ALPHA_PARAM] = 0.5
        pdict[nbgwas_rest.NETWORK_PARAM] = (io.BytesIO(b'hi there'), 'yo.txt')
        pdict[nbgwas_rest.SEEDS_PARAM] = 'haha'

        rv = self._app.post('nbgwas/tasks', data=pdict,
                            follow_redirects=True)

        sys.stdout.write(str(rv.data))
        sys.stdout.flush()
        self.assertEqual(rv.status_code, 202)
        res = rv.headers[nbgwas_rest.LOCATION]
        self.assertTrue(res is not None)
        self.assertTrue('/nbgwas/tasks/' in res)

        uuidstr = re.sub('^.*\/', '', res)
        nbgwas_rest.app.config[nbgwas_rest.JOB_PATH_KEY] = self._temp_dir

        tpath = nbgwas_rest.get_task(uuidstr,
                                     basedir=nbgwas_rest.get_submit_dir())
        self.assertTrue(os.path.isdir(tpath))
        jsonfile = os.path.join(tpath, nbgwas_rest.TASK_JSON)
        self.assertTrue(os.path.isfile(jsonfile))
        with open(jsonfile, 'r') as f:
            jdata = json.load(f)

        self.assertEqual(jdata[nbgwas_rest.ALPHA_PARAM], 0.5)
        self.assertEqual(jdata[nbgwas_rest.SEEDS_PARAM], 'haha')
        networkfile = os.path.join(tpath, nbgwas_rest.NETWORK_DATA)
        self.assertTrue(os.path.isfile(networkfile))
        with open(networkfile, 'r') as f:
            ndata = f.read()

        self.assertEqual(ndata, 'hi there')

    def test_get_id_none(self):
        rv = self._app.get('nbgwas/tasks')
        self.assertEqual(rv.status_code, 405)

    def test_get_id_not_found(self):
        rv = self._app.get('nbgwas/tasks/1234')
        self.assertEqual(str(rv.data), 'hi')
        self.assertEqual(rv.status_code, 500)
