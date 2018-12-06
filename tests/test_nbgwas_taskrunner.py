#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `nbgwas_taskrunner` script."""

import os
import json
import unittest
import shutil
import tempfile


import nbgwas_rest
from nbgwas_rest import nbgwas_taskrunner as nt
from nbgwas_rest.nbgwas_taskrunner import FileBasedTask


class TestNbgwas_rest(unittest.TestCase):
    """Tests for `nbgwas_rest` package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        pass

    def tearDown(self):
        """Tear down test fixtures, if any."""
        pass

    def test_parse_arguments(self):
        """Test something."""
        res = nt._parse_arguments('hi', ['foo'])
        self.assertEqual(res.taskdir, 'foo')
        self.assertEqual(res.wait_time, 30)
        self.assertEqual(res.verbose, 1)

    def test_setuplogging(self):
        res = nt._parse_arguments('hi', ['foo'])
        nt._setuplogging(res)

    def test_filebasedtask_getter_setter_on_basic_obj(self):

        task = FileBasedTask(None, None)
        self.assertEqual(task.get_task_uuid(), None)
        self.assertEqual(task.get_ipaddress(), None)
        self.assertEqual(task.get_networkx_object(), None)
        self.assertEqual(task.get_alpha(), None)
        self.assertEqual(task.get_network(), None)
        self.assertEqual(task.get_gene_level_summary(), None)
        self.assertEqual(task.get_ndex(), None)
        self.assertEqual(task.get_state(), None)
        self.assertEqual(task.get_taskdict(), None)
        self.assertEqual(task.get_taskdir(), None)

        self.assertEqual(task.get_task_summary_as_str(),
                         "{'basedir': None, 'state': None,"
                         " 'ipaddr': None, 'uuid': None}")

        task.set_result_data('result')
        task.set_networkx_object('hi')
        self.assertEqual(task.get_networkx_object(), 'hi')
        task.set_gene_level_summary('sum')
        self.assertEqual(task.get_gene_level_summary(), 'sum')

        task.set_taskdir('/foo')
        self.assertEqual(task.get_taskdir(), '/foo')

        task.set_taskdict({})
        self.assertEqual(task.get_alpha(), None)
        self.assertEqual(task.get_ndex(), None)
        temp_dir = tempfile.mkdtemp()
        try:
            task.set_taskdir(temp_dir)
            self.assertEqual(task.get_network(), None)
            thefile = os.path.join(temp_dir, nbgwas_rest.NETWORK_DATA)
            open(thefile, 'a').close()
            self.assertEqual(task.get_network(), thefile)
        finally:
            shutil.rmtree(temp_dir)

        task.set_taskdict({nbgwas_rest.ALPHA_PARAM: 0.1,
                           nbgwas_rest.NDEX_PARAM: 'ndex3'})
        self.assertEqual(task.get_alpha(), 0.1)
        self.assertEqual(task.get_ndex(), 'ndex3')

    def test_filebasedtask_get_uuid_ip_state_basedir_from_path(self):
        # taskdir is none
        task = FileBasedTask(None, None)
        res = task._get_uuid_ip_state_basedir_from_path()
        self.assertEqual(res[FileBasedTask.BASEDIR], None)
        self.assertEqual(res[FileBasedTask.STATE], None)
        self.assertEqual(res[FileBasedTask.IPADDR], None)
        self.assertEqual(res[FileBasedTask.UUID], None)

        # too basic a path
        task.set_taskdir('/foo')
        res = task._get_uuid_ip_state_basedir_from_path()
        self.assertEqual(res[FileBasedTask.BASEDIR], '/')
        self.assertEqual(res[FileBasedTask.STATE], None)
        self.assertEqual(res[FileBasedTask.IPADDR], None)
        self.assertEqual(res[FileBasedTask.UUID], 'foo')

        # valid path
        task.set_taskdir('/b/submitted/i/myjob')
        res = task._get_uuid_ip_state_basedir_from_path()
        self.assertEqual(res[FileBasedTask.BASEDIR], '/b')
        self.assertEqual(res[FileBasedTask.STATE], 'submitted')
        self.assertEqual(res[FileBasedTask.IPADDR], 'i')
        self.assertEqual(res[FileBasedTask.UUID], 'myjob')

        # big path
        task.set_taskdir('/a/c/b/submitted/i/myjob')
        res = task._get_uuid_ip_state_basedir_from_path()
        self.assertEqual(res[FileBasedTask.BASEDIR], '/a/c/b')
        self.assertEqual(res[FileBasedTask.STATE], 'submitted')
        self.assertEqual(res[FileBasedTask.IPADDR], 'i')
        self.assertEqual(res[FileBasedTask.UUID], 'myjob')

    def test_save_task(self):
        temp_dir = tempfile.mkdtemp()
        try:
            task = FileBasedTask(None, None)
            self.assertEqual(task.save_task(), 'Task dir is None')

            # try with None for dictionary
            task.set_taskdir(temp_dir)
            self.assertEqual(task.save_task(), 'Task dict is None')

            # try with taskdir set to file
            task.set_taskdict('hi')
            somefile = os.path.join(temp_dir, 'somefile')
            open(somefile, 'a').close()
            task.set_taskdir(somefile)
            self.assertEqual(task.save_task(), somefile +
                             ' is not a directory')

            # try with string set as dictionary
            task.set_taskdict('hi')
            task.set_taskdir(temp_dir)
            self.assertEqual(task.save_task(), None)

            task.set_taskdict({'blah': 'value'})
            self.assertEqual(task.save_task(), None)
            tfile = os.path.join(temp_dir, nbgwas_rest.TASK_JSON)
            with open(tfile, 'r') as f:
                self.assertEqual(f.read(), '{"blah": "value"}')

            # test with result set
            task.set_result_data({'result': 'data'})
            self.assertEqual(task.save_task(), None)
            rfile = os.path.join(temp_dir, nbgwas_rest.RESULT)
            with open(rfile, 'r') as f:
                self.assertEqual(f.read(), '{"result": "data"}')
        finally:
            shutil.rmtree(temp_dir)

    def test_move_task(self):
        temp_dir = tempfile.mkdtemp()
        try:
            submitdir = os.path.join(temp_dir, nbgwas_rest.SUBMITTED_STATUS)
            os.makedirs(submitdir, mode=0o755)
            processdir = os.path.join(temp_dir, nbgwas_rest.PROCESSING_STATUS)
            os.makedirs(processdir, mode=0o755)
            donedir = os.path.join(temp_dir, nbgwas_rest.DONE_STATUS)
            os.makedirs(donedir, mode=0o755)

            # try a move on unset task
            task = FileBasedTask(None, None)
            self.assertEqual(task.move_task(nbgwas_rest.PROCESSING_STATUS),
                             'Unable to extract state basedir from task path')

            # try a move from submit to process
            ataskdir = os.path.join(submitdir, '192.168.1.1', 'qwerty-qwerty')
            os.makedirs(ataskdir)
            task = FileBasedTask(ataskdir, {'hi': 'bye'})

            self.assertEqual(task.save_task(), None)

            # try a move from submit to submit
            self.assertEqual(task.move_task(nbgwas_rest.SUBMITTED_STATUS),
                             None)
            self.assertEqual(task.get_taskdir(), ataskdir)

            # try a move from submit to process
            self.assertEqual(task.move_task(nbgwas_rest.PROCESSING_STATUS),
                             None)
            self.assertTrue(not os.path.isdir(ataskdir))
            self.assertTrue(os.path.isdir(task.get_taskdir()))
            self.assertTrue(nbgwas_rest.PROCESSING_STATUS in
                            task.get_taskdir())

            # try a move from process to done
            self.assertEqual(task.move_task(nbgwas_rest.DONE_STATUS),
                             None)
            self.assertTrue(nbgwas_rest.DONE_STATUS in
                            task.get_taskdir())

            # try a move from done to submitted
            self.assertEqual(task.move_task(nbgwas_rest.SUBMITTED_STATUS),
                             None)
            self.assertTrue(nbgwas_rest.SUBMITTED_STATUS in
                            task.get_taskdir())

            # try a move from submitted to error
            self.assertEqual(task.move_task(nbgwas_rest.ERROR_STATUS),
                             None)
            self.assertTrue(nbgwas_rest.DONE_STATUS in
                            task.get_taskdir())
            tjson = os.path.join(task.get_taskdir(), nbgwas_rest.TASK_JSON)
            with open(tjson, 'r') as f:
                data = json.load(f)
                self.assertEqual(data[nbgwas_rest.ERROR_PARAM],
                                 'Unknown error')

            # try a move from error to submitted then back to error again
            # with message this time
            self.assertEqual(task.move_task(nbgwas_rest.SUBMITTED_STATUS),
                             None)
            self.assertEqual(task.move_task(nbgwas_rest.ERROR_STATUS,
                                            error_message='bad'),
                             None)
            tjson = os.path.join(task.get_taskdir(), nbgwas_rest.TASK_JSON)
            with open(tjson, 'r') as f:
                data = json.load(f)
                self.assertEqual(data[nbgwas_rest.ERROR_PARAM],
                                 'bad')
        finally:
            shutil.rmtree(temp_dir)
