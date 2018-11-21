# -*- coding: utf-8 -*-

"""Top-level package for nbgwas_rest."""

__author__ = """Chris Churas"""
__email__ = 'churas.camera@gmail.com'
__version__ = '0.1.0'

import os
import shutil
import json
import uuid
import time
import flask
from flask import Flask, request, jsonify, Response
from flask_restplus import reqparse, abort, Api, Resource, fields

desc = """A REST service for an accessible, fast and customizable network propagation system
for pathway interpretation of Genome Wide Association Studies (GWAS)
"""


NBGWAS_REST_SETTINGS_ENV='NBGWAS_REST_SETTINGS'
# global api object
app = Flask(__name__)

JOB_PATH_KEY = 'JOB_PATH'
WAIT_COUNT_KEY = 'WAIT_COUNT'
SLEEP_TIME_KEY = 'SLEEP_TIME'
SEQUENTIAL_UUID_KEY='SEQUENTIAL_UUID'


app.config[JOB_PATH_KEY] = '/tmp'
app.config[WAIT_COUNT_KEY] = 60
app.config[SLEEP_TIME_KEY] = 10

app.config.from_envvar(NBGWAS_REST_SETTINGS_ENV, silent=True)


TASK_JSON = 'task.json'
NETWORK_DATA = 'network.data'
LOCATION = 'Location'
RESULT = 'result.json'

STATUS_RESULT_KEY = 'status'
NOTFOUND_STATUS = 'notfound'
UNKNOWN_STATUS = 'unknown'
SUBMITTED_STATUS = 'submitted'
PROCESSING_STATUS = 'processing'
DONE_STATUS = 'done'
ERROR_STATUS = 'error'
RESULT_KEY = 'result'


api = Api(app, version=str(__version__),
          title='Network Boosted Genome Wide Association Studies (NBGWAS) ',
          description=desc, example='put example here')
app.config.SWAGGER_UI_DOC_EXPANSION = 'list'

ALPHA_PARAM = 'alpha'
NETWORK_PARAM = 'network'
COLUMN_PARAM = 'column'
SEEDS_PARAM = 'seeds'
NDEX_PARAM = 'ndex'
REMOTEIP_PARAM = 'remoteip'
UUID_PARAM = 'uuid'
ERROR_PARAM = 'error'

uuid_counter = 1


def get_uuid():
    """
    Generates UUID and returns as string. With one caveat,
    if app.config[USE_SEQUENTIAL_UUID] is set and True
    then uuid_counter is returned and incremented
    :return: uuid as string
    """
    if SEQUENTIAL_UUID_KEY in app.config:
        if app.config[SEQUENTIAL_UUID_KEY] is True:
            global uuid_counter
            sequuid = str(uuid_counter)

            uuid_counter = uuid_counter + 1
            return sequuid
    return str(uuid.uuid4())


def get_submit_dir():
    """
    Gets base directory where submitted jobs will be placed
    :return:
    """
    return os.path.join(app.config[JOB_PATH_KEY], SUBMITTED_STATUS)


def get_processing_dir():
    """
        Gets base directory where processing jobs will be placed
    :return:
    """
    return os.path.join(app.config[JOB_PATH_KEY], PROCESSING_STATUS)


def get_done_dir():
    """
        Gets base directory where completed jobs will be placed

    :return:
    """
    return os.path.join(app.config[JOB_PATH_KEY], DONE_STATUS)


def create_task(params):
    """
    Creates a task by consuming data from request_obj passed in
    and persisting that information to the filesystem under
    JOB_PATH/SUBMIT_DIR/<IP ADDRESS>/UUID with various parameters
    stored in TASK_JSON file and if the 'network' file is set
    that data is dumped to NETWORK_DATA file within the directory
    :param request_obj:
    :return: string that is a uuid which denotes directory name
    """
    params['uuid'] = get_uuid()
    taskpath = os.path.join(get_submit_dir(), params['remoteip'],
                            params['uuid'])
    os.makedirs(taskpath, mode=0o755)

    # Getting network
    if params[NETWORK_PARAM] is not None:
        app.logger.debug('Networkfile: ' + str(params[NETWORK_PARAM]))
        networkfile_path = os.path.join(taskpath, NETWORK_DATA)
        with open(networkfile_path, 'wb') as f:
            shutil.copyfileobj(params[NETWORK_PARAM].stream, f)
            f.flush()
        app.logger.debug(networkfile_path + ' saved and it is ' +
                         str(os.path.getsize(networkfile_path)) + ' bytes')
        params[NETWORK_PARAM] = None
    elif params[COLUMN_PARAM] is not None:
        params[COLUMN_PARAM] = str(params[COLUMN_PARAM]).strip()
    elif params[NDEX_PARAM] is not None:
        app.logger.debug("Validating ndex id")
        params[NDEX_PARAM] = str(params[NDEX_PARAM]).strip()
        if len(params[NDEX_PARAM]) > 40:
            raise Exception(NDEX_PARAM + ' parameter value is too long to '
                                         'be an NDex UUID')
    else:
        app.logger.error('Missing one of the required parameters')
        raise Exception('One of the three parameters must be '
                        'passed with request: ' + NETWORK_PARAM +
                        ', ' + COLUMN_PARAM + ', ' + NDEX_PARAM)

    tmp_task_json = TASK_JSON + '.tmp'
    taskfilename = os.path.join(taskpath, tmp_task_json)
    with open(taskfilename, 'w') as f:
        json.dump(params, f)
        f.flush()

    shutil.move(taskfilename, os.path.join(taskpath, TASK_JSON))
    return params['uuid']


def log_task_json_file(taskpath):
    """
    Writes information about task to logger
    :param taskpath: path to task
    :return: None
    """
    if taskpath is None:
        return None

    tmp_task_json = TASK_JSON
    taskfilename = os.path.join(taskpath, tmp_task_json)

    if not os.path.isfile(taskfilename):
        return None

    with open(taskfilename, 'r') as f:
        data = json.load(f)
        app.logger.info('Json file of task: ' + str(data))


def get_task(uuidstr, iphintlist=None, basedir=None):
    """
    Gets task under under basedir.
    :param uuidstr: uuid string for task
    :param iphintlist: list of ip addresses as strings to speed up search.
                       if set then each
                       '/<basedir>//<iphintlist entry>/<uuidstr>'
                       is first checked and if the path is a directory
                       it is returned
    :param basedir:  base directory as string ie /foo
    :return: full path to task or None if not found
    """
    if uuidstr is None:
        app.logger.warning('Path passed in is None')
        return None

    if basedir is None:
        app.logger.error('basedir is None')
        return None

    if not os.path.isdir(basedir):
        app.logger.error(basedir + ' is not a directory')
        return None

    # Todo: Add logic to leverage iphintlist
    # Todo: Add a retry if not found with small delay in case of dir is moving
    for entry in os.listdir(basedir):
        ip_path = os.path.join(basedir, entry)
        if not os.path.isdir(ip_path):
            continue
        for subentry in os.listdir(ip_path):
            if uuidstr != subentry:
                continue
            taskpath = os.path.join(ip_path, subentry)

            if os.path.isdir(taskpath):
                return taskpath
    return None


def wait_for_task(uuidstr, hintlist=None):
    """
    Waits for task to appear in done directory
    :param uuidstr: uuid of task
    :param hintlist: list of ip addresses to search under
    :return: string containing full path to task or None if not found
    """
    if uuidstr is None:
        app.logger.error('uuid is None')
        return None

    counter = 0
    taskpath = None
    done_dir = get_done_dir()
    while counter < app.config[WAIT_COUNT_KEY]:
        taskpath = get_task(uuidstr, iphintlist=hintlist,
                            basedir=done_dir)
        if taskpath is not None:
            break
        app.logger.debug('Sleeping while waiting for ' + uuidstr)
        time.sleep(app.config[SLEEP_TIME_KEY])
        counter = counter + 1

    if taskpath is None:
        app.logger.info('Wait time exceeded while looking for: ' + uuidstr)

    return taskpath


post_parser = reqparse.RequestParser()
post_parser.add_argument(ALPHA_PARAM, type=float, default=0.5,
                         help='Alpha parameter to use in random walk function',
                         location='form')
post_parser.add_argument(SEEDS_PARAM, type=str,
                         help='Comma delimited list of genes',
                         location='form')
post_parser.add_argument(NDEX_PARAM,
                         help='UUID of network to load from'
                              'NDex http://www.ndexbio.org',
                         location='form')
post_parser.add_argument(COLUMN_PARAM, type=str, help='biggim',
                         location='form')
post_parser.add_argument(NETWORK_PARAM, type=reqparse.FileStorage,
                         help='Network file in sif format', location='files')

@api.doc('Runs NEtwork boosted gwas')
@api.route('/nbgwas/tasks', endpoint='nbgswas/tasks')
class TaskBasedRestApp(Resource):
    @api.doc('Runs Network Boosted GWAS',
             responses={
                 202: 'Success',
                 500: 'Internal server error'
             })
    @api.header(LOCATION, 'If successful, URL of created task', example='he')
    @api.expect(post_parser)
    def post(self):
        """
        Runs Network Boosted GWAS asynchronously

        Upon success this endpoint will return a status code of 202
        and in the header
        set the Location to newly created task endpoint that can
        be polled to
        check on status. For more information on results
        see GET /nbgwas/tasks/{id} endpoint

        """
        app.logger.debug("Begin!")

        try:
            params = post_parser.parse_args(request, strict=True)
            params['remoteip'] = request.remote_addr
            res = create_task(params)
            resp = flask.make_response()
            resp.headers[LOCATION] = 'nbgwas/tasks/' + res
            resp.status_code = 202
            return resp
        except OSError as e:
            app.logger.exception('Error creating task')
            abort(500, 'Unable to create task ' + str(e))
        except Exception as ea:
            app.logger.exception('Error creating task')
            abort(500, 'Unable to create task ' + str(ea))


@api.route('/nbgwas/tasks/<string:id>', endpoint='nbgwas/tasks')
class TaskGetterApp(Resource):

    @api.doc('Gets status and response of submitted NBGWAS task',
             responses={
                 200: 'Success in asking server, but does not mean'
                      'task has completed. See the json response'
                      'in body for status',
                 410: 'Task not found',
                 500: 'Internal server error'
             })
    def get(self, id):
        """
        Gets result of task if completed
        {id} is the id of the task obtained from Location field in
        header of /nbgwas/tasks POST endpoint

        The status will be returned in this json format:

        For incomplete/failed jobs

        {
          "status" : "notfound|submitted|processing|error"
        }

        For complete jobs an additional field result is included

        {
          "status" : "done",
          "result" : { "GENE1": SCORE, "GENE2", SCORE2 }
        }
        """
        hintlist = [request.remote_addr]
        taskpath = get_task(id, iphintlist=hintlist,
                            basedir=get_submit_dir())

        if taskpath is not None:
            resp = jsonify({STATUS_RESULT_KEY: SUBMITTED_STATUS})
            resp.status_code = 200
            return resp

        taskpath = get_task(id, iphintlist=hintlist,
                            basedir=get_processing_dir())

        if taskpath is not None:
            resp = jsonify({STATUS_RESULT_KEY: PROCESSING_STATUS})
            resp.status_code = 200
            return resp

        taskpath = get_task(id, iphintlist=hintlist,
                            basedir=get_done_dir())

        if taskpath is None:
            resp = jsonify({STATUS_RESULT_KEY: NOTFOUND_STATUS})
            resp.status_code = 410
            return resp

        result = os.path.join(taskpath, RESULT)
        if not os.path.isfile(result):
            resp = jsonify({STATUS_RESULT_KEY: ERROR_STATUS})
            resp.status_code = 500
            return resp

        log_task_json_file(taskpath)
        app.logger.info('Result file is ' + str(os.path.getsize(result)) +
                        ' bytes')

        with open(result, 'r') as f:
            data = json.load(f)

        return jsonify({STATUS_RESULT_KEY: DONE_STATUS,
                       RESULT_KEY: data})

    def delete(self, id):
        """
        Deletes task associated with id passed in

        Currently not implemented and will always return code 503
        """
        resp = flask.make_response()
        resp.data = 'Currently not implemented'
        resp.status_code = 503
        return resp


@api.doc('Runs Network Boosted GWAS in legacy mode', example='class level examplexxxx')
@api.route('/nbgwas', endpoint='nbgswas')
class RestApp(Resource):
    """Old interface that returns the result immediately"""

    @api.doc('hello',
             description='Legacy REST service that runs NBGWAS and waits for result'
                         ' for more information see POST /nbgwas/tasks endpoint',
             responses={
                 200: 'Success',
                 408: 'Internal server error or task took too long to run',
                 500: 'Internal server error'
             })
    @api.deprecated
    @api.expect(post_parser)
    def post(self):
        """Legacy NBGWAS POST endpoint
        Result is json in following format upon success:

        {
          "GENE1": SCORE1,
          "GENE2": SCORE2
        }

        If there was a problem parsing a parameter then this json
        may be output in body

        {
          "message": "description of error"
        }

        """
        app.logger.debug("Begin!")

        try:
            params = post_parser.parse_args(request, strict=True)
            params['remoteip'] = request.remote_addr
            res = create_task(params)
            hintlist = [request.remote_addr]
            taskpath = wait_for_task(res, hintlist=hintlist)
            if taskpath is None:
                abort(408, 'There was an internal problem or the task'
                           'took too long to run')

            result = os.path.join(taskpath, RESULT)
            if not os.path.isfile(result):
                abort(500, 'No results found for task')
            with open(result, 'r') as f:
                data = json.load(f)

            return jsonify(data)
        except OSError as e:
            app.logger.exception('Error creating task')
            abort(500, 'Unable to create task')
