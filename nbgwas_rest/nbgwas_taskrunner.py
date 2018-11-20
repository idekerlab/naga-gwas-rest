#!/usr/bin/env python


import os
import sys
import argparse
import logging
import time
import shutil
import json

import nbgwas_rest


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
    parser.add_argument('--wait_time', type=int, default=30,
                        help='Time in seconds to wait'
                             'before looking for new'
                             'tasks')
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
    def __init__(self, taskdir, taskdict):
        self._taskdir = taskdir
        self._taskdict = taskdict

    def move_task(self, new_state):
        """
        Changes state of task to new_state
        :param new_state: new state
        :return: None
        """
        taskuuid = os.path.basename(self._taskdir)
        ipdir = os.path.dirname(self._taskdir)
        ipaddress = os.path.basename(ipdir)
        curstate = os.path.basename(ipdir)
        if curstate == new_state:
            logger.debug('Attempt to move task to same state: ' +
                         self._taskdir)
            return None

        ptaskdir = os.path.join(self._taskdir, new_state, ipaddress, taskuuid)
        shutil.move(self._taskdir, ptaskdir)
        self._taskdir = ptaskdir
        return None

    def set_taskdir(self, taskdir):
        self._taskdir = taskdir

    def get_taskdir(self):
        return self._taskdir

    def set_taskdict(self, taskdict):
        self._taskdict = taskdict

    def get_taskdict(self):
        return self._taskdict

    def get_ipaddress(self):
        """
        Gets ip address
        :return:
        """
        return self._taskdict[nbgwas_rest.REMOTEIP_PARAM]

    def get_alpha(self):
        return self._taskdict[nbgwas_rest.ALPHA_PARAM]

    def get_seeds(self):
        return self._taskdict[nbgwas_rest.SEEDS_PARAM]

    def get_bigim(self):
        if nbgwas_rest.COLUMN_PARAM not in self._taskdict:
            return None
        return self._taskdict[nbgwas_rest.COLUMN_PARAM]

    def get_ndex(self):
        if nbgwas_rest.NDEX_PARAM not in self._taskdict:
            return None
        return self._taskdict[nbgwas_rest.NDEX_PARAM]

    def get_network(self):
        if nbgwas_rest.NETWORK_PARAM not in self._taskdict:
            return None
        return os.path.join(self._taskdir, nbgwas_rest.NETWORK_DATA)


class FileBasedSubmittedTaskFactory(object):
    """
    Reads file system to get tasks
    """
    def __init__(self, taskdir):
        self._taskdir = taskdir
        self._submitdir = os.path.join(self._taskdir,
                                       nbgwas_rest.SUBMITTED_STATUS)

    def _find_next_task(self):
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
                    return subfp
        return None

    def get_next_task(self):
        """
        Gets a task that needs to be processed
        :return:
        """
        taskdir = self._find_next_task()
        if taskdir is None:
            return None

        tjson = os.path.join(taskdir, nbgwas_rest.TASK_JSON)
        jsondata = None
        if os.path.isfile(tjson):
            with open(tjson, 'r') as f:
                jsondata = json.load(f)

        return FileBasedTask(taskdir, jsondata)


class NbgwasTaskRunner(object):
    """
    Runs tasks created by Nbgwas REST service
    """
    def __init__(self, wait_time=30,
                 taskfactory=None,
                 processor=None):
        self._taskfactory = taskfactory
        self._wait_time = wait_time

    def _process_task(self, task):
        """
        Processes a task
        :param taskdir:
        :return:
        """
        logger.info('Task dir: ' + task.get_taskdir())
        # task.move_task(nbgwas_rest.PROCESSING_STATUS)
        time.sleep(100)
        # do work here

        # task.move_task(nbgwas_rest.DONE_STATUS)

    def run_tasks(self):
        """
        Main entry point, this function loops looking for
        tasks to run.
        :return:
        """
        while 1 < 2:
            task = self._taskfactory.get_next_task()
            if task is None:
                time.sleep(self._wait_time)
                continue
            logger.debug('Found a task: ' + str(task))
            self._process_task(task)


def main(args):
    """Main entry point"""
    desc = """Runs tasks generated by NBGWAS REST service

    """
    theargs = _parse_arguments(desc, args[1:])
    theargs.program = args[0]
    theargs.version = nbgwas_rest.__version__
    _setuplogging(theargs)
    try:
        ab_tdir = os.path.abspath(theargs.taskdir)
        logger.debug('Task directory set to: ' + ab_tdir)

        tfac = FileBasedSubmittedTaskFactory(ab_tdir)
        runner = NbgwasTaskRunner(taskfactory=tfac,
                                  wait_time=theargs.wait_time)
        runner.run_tasks()
    except Exception as e:
        logger.exception("Error caught exception")
        return 2
    finally:
        logging.shutdown()


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv))
