#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `naga_taskrunner` script."""

import os
import json
import unittest
import shutil
import tempfile
from unittest.mock import MagicMock

import networkx as nx

import nbgwas_rest
from nbgwas_rest import naga_taskrunner as nt
from nbgwas_rest.naga_taskrunner import FileBasedTask
from nbgwas_rest.naga_taskrunner import FileBasedSubmittedTaskFactory
from nbgwas_rest.naga_taskrunner import NetworkXFromNDExFactory
from nbgwas_rest.naga_taskrunner import NagaTaskRunner
from nbgwas_rest.naga_taskrunner import DeletedFileBasedTaskFactory


class TestNaga_rest(unittest.TestCase):
    """Tests for `naga_rest` package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        pass

    def tearDown(self):
        """Tear down test fixtures, if any."""
        pass

    def get_protein_coding(self):
        return """A1BG    19      63551643        63565932
A1CF    10      52271589        52315441
A2M     12      9111570 9159825
A2ML1   12      8911704 8930864
A3GALT2 1       744045        744090
A4GALT  22      41418839        41419901
A4GNT   3       139325249       139333919
AAAS    12      51987506        52001679
AACS    12      124155649       124193824
AADAC   3       153014550       153028966
AADACL2 3       152934404       152958242
AADACL3 1       744045        744095
AADACL4 1       12627152        12649684
AADAT   4       171217947       171247947
AAK1    2       69624874        69724481
AAMP    2       218837095       218843137
""" # noqa

    def get_snp(self):
        return """snpid chromosome basepair a1 a2 or se pvalue info ngt CEUaf
rs3131972       1       742584  A       G       1.0257  0.0835  0.761033        0.1613  0       0.16055
rs3131969       1       744045  A       G       1.0221  0.0801  0.784919        0.2225  0       0.133028
rs3131967       1       744197  T       C       1.0227  0.0858  0.79352 0.206   0       .
rs1048488       1       750775  T       C       0.9749  0.0835  0.761041        0.1613  0       0.836449
rs12562034      1       758311  A       G       1.0011  0.0756  0.987899        0.1856  3       0.0925926
rs12124819      1       766409  A       G       1.2838  0.226   0.269088        0.0145  0       .
rs4040617       1       769185  A       G       0.9787  0.0797  0.786883        0.233   3       0.87156
rs4970383       1       828418  A       C       1.116   0.1159  0.343555        0.0403  0       0.201835
rs4475691       1       836671  T       C       1.0926  0.0847  0.295819        0.0903  1       0.146789
rs1806509       1       843817  A       C       0.9152  0.0831  0.286321        0.0611  0       0.600917
""" # noqa

    def test_parse_arguments(self):
        """Test something."""
        res = nt._parse_arguments('hi', ['--protein_coding_dir',
                                         'pcd', 'foo'])
        self.assertEqual(res.taskdir, 'foo')
        self.assertEqual(res.protein_coding_dir, 'pcd')

        self.assertEqual(res.wait_time, 30)
        self.assertEqual(res.verbose, 1)
        self.assertEqual(res.disabledelete, False)
        self.assertEqual(res.protein_coding_suffix, '.txt')
        self.assertEqual(res.ndexserver, 'public.ndexbio.org')

    def test_setuplogging(self):
        res = nt._parse_arguments('hi', ['--protein_coding_dir',
                                         'pcd', 'foo'])
        nt._setuplogging(res)

    def test_filebasedtask_getter_setter_on_basic_obj(self):

        task = FileBasedTask(None, None)
        self.assertEqual(task.get_task_uuid(), None)
        self.assertEqual(task.get_ipaddress(), None)
        self.assertEqual(task.get_networkx_object(), None)
        self.assertEqual(task.get_alpha(), FileBasedTask.OPTIMAL)
        self.assertEqual(task.get_protein_coding(), None)
        self.assertEqual(task.get_window(), None)
        self.assertEqual(task.get_ndex(), None)
        self.assertEqual(task.get_state(), None)
        self.assertEqual(task.get_taskdict(), None)
        self.assertEqual(task.get_taskdir(), None)
        self.assertEqual(task.get_snp_level_summary_file(), None)
        self.assertEqual(task.get_protein_coding_file(), None)
        self.assertEqual(task.get_snp_chromosome_label(),
                         nbgwas_rest.SNP_LEVEL_SUMMARY_CHROM_COL)
        self.assertEqual(task.get_snp_basepair_label(),
                         nbgwas_rest.SNP_LEVEL_SUMMARY_BP_COL)
        self.assertEqual(task.get_snp_pvalue_label(),
                         nbgwas_rest.SNP_LEVEL_SUMMARY_PVAL_COL)

        self.assertEqual(task.get_task_summary_as_str(),
                         "{'basedir': None, 'state': None,"
                         " 'ipaddr': None, 'uuid': None}")

        task.set_result_data('result')
        task.set_networkx_object('hi')
        self.assertEqual(task.get_networkx_object(), 'hi')

        task.set_taskdir('/foo')
        self.assertEqual(task.get_taskdir(), '/foo')

        task.set_taskdict({nbgwas_rest.ALPHA_PARAM: None})
        self.assertEqual(task.get_alpha(), FileBasedTask.OPTIMAL)

        task.set_taskdict({})
        self.assertEqual(task.get_alpha(), FileBasedTask.OPTIMAL)
        self.assertEqual(task.get_ndex(), None)
        self.assertEqual(task.get_protein_coding(), None)
        self.assertEqual(task.get_window(), None)
        self.assertEqual(task.get_snp_chromosome_label(),
                         nbgwas_rest.SNP_LEVEL_SUMMARY_CHROM_COL)
        self.assertEqual(task.get_snp_basepair_label(),
                         nbgwas_rest.SNP_LEVEL_SUMMARY_BP_COL)
        self.assertEqual(task.get_snp_pvalue_label(),
                         nbgwas_rest.SNP_LEVEL_SUMMARY_PVAL_COL)

        temp_dir = tempfile.mkdtemp()
        try:
            task.set_taskdir(temp_dir)
            self.assertEqual(task.get_snp_level_summary_file(), None)
            thefile = os.path.join(temp_dir,
                                   nbgwas_rest.SNP_LEVEL_SUMMARY_PARAM)
            open(thefile, 'a').close()
            self.assertEqual(task.get_snp_level_summary_file(), thefile)
        finally:
            shutil.rmtree(temp_dir)

        task.set_taskdict({nbgwas_rest.ALPHA_PARAM: 0.1,
                           nbgwas_rest.NDEX_PARAM: 'ndex3',
                           nbgwas_rest.PROTEIN_CODING_PARAM: 'yo',
                           nbgwas_rest.WINDOW_PARAM: 10,
                           nbgwas_rest.
                          SNP_LEVEL_SUMMARY_COL_LABEL_PARAM: 'a,b,c'
                           })
        self.assertEqual(task.get_alpha(), 0.1)
        self.assertEqual(task.get_ndex(), 'ndex3')
        self.assertEqual(task.get_protein_coding(), 'yo')
        self.assertEqual(task.get_window(), 10)
        self.assertEqual(task.get_snp_chromosome_label(), 'a')
        self.assertEqual(task.get_snp_basepair_label(), 'b')
        self.assertEqual(task.get_snp_pvalue_label(), 'c')
        self.assertEqual(task._get_value_from_snp_column_label_string(-1),
                         None)
        self.assertEqual(task._get_value_from_snp_column_label_string(3), None)

    def test_filebasedtask_set_naga_version(self):
        task = FileBasedTask(None, None)
        task.set_naga_version()
        tdict = task.get_taskdict()
        self.assertTrue(nbgwas_rest.NAGA_VERSION in tdict)
        self.assertTrue(tdict[nbgwas_rest.NAGA_VERSION] is not None)

        task = FileBasedTask(None, {'hi': 'how'})
        task.set_naga_version(nagaversion='123')
        tdict = task.get_taskdict()
        self.assertEqual(tdict[nbgwas_rest.NAGA_VERSION], '123')
        self.assertEqual(tdict['hi'], 'how')

    def test_filebasedtask_get_protein_coding_file_no_protein_coding_dir(self):
        temp_dir = tempfile.mkdtemp()
        try:
            tdict = {nbgwas_rest.PROTEIN_CODING_PARAM: 'yo'}
            task = FileBasedTask(temp_dir, tdict)
            self.assertEqual(task.get_protein_coding_file(), None)
            pc_file = os.path.join(temp_dir, nbgwas_rest.PROTEIN_CODING_PARAM)
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

    def test_filebasedtask_delete_temp_files(self):
        temp_dir = tempfile.mkdtemp()
        try:
            processdir = os.path.join(temp_dir, nbgwas_rest.PROCESSING_STATUS)
            os.makedirs(processdir, mode=0o755)
            donedir = os.path.join(temp_dir, nbgwas_rest.DONE_STATUS)
            os.makedirs(donedir, mode=0o755)
            ataskdir = os.path.join(processdir, '192.168.1.1', 'qwerty-qwerty')
            os.makedirs(ataskdir)
            taskdict = {'hi': 'bye'}
            task = FileBasedTask(ataskdir, taskdict)
            self.assertEqual(task.save_task(), None)

            # try move with delete true, but no file to delete
            self.assertEqual(task.move_task(nbgwas_rest.DONE_STATUS,
                                            delete_temp_files=True), None)

            # move task back to processing
            self.assertEqual(task.move_task(nbgwas_rest.PROCESSING_STATUS),
                             None)

            # add file and try move to done with delete set to false
            snpfile = os.path.join(task.get_taskdir(),
                                   nbgwas_rest.SNP_LEVEL_SUMMARY_PARAM)
            open(snpfile, 'a').close()

            self.assertEqual(task.move_task(nbgwas_rest.DONE_STATUS),
                             None)

            self.assertTrue(os.path.isfile(task.get_snp_level_summary_file()))

            # move back and try move to done with delete set to true
            self.assertEqual(task.move_task(nbgwas_rest.PROCESSING_STATUS),
                             None)

            self.assertEqual(task.move_task(nbgwas_rest.DONE_STATUS,
                                            delete_temp_files=True),
                             None)
            self.assertEqual(task.get_snp_level_summary_file(), None)
        finally:
            shutil.rmtree(temp_dir)

    def test_filebasedtask_delete_task_files(self):
        temp_dir = tempfile.mkdtemp()
        try:
            # try where taskdir is none
            task = FileBasedTask(None, None)
            self.assertEqual(task.delete_task_files(),
                             'Task directory is None')

            # try where taskdir is not a directory
            notadir = os.path.join(temp_dir, 'notadir')
            task = FileBasedTask(notadir, None)
            self.assertEqual(task.delete_task_files(),
                             'Task directory ' + notadir +
                             ' is not a directory')

            # try on empty directory
            emptydir = os.path.join(temp_dir, 'emptydir')
            os.makedirs(emptydir, mode=0o755)
            task = FileBasedTask(emptydir, None)
            self.assertEqual(task.delete_task_files(), None)
            self.assertFalse(os.path.isdir(emptydir))

            # try with result, snp, and task.json files
            valid_dir = os.path.join(temp_dir, 'yoyo')
            os.makedirs(valid_dir, mode=0o755)
            open(os.path.join(valid_dir, nbgwas_rest.RESULT), 'a').close()
            open(os.path.join(valid_dir, nbgwas_rest.TASK_JSON),
                 'a').close()
            open(os.path.join(valid_dir,
                              nbgwas_rest.SNP_LEVEL_SUMMARY_PARAM),
                 'a').close()

            task = FileBasedTask(valid_dir, {})
            self.assertEqual(task.delete_task_files(), None)
            self.assertFalse(os.path.isdir(valid_dir))

            # try where extra file causes os.rmdir to fail
            valid_dir = os.path.join(temp_dir, 'yoyo')
            os.makedirs(valid_dir, mode=0o755)
            open(os.path.join(valid_dir, 'somefile'), 'a').close()

            open(os.path.join(valid_dir, nbgwas_rest.RESULT), 'a').close()
            open(os.path.join(valid_dir, nbgwas_rest.TASK_JSON),
                 'a').close()
            open(os.path.join(valid_dir,
                              nbgwas_rest.SNP_LEVEL_SUMMARY_PARAM),
                 'a').close()
            task = FileBasedTask(valid_dir, {})
            self.assertTrue('trying to remove ' in task.delete_task_files())
            self.assertTrue(os.path.isdir(valid_dir))

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

            shutil.rmtree(taskdir)
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
        runner = NagaTaskRunner()
        self.assertEqual(runner._get_networkx_object(None), None)

        # try with ndex id set to None
        task = FileBasedTask(None, {})
        runner = NagaTaskRunner()
        self.assertEqual(runner._get_networkx_object(task), None)

        # try with ndex id set
        task = FileBasedTask(None, {nbgwas_rest.NDEX_PARAM: 'someid'})
        runner = NagaTaskRunner()
        self.assertEqual(runner._get_networkx_object(task), None)

    def test_nbgwastaskrunner_get_networkx_object_from_ndex_no_network(self):
        mock_network_fac = NetworkXFromNDExFactory()
        mock_network_fac.get_networkx_object = MagicMock(return_value=None)
        runner = NagaTaskRunner(networkfactory=mock_network_fac)
        res = runner._get_networkx_object_from_ndex('123')
        self.assertTrue(res is None)

    def test_nbgwastaskrunner_get_networkx_object_from_ndex_valid_net(self):
        mock_network_fac = NetworkXFromNDExFactory()
        net_obj = nx.Graph()
        net_obj.add_node(1, {NagaTaskRunner.NDEX_NAME: 'node1'})
        net_obj.add_node(2, {NagaTaskRunner.NDEX_NAME: 'node2'})
        net_obj.add_edge(1, 2)
        mock_network_fac.get_networkx_object = MagicMock(return_value=net_obj)
        runner = NagaTaskRunner(networkfactory=mock_network_fac)
        res = runner._get_networkx_object_from_ndex('123')
        self.assertTrue(res is not None)
        self.assertEqual(len(res.node), 2)
        self.assertEqual(res.node['node1']['name'], 'node1')
        self.assertEqual(res.node['node2']['name'], 'node2')

    def test_nbgwastaskrunner_process_task_networkx_is_none(self):
        temp_dir = tempfile.mkdtemp()
        try:
            mock_network_fac = NetworkXFromNDExFactory()
            mock_network_fac.get_networkx_object = MagicMock(return_value=None)
            runner = NagaTaskRunner(networkfactory=mock_network_fac)
            taskdir = os.path.join(temp_dir, nbgwas_rest.SUBMITTED_STATUS,
                                   '1.2.3.4', 'taskuuid')
            os.makedirs(taskdir, mode=0o755)
            task = FileBasedTask(taskdir, {nbgwas_rest.NDEX_PARAM: 'someid'})
            runner._process_task(task)

            self.assertTrue(nbgwas_rest.DONE_STATUS in task.get_taskdir())
            self.assertEqual(task.get_taskdict()[nbgwas_rest.ERROR_STATUS],
                             'Unable to get networkx object for task')
        finally:
            shutil.rmtree(temp_dir)

    def test_nbgwastaskrunner_process_task_with_mini_snp_pc(self):
        temp_dir = tempfile.mkdtemp()
        try:
            mock_network_fac = NetworkXFromNDExFactory()
            net_obj = nx.Graph()
            net_obj.add_node(1, {NagaTaskRunner.NDEX_NAME: 'A3GALT2'})
            net_obj.add_node(2, {NagaTaskRunner.NDEX_NAME: 'AADACL3'})
            net_obj.add_edge(1, 2)
            mock_network_fac.\
                get_networkx_object = MagicMock(return_value=net_obj)
            runner = NagaTaskRunner(networkfactory=mock_network_fac)
            taskdir = os.path.join(temp_dir, nbgwas_rest.SUBMITTED_STATUS,
                                   '1.2.3.4', 'taskuuid')
            os.makedirs(taskdir, mode=0o755)
            snpfile = os.path.join(taskdir,
                                   nbgwas_rest.SNP_LEVEL_SUMMARY_PARAM)
            with open(snpfile, 'w') as f:
                f.write(self.get_snp())
                f.flush()
            pcfile = os.path.join(taskdir, nbgwas_rest.PROTEIN_CODING_PARAM)
            with open(pcfile, 'w') as f:
                f.write(self.get_protein_coding())
                f.flush()

            task = FileBasedTask(taskdir, {nbgwas_rest.NDEX_PARAM: 'someid',
                                           nbgwas_rest.WINDOW_PARAM: 100,
                                           nbgwas_rest.ALPHA_PARAM: 0.2})
            runner._process_task(task)
            self.assertTrue(nbgwas_rest.DONE_STATUS in task.get_taskdir())
            self.assertTrue(nbgwas_rest.ERROR_STATUS not in
                            task.get_taskdict())

            result = os.path.join(task.get_taskdir(), nbgwas_rest.RESULT)
            with open(result, 'r') as f:
                data = json.load(f)

            #self.assertEqual(str(data), 'hi')
            self.assertEqual(data[nbgwas_rest.RESULTVALUE_KEY]['A3GALT2'][0], 0.0)
            self.assertTrue(0.0 < data[nbgwas_rest.RESULTVALUE_KEY]['A3GALT2'][1] < 0.3)
            self.assertEqual(data[nbgwas_rest.RESULTVALUE_KEY]['A3GALT2'][2], 0.0)
            self.assertTrue(0.0 < data[nbgwas_rest.RESULTVALUE_KEY]['A3GALT2'][3] < 0.3)

            self.assertEqual(data[nbgwas_rest.RESULTVALUE_KEY]['AADACL3'][0], 0.0)
            self.assertTrue(0.0 < data[nbgwas_rest.RESULTVALUE_KEY]['AADACL3'][1] < 0.3)
            self.assertEqual(data[nbgwas_rest.RESULTVALUE_KEY]['AADACL3'][2], 0.0)
            self.assertTrue(0.0 < data[nbgwas_rest.RESULTVALUE_KEY]['AADACL3'][3] < 0.3)



            tdict = task.get_taskdict()
            self.assertTrue(nbgwas_rest.NAGA_VERSION in tdict)
            self.assertTrue(tdict[nbgwas_rest.NAGA_VERSION] is not None)

        finally:
            shutil.rmtree(temp_dir)

    def test_nbgwastaskrunner_run_tasks_no_work(self):
        mocktaskfac = MagicMock()
        mocktaskfac.get_next_task = MagicMock(side_effect=[None, None])
        runner = NagaTaskRunner(wait_time=0, taskfactory=mocktaskfac)
        loop = MagicMock()
        loop.side_effect = [True, True, False]
        runner.run_tasks(keep_looping=loop)
        self.assertEqual(loop.call_count, 3)
        self.assertEqual(mocktaskfac.get_next_task.call_count, 2)

    def test_nbgwastaskrunner_run_tasks_task_raises_exception(self):
        temp_dir = tempfile.mkdtemp()
        try:
            mocktaskfac = MagicMock()
            mocktask = MagicMock()
            mocktask.get_taskdir = MagicMock(return_value=temp_dir)
            mocktask.move_task = MagicMock()
            mocktaskfac.get_next_task.side_effect = [None, mocktask]

            mock_net_fac = MagicMock()
            mock_net_fac. \
                get_networkx_object = MagicMock(side_effect=Exception('foo'))

            runner = NagaTaskRunner(wait_time=0,
                                    taskfactory=mocktaskfac,
                                    networkfactory=mock_net_fac)
            loop = MagicMock()
            loop.side_effect = [True, True, False]
            runner.run_tasks(keep_looping=loop)
            self.assertEqual(loop.call_count, 3)
            self.assertEqual(mocktaskfac.get_next_task.call_count, 2)
        finally:
            shutil.rmtree(temp_dir)

    def test_nbgwastaskrunner_remove_deleted_task(self):
        temp_dir = tempfile.mkdtemp()
        try:
            # try where delete task factory is none
            runner = NagaTaskRunner(wait_time=0)
            self.assertEqual(runner._remove_deleted_task(), False)

            # try where no task is returned
            mockfac = MagicMock()
            mockfac.get_next_task = MagicMock(return_value=None)
            runner = NagaTaskRunner(wait_time=0,
                                    deletetaskfactory=mockfac)
            res = runner._remove_deleted_task()
            self.assertEqual(res, False)
            mockfac.get_next_task.assert_called()

            # try where task.get_taskdir() is None
            task = MagicMock()
            task.get_taskdir = MagicMock(return_value=None)
            mockfac.get_next_task = MagicMock(return_value=task)
            runner = NagaTaskRunner(wait_time=0,
                                    deletetaskfactory=mockfac)
            res = runner._remove_deleted_task()
            self.assertEqual(res, True)
            mockfac.get_next_task.assert_called()
            task.get_taskdir.assert_called()

            # try where task.delete_task_files() raises Exception
            task = MagicMock()
            task.get_taskdir = MagicMock(return_value='/foo')
            task.delete_task_files = MagicMock(side_effect=Exception('some '
                                                                     'error'))
            mockfac.get_next_task = MagicMock(return_value=task)
            runner = NagaTaskRunner(wait_time=0,
                                    deletetaskfactory=mockfac)
            res = runner._remove_deleted_task()
            self.assertEqual(res, False)
            mockfac.get_next_task.assert_called()
            task.get_taskdir.assert_called()
            task.delete_task_files.assert_called()

            # try with valid task to delete, but delete returns message
            task = MagicMock()
            task.get_taskdir = MagicMock(return_value='/foo')
            task.delete_task_files = MagicMock(return_value='a error')
            mockfac.get_next_task = MagicMock(return_value=task)
            runner = NagaTaskRunner(wait_time=0,
                                    deletetaskfactory=mockfac)
            res = runner._remove_deleted_task()
            self.assertEqual(res, True)
            mockfac.get_next_task.assert_called()
            task.get_taskdir.assert_called()
            task.delete_task_files.assert_called()

            # try with valid task to delete
            task = MagicMock()
            task.get_taskdir = MagicMock(return_value='/foo')
            task.delete_task_files = MagicMock(return_value=None)
            mockfac.get_next_task = MagicMock(return_value=task)
            runner = NagaTaskRunner(wait_time=0,
                                    deletetaskfactory=mockfac)
            res = runner._remove_deleted_task()
            self.assertEqual(res, True)
            mockfac.get_next_task.assert_called()
            task.get_taskdir.assert_called()
            task.delete_task_files.assert_called()
        finally:
            shutil.rmtree(temp_dir)

    def test_deletefilebasedtaskfactory_get_task_with_id(self):
        temp_dir = tempfile.mkdtemp()
        try:
            # try where taskdir is not set
            tfac = DeletedFileBasedTaskFactory(None)
            res = tfac._get_task_with_id('foo')
            self.assertEqual(res, None)

            # try with valid taskdir
            tfac = DeletedFileBasedTaskFactory(temp_dir)
            res = tfac._get_task_with_id('foo')
            self.assertEqual(res, None)

            # try where we match in submit dir, but match is not
            # a directory
            submitfile = os.path.join(temp_dir, nbgwas_rest.SUBMITTED_STATUS,
                                      '1.2.3.4', 'foo')
            os.makedirs(os.path.dirname(submitfile), mode=0o755)
            open(submitfile, 'a').close()
            tfac = DeletedFileBasedTaskFactory(temp_dir)
            res = tfac._get_task_with_id('foo')
            self.assertEqual(res, None)
            os.unlink(submitfile)

            # try where we match in submit dir, but no json file
            submitdir = os.path.join(temp_dir, nbgwas_rest.SUBMITTED_STATUS,
                                     '1.2.3.4', 'foo')
            os.makedirs(submitdir, mode=0o755)
            tfac = DeletedFileBasedTaskFactory(temp_dir)
            res = tfac._get_task_with_id('foo')
            self.assertEqual(res.get_taskdir(), submitdir)

            # try where we match in submit dir and there is a json file
            taskfile = os.path.join(submitdir,
                                    nbgwas_rest.TASK_JSON)
            with open(taskfile, 'w') as f:
                json.dump({nbgwas_rest.REMOTEIP_PARAM: '1.2.3.4'}, f)
                f.flush()

            tfac = DeletedFileBasedTaskFactory(temp_dir)
            res = tfac._get_task_with_id('foo')
            self.assertEqual(res.get_taskdir(), submitdir)
            self.assertEqual(res.get_ipaddress(), '1.2.3.4')

            # try where loading json file raises exception
            os.unlink(taskfile)
            open(taskfile, 'a').close()
            res = tfac._get_task_with_id('foo')
            self.assertEqual(res.get_taskdir(), submitdir)
            self.assertEqual(res.get_taskdict(), {})
            shutil.rmtree(submitdir)

            # try where we match in processing dir
            procdir = os.path.join(temp_dir, nbgwas_rest.PROCESSING_STATUS,
                                   '4.5.5.5',
                                   '02e487ef-79df-4d99-8f22-1ff1d6d52a2a')
            os.makedirs(procdir, mode=0o755)
            res = tfac._get_task_with_id('02e487ef-79df-4d99-8f22-'
                                         '1ff1d6d52a2a')
            self.assertEqual(res.get_taskdir(), procdir)
            shutil.rmtree(procdir)

            # try where we match in done dir
            donedir = os.path.join(temp_dir, nbgwas_rest.DONE_STATUS,
                                   '192.168.5.5',
                                   '02e487ef-79df-4d99-8f22-1ff1d6d52a2a')
            os.makedirs(donedir, mode=0o755)
            res = tfac._get_task_with_id('02e487ef-79df-4d99-8f22-'
                                         '1ff1d6d52a2a')
            self.assertEqual(res.get_taskdir(), donedir)

        finally:
            shutil.rmtree(temp_dir)

    def test_deletefilebasedtaskfactory_get_next_task(self):
        temp_dir = tempfile.mkdtemp()
        try:
            # test where delete request dir is None
            tfac = DeletedFileBasedTaskFactory(None)
            res = tfac.get_next_task()
            self.assertEqual(res, None)

            # test where delete request dir is not a directory
            tfac = DeletedFileBasedTaskFactory(temp_dir)
            res = tfac.get_next_task()
            self.assertEqual(res, None)

            # no delete requests found
            del_req_dir = os.path.join(temp_dir, nbgwas_rest.DELETE_REQUESTS)
            os.makedirs(del_req_dir, mode=0o755)
            tfac = DeletedFileBasedTaskFactory(temp_dir)
            res = tfac.get_next_task()
            self.assertEqual(res, None)

            # directory in delete requests dir
            dir_in_del_dir = os.path.join(del_req_dir, 'uhohadir')
            os.makedirs(dir_in_del_dir, mode=0o755)
            tfac = DeletedFileBasedTaskFactory(temp_dir)
            res = tfac.get_next_task()
            self.assertEqual(res, None)

            # Found a delete request, but no task found in system
            a_request = os.path.join(del_req_dir,
                                     '02e487ef-79df-4d99-8f22-1ff1d6d52a2a')
            with open(a_request, 'w') as f:
                f.write('1.2.3.4')
                f.flush()
            tfac = DeletedFileBasedTaskFactory(temp_dir)
            res = tfac.get_next_task()
            self.assertEqual(res, None)
            self.assertTrue(not os.path.isfile(a_request))

            # Found a valid request in system
            a_request = os.path.join(del_req_dir,
                                     '02e487ef-79df-4d99-8f22-1ff1d6d52a2a')
            with open(a_request, 'w') as f:
                f.write('1.2.3.4')
                f.flush()
            done_dir = os.path.join(temp_dir, nbgwas_rest.DONE_STATUS,
                                    '1.2.3.4',
                                    '02e487ef-79df-4d99-8f22-1ff1d6d52a2a')
            os.makedirs(done_dir, mode=0o755)
            tfac = DeletedFileBasedTaskFactory(temp_dir)
            res = tfac.get_next_task()
            self.assertEqual(res.get_taskdir(), done_dir)
            self.assertEqual(res.get_taskdict(), {})
            self.assertTrue(not os.path.isfile(a_request))

        finally:
            shutil.rmtree(temp_dir)

    def test_main(self):
        temp_dir = tempfile.mkdtemp()
        try:
            # test no work and disable delete true
            loop = MagicMock()
            loop.side_effect = [True, True, False]
            nt.main(['foo.py', '--wait_time', '0',
                     '--protein_coding_dir',
                     'pcdir', '--nodaemon', temp_dir],
                    keep_looping=loop)

            # test no work and disable delete false
            loop = MagicMock()
            loop.side_effect = [True, True, False]
            nt.main(['foo.py', '--wait_time', '0',
                     '--disabledelete',
                     '--protein_coding_dir',
                     'pcdir', '--nodaemon', temp_dir],
                    keep_looping=loop)

            # test exception catch works
            loop = MagicMock()
            loop.side_effect = Exception('some error')
            nt.main(['foo.py', '--wait_time', '0',
                     '--protein_coding_dir',
                     'pcdir', '--nodaemon', temp_dir],
                    keep_looping=loop)
        finally:
            shutil.rmtree(temp_dir)
