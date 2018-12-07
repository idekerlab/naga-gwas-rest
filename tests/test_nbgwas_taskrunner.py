#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `nbgwas_taskrunner` script."""

import os
import json
import unittest
import shutil
import tempfile
from unittest.mock import MagicMock

import networkx as nx

import nbgwas_rest
from nbgwas_rest import nbgwas_taskrunner as nt
from nbgwas_rest.nbgwas_taskrunner import FileBasedTask
from nbgwas_rest.nbgwas_taskrunner import FileBasedSubmittedTaskFactory
from nbgwas_rest.nbgwas_taskrunner import NetworkXFromNDExFactory
from nbgwas_rest.nbgwas_taskrunner import NbgwasTaskRunner


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
        res = nt._parse_arguments('hi', ['--protein_coding_dir',
                                         'pcd', 'foo'])
        self.assertEqual(res.taskdir, 'foo')
        self.assertEqual(res.protein_coding_dir, 'pcd')

        self.assertEqual(res.wait_time, 30)
        self.assertEqual(res.verbose, 1)

    def test_setuplogging(self):
        res = nt._parse_arguments('hi', ['--protein_coding_dir',
                                         'pcd', 'foo'])
        nt._setuplogging(res)

    def test_filebasedtask_getter_setter_on_basic_obj(self):

        task = FileBasedTask(None, None)
        self.assertEqual(task.get_task_uuid(), None)
        self.assertEqual(task.get_ipaddress(), None)
        self.assertEqual(task.get_networkx_object(), None)
        self.assertEqual(task.get_alpha(), None)
        self.assertEqual(task.get_protein_coding(), None)
        self.assertEqual(task.get_window(), None)
        self.assertEqual(task.get_ndex(), None)
        self.assertEqual(task.get_state(), None)
        self.assertEqual(task.get_taskdict(), None)
        self.assertEqual(task.get_taskdir(), None)
        self.assertEqual(task.get_snp_level_summary_file(), None)
        self.assertEqual(task.get_protein_coding_file(), None)

        self.assertEqual(task.get_task_summary_as_str(),
                         "{'basedir': None, 'state': None,"
                         " 'ipaddr': None, 'uuid': None}")

        task.set_result_data('result')
        task.set_networkx_object('hi')
        self.assertEqual(task.get_networkx_object(), 'hi')

        task.set_taskdir('/foo')
        self.assertEqual(task.get_taskdir(), '/foo')

        task.set_taskdict({})
        self.assertEqual(task.get_alpha(), None)
        self.assertEqual(task.get_ndex(), None)
        self.assertEqual(task.get_protein_coding(), None)
        self.assertEqual(task.get_window(), None)
        temp_dir = tempfile.mkdtemp()
        try:
            task.set_taskdir(temp_dir)
            self.assertEqual(task.get_snp_level_summary_file(), None)
            thefile = os.path.join(temp_dir, nbgwas_rest.SNP_LEVEL_SUMMARY_PARAM)
            open(thefile, 'a').close()
            self.assertEqual(task.get_snp_level_summary_file(), thefile)
        finally:
            shutil.rmtree(temp_dir)

        task.set_taskdict({nbgwas_rest.ALPHA_PARAM: 0.1,
                           nbgwas_rest.NDEX_PARAM: 'ndex3',
                           nbgwas_rest.PROTEIN_CODING_PARAM: 'yo',
                           nbgwas_rest.WINDOW_PARAM: 10})
        self.assertEqual(task.get_alpha(), 0.1)
        self.assertEqual(task.get_ndex(), 'ndex3')
        self.assertEqual(task.get_protein_coding(), 'yo')
        self.assertEqual(task.get_window(), 10)

    def test_filebasedtask_get_protein_coding_file_no_protein_coding_dir(self):
        temp_dir = tempfile.mkdtemp()
        try:
            tdict = {nbgwas_rest.PROTEIN_CODING_PARAM: 'yo'}
            task = FileBasedTask(temp_dir, tdict)
            self.assertEqual(task.get_protein_coding_file(), None)
            pc_file = os.path.join(temp_dir,nbgwas_rest.PROTEIN_CODING_PARAM)
            open(pc_file, 'a').close()
            self.assertEqual(task.get_protein_coding_file(), pc_file)
        finally:
            shutil.rmtree(temp_dir)

    def test_filebasedtask_get_protein_coding_file_with_protein_coding(self):
        temp_dir = tempfile.mkdtemp()
        try:
            pcdir = os.path.join(temp_dir, 'pcdir')
            os.makedirs(pcdir, mode=0o755)
            task = FileBasedTask(temp_dir, None, protein_coding_dir=pcdir)

            # try with no protein coding param
            self.assertEqual(task.get_protein_coding_file(), None)

            # try with protein coding param set but no file
            tdict = {nbgwas_rest.PROTEIN_CODING_PARAM: 'yo'}
            task.set_taskdict(tdict)
            self.assertEqual(task.get_protein_coding_file(), None)

            # now add file no suffix to directory and try
            pc_file = os.path.join(pcdir, 'yo')
            open(pc_file, 'a').close()
            self.assertEqual(task.get_protein_coding_file(), pc_file)

            task = FileBasedTask(temp_dir, tdict, protein_coding_dir=pcdir,
                                 protein_coding_suffix='.txt')

            # test suffix adding logic
            self.assertEqual(task.get_protein_coding_file(), None)

            pc_file_txt = pc_file + '.txt'
            open(pc_file_txt, 'a').close()
            self.assertEqual(task.get_protein_coding_file(), pc_file_txt)
        finally:
            shutil.rmtree(temp_dir)


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

    def test_filebasedsubmittedtaskfactory_get_next_task_taskdirnone(self):
        fac = FileBasedSubmittedTaskFactory(None, None, None)
        self.assertEqual(fac.get_next_task(), None)

    def test_filebasedsubmittedtaskfactory_get_next_task(self):
        temp_dir = tempfile.mkdtemp()
        try:
            # no submit dir
            fac = FileBasedSubmittedTaskFactory(temp_dir, None, None)
            self.assertEqual(fac.get_next_task(), None)

            # empty submit dir
            sdir = os.path.join(temp_dir, nbgwas_rest.SUBMITTED_STATUS)
            os.makedirs(sdir, mode=0o755)
            self.assertEqual(fac.get_next_task(), None)

            # submit dir with file in it
            sdirfile = os.path.join(sdir, 'somefile')
            open(sdirfile, 'a').close()
            self.assertEqual(fac.get_next_task(), None)

            # submit dir with 1 subdir, but that is empty too
            ipsubdir = os.path.join(sdir, '1.2.3.4')
            os.makedirs(ipsubdir, mode=0o755)
            self.assertEqual(fac.get_next_task(), None)

            # submit dir with 1 subdir, with a file in it for some reason
            afile = os.path.join(ipsubdir, 'hithere')
            open(afile, 'a').close()
            self.assertEqual(fac.get_next_task(), None)

            # empty task dir
            taskdir = os.path.join(ipsubdir, 'sometask')
            os.makedirs(taskdir, mode=0o755)
            self.assertEqual(fac.get_next_task(), None)

            # empty json file
            taskjsonfile = os.path.join(taskdir, nbgwas_rest.TASK_JSON)
            open(taskjsonfile, 'a').close()
            self.assertEqual(fac.get_next_task(), None)
            self.assertEqual(fac.get_size_of_problem_list(), 1)
            plist = fac.get_problem_list()
            self.assertEqual(plist[0], taskdir)

            # try invalid json file

            # try with another task this time valid
            fac = FileBasedSubmittedTaskFactory(temp_dir, None, None)
            anothertask = os.path.join(sdir, '4.5.6.7', 'goodtask')
            os.makedirs(anothertask, mode=0o755)
            goodjson = os.path.join(anothertask, nbgwas_rest.TASK_JSON)
            with open(goodjson, 'w') as f:
                json.dump({'hi': 'there'}, f)

            res = fac.get_next_task()
            self.assertEqual(res.get_taskdict(), {'hi': 'there'})
            self.assertEqual(fac.get_size_of_problem_list(), 0)

            # try again since we didn't move it
            res = fac.get_next_task()
            self.assertEqual(res.get_taskdict(), {'hi': 'there'})
            self.assertEqual(fac.get_size_of_problem_list(), 0)
        finally:
            shutil.rmtree(temp_dir)

    def test_networkxfromndexfactory(self):
        fac = NetworkXFromNDExFactory(ndex_server=None)
        self.assertEqual(fac.get_networkx_object(None), None)

        try:
            # try with invalid uuid on an invalid server
            fac.get_networkx_object('hi')
            self.fail('Expected ConnectionError')
        except Exception as ae:
            self.assertEqual(str(ae), 'Server and uuid not specified')

    def test_nbgwastaskrunner_get_networkx_object(self):

        # try with None set as task
        runner = NbgwasTaskRunner()
        self.assertEqual(runner._get_networkx_object(None), None)

        # try with ndex id set to None
        task = FileBasedTask(None, {})
        runner = NbgwasTaskRunner()
        self.assertEqual(runner._get_networkx_object(task), None)

        # try with ndex id set
        task = FileBasedTask(None, {nbgwas_rest.NDEX_PARAM: 'someid'})
        runner = NbgwasTaskRunner()
        self.assertEqual(runner._get_networkx_object(task), None)

    def test_nbgwastaskrunner_get_networkx_object_from_ndex_valid_network(self):
        mock_network_fac = NetworkXFromNDExFactory()
        net_obj = nx.Graph()
        net_obj.add_node(1, {NbgwasTaskRunner.NDEX_NAME: 'node1'})
        net_obj.add_node(2, {NbgwasTaskRunner.NDEX_NAME: 'node2'})
        net_obj.add_edge(1, 2)
        mock_network_fac.get_networkx_object = MagicMock(return_value=net_obj)
        runner = NbgwasTaskRunner(networkfactory=mock_network_fac)
        res = runner._get_networkx_object_from_ndex('123')
        self.assertTrue(res is not None)
        self.assertEqual(len(res.node), 2)
        self.assertEqual(res.node['node1']['name'], 'node1')
        self.assertEqual(res.node['node2']['name'], 'node2')




