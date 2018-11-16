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
# global api object
app = Flask(__name__, instance_relative_config=True)
api = Api(app, version=str(__version__),
          title='Network Boosted Genome Wide Association Studies (NBGWAS) ',
          description=desc, example='put example here')
app.config.SWAGGER_UI_DOC_EXPANSION = 'list'

ALPHA_PARAM = 'alpha'
NETWORK_PARAM = 'network'
COLUMN_PARAM = 'column'
SEEDS_PARAM = 'seeds'
NDEX_PARAM = 'ndex'

JOB_PATH = '/tmp/nbgwas'
TASK_JSON = 'task.json'
NETWORK_DATA = 'network.data'
LOCATION = 'Location'
RESULT = 'result.json'
WAIT_COUNT = 60
SLEEP_TIME = 10


def create_task(request_obj):
    params = {}
    params[ALPHA_PARAM] = float(request_obj.values.get(ALPHA_PARAM, 0.5))

    if SEEDS_PARAM in request_obj.values:
        params[SEEDS_PARAM] = request_obj.values[SEEDS_PARAM]

    params['uuid'] = str(uuid.uuid4())

    taskpath = os.path.join(JOB_PATH, request_obj.remote_addr, params['uuid'])
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
        params[COLUMN_PARAM] = request_obj.values[COLUMN_PARAM]  # what is 0.8?

    elif NDEX_PARAM in request_obj.values:
        app.logger.debug("Getting network from NDEx")
        params[NDEX_PARAM] = request_obj.values[NDEX_PARAM]
    else:
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


def get_task(uuidstr, hintlist=None, basedir=JOB_PATH):

    if hintlist is not None:
        for subdir in hintlist:
            taskpath = os.path.join(basedir, subdir, uuidstr)
            if os.path.isdir(taskpath):
                return taskpath

    for entry in os.listdir(basedir):
        fullpath = os.path.join(basedir, entry)
        if not os.path.isdir(fullpath):
            taskpath = os.path.join(fullpath, uuidstr)
            if os.path.isdir(taskpath):
                return taskpath
    return None


# NETWORK_PARAM: fields.Arbitrary(description='If set, loads network from file (TODO explain format)')
task_fields = api.model('tasks', {
    ALPHA_PARAM: fields.Float(0.2, min=0.0, max=1.0,
                              description='Alpha parameter to use in random walk function'),
    NDEX_PARAM: fields.String(None, description='If set, grabs network matching ID from NDEX http://http://www.ndexbio.org/'),
    SEEDS_PARAM: fields.String(None, description='Comma list of genes...'),
    COLUMN_PARAM: fields.String(None, description='Setting this gets network from bigim?'),
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
            abort(500, 'Unable to create task')


@api.route('/nbgwas/tasks/<string:id>', endpoint='nbgwas/tasks')
class TaskGetterApp(Resource):

    def head(self, id):
        resp = flask.make_response()
        resp.status_code = 200
        return resp

    def get(self, id):
        resp = flask.make_response()
        resp.status_code = 200
        return resp

    def delete(self, id):
        """
        Deletes task associated with id passed in
        :param id: task id to delete. If set to 'all' then all tasks coming
                   from ip address will be deleted
        :return: Status code 200 upon success otherwise 500 and a message
        """
        resp = flask.make_response()
        resp.status_code = 200
        return resp


@api.doc('Runs Network Boosted GWAS in legacy mode', example='class level examplexxxx')
@api.route('/nbgwas', endpoint='nbgswas')
class RestApp(Resource):
    """Old interface that returns the result immediately"""

    @api.doc('hello', params={ALPHA_PARAM: 'Alpha parameter to use in random walk '
                                           'with restart model function should be set to values between 0-1',
                              NDEX_PARAM: 'If set, grabs network matching ID from NDEX http://http://www.ndexbio.org/',
                              NETWORK_PARAM: 'If set, loads network from file (TODO explain format)',
                              SEEDS_PARAM: 'Comma list of genes...',
                              COLUMN_PARAM: 'Setting this gets network from bigim?'
                              },
             description='Legacy REST service that runs NBGWAS and waits for result',
             example='Add example here',
             responses={
                 200: 'Success',
                 500: 'Internal server error'
             })
    @api.deprecated
    def post(self):
        """Runs Network Boosted GWAS"""
        app.logger.debug("Begin!")

        try:
            res = create_task(request)
            counter = 0

            while counter < WAIT_COUNT:
                taskpath = get_task(res)
                if taskpath is not None:
                    break
                app.logger.debug('Sleeping while waiting for ' + res)
                time.sleep(SLEEP_TIME)

            result = os.path.join(taskpath, RESULT)
            with open(result, 'r') as f:
                data = json.load(result)

            resp = flask.make_response()
            resp.status_code = 200
            resp.data = data
            return resp
        except OSError as e:
            app.logger.exception('Error creating task')
            abort(500, 'Unable to create task')
