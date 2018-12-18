#!/usr/bin/env python


import os
import sys
import argparse
import logging
import time
import shutil
import json

from nbgwas import Nbgwas

import nbgwas_rest
import networkx as nx
from ndex2 import create_nice_cx_from_server


logger = logging.getLogger('nbgwas_taskrunner')

LOG_FORMAT = "%(asctime)-15s %(levelname)s %(relativeCreated)dms " \
             "%(filename)s::%(funcName)s():%(lineno)d %(message)s"


def _parse_arguments(desc, args):
    """Parses command line arguments"""
    help_formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=desc,
                                     formatter_class=help_formatter)
    parser.add_argument('taskdir', help='Base directory where tasks'
                                        'are located')
    parser.add_argument('--protein_coding_dir', required=True,
                        help='Directory where protein_coding data files '
                             'reside')
    parser.add_argument('--protein_coding_suffix', default='.txt',
                        help='Suffix of protein_coding files in '
                             '--protein_coding_dir directory. (default .txt)')
    parser.add_argument('--wait_time', type=int, default=30,
                        help='Time in seconds to wait'
                             'before looking for new'
                             'tasks')
    parser.add_argument('--ndexserver', default='public.ndexbio.org',
                        help='NDEx server default is public.ndexbio.org')
    parser.add_argument('--version', action='version',
                        version=('%(prog)s ' + nbgwas_rest.__version__))
    parser.add_argument('--verbose', '-v', action='count',
                        help='Increases logging verbosity, max is 4',
                        default=1)
    return parser.parse_args(args)


def _setuplogging(theargs):
    """Sets up logging"""
    level = (50 - (10 * theargs.verbose))
    logging.basicConfig(format=LOG_FORMAT,
                        level=level)
    for k in logging.Logger.manager.loggerDict.keys():
        thelog = logging.Logger.manager.loggerDict[k]

        # not sure if this is the cleanest way to do this
        # but the dictionary of Loggers has a PlaceHolder
        # object which tosses an exception if setLevel()
        # is called so I'm checking the class names
        try:
            thelog.setLevel(level)
        except AttributeError:
            pass


class FileBasedTask(object):
    """Represents a task
    """

    BASEDIR = 'basedir'
    STATE = 'state'
    IPADDR = 'ipaddr'
    UUID = 'uuid'
    OPTIMAL = 'optimal'
    TASK_FILES = [nbgwas_rest.RESULT, nbgwas_rest.SNP_LEVEL_SUMMARY_PARAM,
                  nbgwas_rest.TASK_JSON]

    def __init__(self, taskdir, taskdict,
                 protein_coding_dir=None,
                 protein_coding_suffix=None):
        self._taskdir = taskdir
        self._taskdict = taskdict
        self._networkx_obj = None
        self._snplevelsummary = None
        self._resultdata = None
        self._protein_coding_dir = protein_coding_dir
        self._protein_coding_suffix = protein_coding_suffix

    def delete_task_files(self):
        """
        Deletes all files and directories pertaining to task
        on filesystem
        :return: None upon success or str with error message
        """
        if self._taskdir is None:
            return 'Task directory is None'

        if not os.path.isdir(self._taskdir):
            return ('Task directory ' + self._taskdir +
                    ' is not a directory')

        # this is a paranoid removal since we only are tossing
        # the directory in question and files listed in TASK_FILES
        try:
            for entry in os.listdir(self._taskdir):
                if entry not in FileBasedTask.TASK_FILES:
                    logger.error(entry + ' not in files created by task')
                    continue
                fp = os.path.join(self._taskdir, entry)
                if os.path.isfile(fp):
                    os.unlink(fp)
            os.rmdir(self._taskdir)
            return None
        except Exception as e:
            logger.exception('Caught exception removing ' + self._taskdir)
            return ('Caught exception ' + str(e) + 'trying to remove ' +
                    self._taskdir)

    def save_task(self):
        """
        Updates task in datastore. For filesystem based
        task this means rewriting the task.json file
        :return: None for success otherwise string containing error message
        """
        if self._taskdir is None:
            return 'Task dir is None'

        if self._taskdict is None:
            return 'Task dict is None'

        if not os.path.isdir(self._taskdir):
            return str(self._taskdir) + ' is not a directory'

        tjsonfile = os.path.join(self._taskdir, nbgwas_rest.TASK_JSON)
        logger.debug('Writing task data to: ' + tjsonfile)
        with open(tjsonfile, 'w') as f:
            json.dump(self._taskdict, f)

        if self._resultdata is not None:
            resultfile = os.path.join(self._taskdir, nbgwas_rest.RESULT)
            logger.debug('Writing result data to: ' + resultfile)
            with open(resultfile, 'w') as f:
                json.dump(self._resultdata, f)
                f.flush()
        return None

    def move_task(self, new_state,
                  error_message=None,
                  delete_temp_files=False):
        """
        Changes state of task to new_state
        :param new_state: new state
        :return: None
        """
        taskattrib = self._get_uuid_ip_state_basedir_from_path()
        if taskattrib is None or taskattrib[FileBasedTask.BASEDIR] is None:
            return 'Unable to extract state basedir from task path'

        if taskattrib[FileBasedTask.STATE] == new_state:
            logger.debug('Attempt to move task to same state: ' +
                         self._taskdir)
            return None

        # if new state is error still put the task into
        # done directory, but update error message in
        # task json
        if new_state == nbgwas_rest.ERROR_STATUS:
            new_state = nbgwas_rest.DONE_STATUS

            if error_message is None:
                emsg = 'Unknown error'
            else:
                emsg = error_message
            logger.info('Task set to error state with message: ' +
                        emsg)
            self._taskdict[nbgwas_rest.ERROR_PARAM] = emsg
            self.save_task()
        logger.debug('Changing task: ' + str(taskattrib[FileBasedTask.UUID]) +
                     ' to state ' + new_state)
        ptaskdir = os.path.join(taskattrib[FileBasedTask.BASEDIR], new_state,
                                taskattrib[FileBasedTask.IPADDR],
                                taskattrib[FileBasedTask.UUID])
        shutil.move(self._taskdir, ptaskdir)
        self._taskdir = ptaskdir

        if delete_temp_files is True:
            self._delete_temp_files()
        return None

    def _delete_temp_files(self):
        """
        Deletes snp level param file from filesystem
        :return: None
        """
        try:
            snpfile = self.get_snp_level_summary_file()
            if snpfile is None:
                return
            logger.debug('Removing ' + snpfile)
            os.unlink(snpfile)

        except OSError:
            logger.exception('Caught exception trying to remove file')

    def _get_uuid_ip_state_basedir_from_path(self):
        """
        Parses taskdir path into main parts and returns
        result as dict
        :return: {'basedir': basedir,
                  'state': state
                  'ipaddr': ip address,
                  'uuid': task uuid}
        """
        if self._taskdir is None:
            logger.error('Task dir not set')
            return {FileBasedTask.BASEDIR: None,
                    FileBasedTask.STATE: None,
                    FileBasedTask.IPADDR: None,
                    FileBasedTask.UUID: None}
        taskuuid = os.path.basename(self._taskdir)
        ipdir = os.path.dirname(self._taskdir)
        ipaddr = os.path.basename(ipdir)
        if ipaddr == '':
            ipaddr = None
        statedir = os.path.dirname(ipdir)
        state = os.path.basename(statedir)
        if state == '':
            state = None
        basedir = os.path.dirname(statedir)
        return {FileBasedTask.BASEDIR: basedir,
                FileBasedTask.STATE: state,
                FileBasedTask.IPADDR: ipaddr,
                FileBasedTask.UUID: taskuuid}

    def get_ipaddress(self):
        """
        gets ip address
        :return:
        """
        res = self._get_uuid_ip_state_basedir_from_path()[FileBasedTask.IPADDR]
        return res

    def get_state(self):
        """
        Gets current state of task based on taskdir
        :return:
        """
        return self._get_uuid_ip_state_basedir_from_path()[FileBasedTask.STATE]

    def get_task_uuid(self):
        """
        Parses taskdir path to get uuid
        :return: string containing uuid or None if not found
        """
        return self._get_uuid_ip_state_basedir_from_path()[FileBasedTask.UUID]

    def get_task_summary_as_str(self):
        """
        Prints quick summary of task
        :return:
        """
        res = self._get_uuid_ip_state_basedir_from_path()
        return str(res)

    def set_result_data(self, result):
        """
        Sets result data object
        :param result:
        :return:
        """
        self._resultdata = result

    def set_networkx_object(self, networkx_obj):
        """
        Sets networkx_obj
        :param networkx_obj:
        :return:
        """
        self._networkx_obj = networkx_obj

    def get_networkx_object(self):
        """
        Gets networkx_obj
        :return:
        """
        return self._networkx_obj

    def set_taskdir(self, taskdir):
        """
        Sets task directory
        :param taskdir:
        :return:
        """
        self._taskdir = taskdir

    def get_taskdir(self):
        """
        Gets task directory
        :return:
        """
        return self._taskdir

    def set_taskdict(self, taskdict):
        """
        Sets task dictionary
        :param taskdict:
        :return:
        """
        self._taskdict = taskdict

    def get_taskdict(self):
        """
        Gets task dictionary
        :return:
        """
        return self._taskdict

    def get_alpha(self):
        """
        Gets alpha parameter
        :return: alpha parameter or None
        """
        if self._taskdict is None:
            return FileBasedTask.OPTIMAL
        if nbgwas_rest.ALPHA_PARAM not in self._taskdict:
            return FileBasedTask.OPTIMAL
        res = self._taskdict[nbgwas_rest.ALPHA_PARAM]
        if res is None:
            return FileBasedTask.OPTIMAL
        return res

    def get_protein_coding(self):
        """
        Gets protein coding parameter
        :return:
        """
        if self._taskdict is None:
            return None
        if nbgwas_rest.PROTEIN_CODING_PARAM not in self._taskdict:
            return None
        return self._taskdict[nbgwas_rest.PROTEIN_CODING_PARAM]

    def get_window(self):
        """
        Gets window parameter
        :return:
        """
        if self._taskdict is None:
            return None
        if nbgwas_rest.WINDOW_PARAM not in self._taskdict:
            return None
        return self._taskdict[nbgwas_rest.WINDOW_PARAM]

    def _get_value_from_snp_column_label_string(self, the_index):
        """
        Parses snp level summary column label parameter by comma
        :param the_index: index of value to return
        :returns: string
        """
        if self._taskdict is None:
            return None
        if nbgwas_rest.SNP_LEVEL_SUMMARY_COL_LABEL_PARAM not in self._taskdict:
            return None
        the_str = self._taskdict[nbgwas_rest.SNP_LEVEL_SUMMARY_COL_LABEL_PARAM]

        split_str = the_str.split(',')
        if the_index < 0:
            return None
        if the_index >= len(split_str):
            return None
        return split_str[the_index]

    def get_snp_chromosome_label(self):
        """
        Gets label for chromosome column in SNP level summary file
        :return:
        """
        res = self._get_value_from_snp_column_label_string(0)
        if res is None:
            return nbgwas_rest.SNP_LEVEL_SUMMARY_CHROM_COL
        return res

    def get_snp_basepair_label(self):
        """
        Gets label for basepair column in SNP level summary file
        :return:
        """
        res = self._get_value_from_snp_column_label_string(1)
        if res is None:
            return nbgwas_rest.SNP_LEVEL_SUMMARY_BP_COL
        return res

    def get_snp_pvalue_label(self):
        """
        Gets label for pvalue column in SNP level summary file
        :return:
        """
        res = self._get_value_from_snp_column_label_string(2)
        if res is None:
            return nbgwas_rest.SNP_LEVEL_SUMMARY_PVAL_COL
        return res

    def get_ndex(self):
        """
        Gets ndex parameter
        :return:
        """
        if self._taskdict is None:
            return None
        if nbgwas_rest.NDEX_PARAM not in self._taskdict:
            return None
        return self._taskdict[nbgwas_rest.NDEX_PARAM]

    def get_snp_level_summary_file(self):
        """
        Gets snp level summary file path
        :return:
        """
        if self._taskdir is None:
            return None
        snp_file = os.path.join(self._taskdir,
                                nbgwas_rest.SNP_LEVEL_SUMMARY_PARAM)
        if not os.path.isfile(snp_file):
            return None
        return snp_file

    def get_protein_coding_file(self):
        """
        Gets protein coding file path by first seeing if
        a file with name nbgwas_rest.PROTEIN_CODING_PARAM
        resides in the tasks directory otherwise the code
        looks in the protein coding directory set in the
        constructor and looks for a file with name
        from get_protein_coding() (adding the suffix set
        in constructor if its not None)
        :return: path to protein coding file or None
        """
        """Look in task directory for protein coding file
        otherwise look in protein_coding_dir set in constructor
        """
        if self._taskdir is None:
            return None

        pc_file = os.path.join(self._taskdir,
                               nbgwas_rest.PROTEIN_CODING_PARAM)

        logger.debug('Looking for protein coding file in task: ' + pc_file)

        if os.path.isfile(pc_file):
            return pc_file

        if self._protein_coding_dir is None:
            logger.warning('Protein coding directory is None')
            return None

        p_code = self.get_protein_coding()

        if p_code is None:
            logger.warning('Protein coding parameter is None')
            return None

        pc_file = os.path.join(self._protein_coding_dir, p_code)
        if self._protein_coding_suffix is not None:
            pc_file = pc_file + str(self._protein_coding_suffix)

        logger.debug('Looking for protein coding file: ' + pc_file)

        if os.path.isfile(pc_file):
            return pc_file

        return None


class FileBasedSubmittedTaskFactory(object):
    """
    Reads file system to get tasks
    """
    def __init__(self, taskdir, protein_coding_dir,
                 protein_coding_suffix):
        self._taskdir = taskdir
        self._submitdir = None
        if self._taskdir is not None:
            self._submitdir = os.path.join(self._taskdir,
                                           nbgwas_rest.SUBMITTED_STATUS)
        self._protein_coding_dir = protein_coding_dir
        self._protein_coding_suffix = protein_coding_suffix
        self._problemlist = []

    def get_next_task(self):
        """
        Looks for next task in task dir. currently finds the first
        :return:
        """
        if self._submitdir is None:
            logger.error('Submit directory is None')
            return None
        if not os.path.isdir(self._submitdir):
            logger.error(self._submitdir +
                         ' does not exist or is not a directory')
            return None
        for entry in os.listdir(self._submitdir):
            fp = os.path.join(self._submitdir, entry)
            if not os.path.isdir(fp):
                continue
            for subentry in os.listdir(fp):
                subfp = os.path.join(fp, subentry)
                if os.path.isdir(subfp):
                    tjson = os.path.join(subfp, nbgwas_rest.TASK_JSON)
                    if os.path.isfile(tjson):
                        try:
                            with open(tjson, 'r') as f:
                                jsondata = json.load(f)
                            return FileBasedTask(subfp, jsondata,
                                                 protein_coding_dir=self.
                                                 _protein_coding_dir,
                                                 protein_coding_suffix=self.
                                                 _protein_coding_suffix)
                        except Exception as e:
                            if subfp not in self._problemlist:
                                logger.info('Skipping task: ' + subfp +
                                            ' due to error reading json' +
                                            ' file: ' + str(e))
                                self._problemlist.append(subfp)
        return None

    def get_size_of_problem_list(self):
        """
        Gets size of problem list
        :return:
        """
        return len(self._problemlist)

    def get_problem_list(self):
        """
        Gets problem list
        :return:
        """
        return self._problemlist


class NetworkXFromNDExFactory(object):
    """Factory to get networkx object from NDEx server
    """
    def __init__(self, ndex_server=None, username=None,
                 password=None):
        """Constructor"""
        self._ndex_server = ndex_server
        self._username = username
        self._password = password

    def get_networkx_object(self, ndex_uuid):
        """
        Given a NDEx uuid, this method returns
        the network as a networkx object
        :param ndex_uuid: NDEx uuid to get
        :return: networkx object upon success or None if unable to load
        """
        if ndex_uuid is None:
            logger.error('UUID passed in is None')
            return None
        cxnet = create_nice_cx_from_server(server=self._ndex_server,
                                           uuid=ndex_uuid)
        return cxnet.to_networkx()


class NbgwasTaskRunner(object):
    """
    Runs tasks created by Nbgwas REST service
    """

    NDEX_NAME = 'name'

    NEGATIVE_LOG = 'Negative Log'
    BINARIZED_HEAT = 'Binarized Heat'
    BINARIZE_HEAT_METHOD = 'binarize'
    NEG_LOG_HEAT_METHOD = 'neg_log'
    DIFFUSED_LOG = 'Diffused (Log)'
    DIFFUSED_BINARIZED = 'Diffused (Binarized)'
    DIFFUSE_METHOD = 'random_walk'

    def __init__(self, wait_time=30,
                 taskfactory=None,
                 networkfactory=None,
                 ):
        self._taskfactory = taskfactory
        self._wait_time = wait_time
        self._networkfactory = networkfactory

    def _get_networkx_object(self, task):
        """
        Examines task and generates appropriate
        networkx object that is returned
        :param task:
        :return: same task object
        """
        if task is None:
            logger.error('task is None')
            return None

        ndex_id = task.get_ndex()
        if ndex_id is not None:
            return self._get_networkx_object_from_ndex(ndex_id)

        return None

    def _get_networkx_object_from_ndex(self, ndex_id):
        """
        Extracts networkx object from ndex and relabels the nodes
        by the name of the node set as NDEX_NAME attribute.
        For example if original NDEx network looked like this if
        str(network.node):

        {1: {'name': 'node1'}, 2: {'name': 'node2'}}

        The returned network will look like this if str(network.node):

        {'node1': {'name': 'node1'}, 'node2': {'name': 'node2'}}

        :param task: contains id to get
        :return:
        """
        if self._networkfactory is None:
            logger.error('Network factory is None')
            return None

        dG = self._networkfactory.get_networkx_object(ndex_id)
        if dG is None:
            logger.error("None returned trying to get network")
            return None

        logger.debug('Generating name map')
        name_map = {i: j[NbgwasTaskRunner.NDEX_NAME]
                    for i, j in dG.node.items()}

        logger.debug('Calling networkx.relabel_nodes with name map')
        return nx.relabel_nodes(dG, name_map)

    def _process_task(self, task, delete_temp_files=True):
        """
        Processes a task
        :param taskdir:
        :return:
        """
        logger.info('Task dir: ' + task.get_taskdir())
        task.move_task(nbgwas_rest.PROCESSING_STATUS)

        n_obj = self._get_networkx_object(task)
        if n_obj is None:
            emsg = 'Unable to get networkx object for task'
            logger.error(emsg)
            task.move_task(nbgwas_rest.ERROR_STATUS,
                           error_message=emsg)
            return

        task.set_networkx_object(n_obj)

        result, emsg = self._run_nbgwas(task)

        if result is None:
            if emsg is None:
                emsg = 'No result generated'
            logger.error('Task failed ' + emsg)
            task.move_task(nbgwas_rest.ERROR_STATUS,
                           error_message=emsg)
            return

        logger.info('Task processing completed')
        task.set_result_data(result)
        task.save_task()
        task.move_task(nbgwas_rest.DONE_STATUS,
                       delete_temp_files=delete_temp_files)
        return

    def _run_nbgwas(self, task):
        """
        Runs nbgwas processing
        :param task: The task to process which is assumed to
                     have a valid network when task.get_networkx_object()
                     is called
        :return: tuple if successful result will be ({}, None) otherwise
                 (None, 'str containing error message') or (None, None)

        """
        logger.debug('Creating Nbgwas object')
        g = Nbgwas()

        logger.debug('Creating NBgwas.Snps object')
        g.snps.from_files(
            task.get_snp_level_summary_file(),
            task.get_protein_coding_file(),
            snp_chrom_col=task.get_snp_chromosome_label(),
            snp_bp_col=task.get_snp_basepair_label(),
            pval_col=task.get_snp_pvalue_label(),
            snp_kwargs={'sep': '\s+|\s*,\s*'},
            pc_kwargs={'sep': '\s+', 'names': ['Chrom', 'Start', 'End'],
                       'index_col': 0}
        )

        logger.debug('Assigning SNPS to genes')
        g.genes = g.snps.assign_snps_to_genes(window_size=task.get_window(),
                                              to_Gene=True)

        logger.debug('Converting to head using method: ' +
                     NbgwasTaskRunner.BINARIZE_HEAT_METHOD)
        g.genes.convert_to_heat(method=NbgwasTaskRunner.BINARIZE_HEAT_METHOD,
                                name=NbgwasTaskRunner.BINARIZED_HEAT)

        logger.debug('2nd converting to head using method: ' +
                     NbgwasTaskRunner.NEG_LOG_HEAT_METHOD)
        g.genes.convert_to_heat(method=NbgwasTaskRunner.NEG_LOG_HEAT_METHOD,
                                name=NbgwasTaskRunner.NEGATIVE_LOG)

        g.network = task.get_networkx_object()

        logger.debug('map to node table')
        g.map_to_node_table(columns=[NbgwasTaskRunner.BINARIZED_HEAT,
                                     NbgwasTaskRunner.NEGATIVE_LOG])

        logger.debug('Running diffuse ')
        g.diffuse(method=NbgwasTaskRunner.DIFFUSE_METHOD,
                  alpha=task.get_alpha(),
                  node_attribute=NbgwasTaskRunner.BINARIZED_HEAT,
                  result_name=NbgwasTaskRunner.DIFFUSED_BINARIZED)

        logger.debug('Running diffuse 2')

        g.diffuse(method=NbgwasTaskRunner.DIFFUSE_METHOD,
                  alpha=task.get_alpha(),
                  node_attribute=NbgwasTaskRunner.NEGATIVE_LOG,
                  result_name=NbgwasTaskRunner.DIFFUSED_LOG)


        logger.debug('Extract node name and scores from node_table')
        # the data frame below is the result give the name and
        # Diffused (Log) to the user
        unsortdf = g.network.node_table[[g.network.node_name,
                                         NbgwasTaskRunner.DIFFUSED_LOG]]

        logger.debug('Sort results by scores')
        dframe = unsortdf.sort_values(by=NbgwasTaskRunner.DIFFUSED_LOG,
                                      ascending=False)

        logger.debug('Put results into dict()')
        result = {gene: score for gene, score in dframe.values}
        return result, None

    def run_tasks(self, keep_looping=lambda: True):
        """
        Main entry point, this function loops looking for
        tasks to run.
        :param keep_looping: Function that should return True to
                             denote this method should keep waiting
                             for new Tasks or False to exit
        :return:
        """
        while keep_looping():
            task = self._taskfactory.get_next_task()
            if task is None:
                time.sleep(self._wait_time)
                continue

            logger.debug('Found a task: ' + str(task.get_taskdir()))
            try:
                self._process_task(task)
            except Exception as e:
                emsg = ('Caught exception processing task: ' +
                        task.get_taskdir() + ' : ' + str(e))
                logger.exception('Skipping task cause - ' + emsg)
                task.move_task(nbgwas_rest.ERROR_STATUS,
                               error_message=emsg)


def main(args):
    """Main entry point"""
    desc = """Runs tasks generated by NAGA REST service

    """
    theargs = _parse_arguments(desc, args[1:])
    theargs.program = args[0]
    theargs.version = nbgwas_rest.__version__
    _setuplogging(theargs)
    try:
        ab_tdir = os.path.abspath(theargs.taskdir)
        ab_pdir = os.path.abspath(theargs.protein_coding_dir)
        logger.debug('Task directory set to: ' + ab_tdir)

        tfac = FileBasedSubmittedTaskFactory(ab_tdir,
                                             ab_pdir,
                                             theargs.protein_coding_suffix)
        netfac = NetworkXFromNDExFactory(ndex_server=theargs.ndexserver)
        runner = NbgwasTaskRunner(taskfactory=tfac,
                                  networkfactory=netfac,
                                  wait_time=theargs.wait_time)

        runner.run_tasks()
    except Exception:
        logger.exception("Error caught exception")
        return 2
    finally:
        logging.shutdown()


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv))
