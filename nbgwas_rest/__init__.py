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

JSON_MIMETYPE = 'application/json'

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


SUBMIT_DIR = 'submitted'
PROCESSING_DIR = 'processing'
DONE_DIR = 'done'
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

uuid_counter=1

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
    return os.path.join(app.config[JOB_PATH_KEY], SUBMIT_DIR)


def get_processing_dir():
    """
        Gets base directory where processing jobs will be placed
    :return:
    """
    return os.path.join(app.config[JOB_PATH_KEY], PROCESSING_DIR)


def get_done_dir():
    """
        Gets base directory where completed jobs will be placed

    :return:
    """
    return os.path.join(app.config[JOB_PATH_KEY], DONE_DIR)


def create_task(request_obj):
    """
    Creates a task by consuming data from request_obj passed in
    and persisting that information to the filesystem under
    JOB_PATH/SUBMIT_DIR/<IP ADDRESS>/UUID with various parameters
    stored in TASK_JSON file and if the 'network' file is set
    that data is dumped to NETWORK_DATA file within the directory
    :param request_obj:
    :return: string that is a uuid which denotes directory name
    """
    params = {}
    params[ALPHA_PARAM] = float(request_obj.values.get(ALPHA_PARAM, 0.5))

    if SEEDS_PARAM in request_obj.values:
        params[SEEDS_PARAM] = request_obj.values[SEEDS_PARAM]

    params['uuid'] = get_uuid()
    params['remoteip'] = request_obj.remote_addr
    taskpath = os.path.join(get_submit_dir(), params['remoteip'],
                            params['uuid'])
    os.makedirs(taskpath, mode=0o755)

    # Getting network
    if NETWORK_PARAM in request_obj.files:
        network_file = request_obj.files[NETWORK_PARAM]
        app.logger.debug('Networkfile: ' + str(network_file))
        networkfile_path = os.path.join(taskpath, NETWORK_DATA)

        with open(networkfile_path, 'wb') as f:
            shutil.copyfileobj(network_file.stream, f)
            f.flush()
    elif COLUMN_PARAM in request_obj.values:
        app.logger.debug("Getting file from BigGIM")
        # what is 0.8?
        params[COLUMN_PARAM] = request_obj.values[COLUMN_PARAM]
    elif NDEX_PARAM in request_obj.values:
        app.logger.debug("Getting network from NDEx")
        params[NDEX_PARAM] = request_obj.values[NDEX_PARAM]
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


task_fields = api.model('tasks', {
    ALPHA_PARAM: fields.Float(0.2, min=0.0, max=1.0,
                              description='Alpha parameter to use in random '
                                          'walk function'),
    NDEX_PARAM: fields.String(None, description='If set, grabs network'
                                                ' matching ID from NDEX '
                                                'http://http://www.ndexbio.'
                                                'org/'),
    SEEDS_PARAM: fields.String(None, description='Comma list of genes...'),
    COLUMN_PARAM: fields.String(None, description='Setting this gets '
                                                  'network from bigim?'),
})

@api.doc('Runs NEtwork boosted gwas')
@api.route('/nbgwas/tasks', endpoint='nbgswas/tasks')
class TaskBasedRestApp(Resource):

    @api.doc('Runs Network Boosted GWAS',
             responses={
                 202: 'Success',
                 500: 'Internal server error'
             })
    @api.header(LOCATION, 'If successful, URL of created task', example='he')
    @api.expect(task_fields)
    def post(self):
        """
        Runs Network Boosted GWAS asynchronously

        Some more information here
        """
        app.logger.debug("Begin!")

        try:
            res = create_task(request)
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
                 200: 'Success',
                 410: 'Task not found',
                 500: 'Internal server error'
             })
    def get(self, id):
        """
        Gets result of task if completed
        :param id:
        :return:
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
        :param id: task id to delete. If set to 'all' then all tasks coming
                   from ip address will be deleted
        :return: Currently not implemented and will always return code 503
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
             description='Legacy REST service that runs NBGWAS and waits for result',
             responses={
                 200: 'Success',
                 408: 'Internal server error or task took too long to run',
                 500: 'Internal server error'
             })
    @api.deprecated
    @api.expect(task_fields)
    def post(self):
        """Runs Network Boosted GWAS"""
        app.logger.debug("Begin!")

        try:
            res = create_task(request)
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
