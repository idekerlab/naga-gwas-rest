# -*- coding: utf-8 -*-

"""Top-level package for nbgwas_rest."""

__author__ = """Chris Churas"""
__email__ = 'churas.camera@gmail.com'
__version__ = '0.2.0'

import os
import shutil
import json
import uuid
import time
import flask
from flask import Flask, request, jsonify
from flask_restplus import reqparse, abort, Api, Resource



desc = """This system is designed to use biological networks to analyze GWAS results.

A GWAS association score is assigned to the genes. A molecular network is downloaded from the NDEx database, and network propagation is performed, providing a set of
 new scores for each gene. The top hits on this list form a new subnetwork, which can be compared to a set of gold standard genes in order to evaluate the
 enrichment for previously discovered biology. 
 
 See https://github.com/shfong/nbgwas for details.
""" # noqa

NBGWAS_REST_SETTINGS_ENV = 'NBGWAS_REST_SETTINGS'
# global api object
app = Flask(__name__)

JOB_PATH_KEY = 'JOB_PATH'
WAIT_COUNT_KEY = 'WAIT_COUNT'
SLEEP_TIME_KEY = 'SLEEP_TIME'

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

SNP_ANALYZER_NS = 'snp_analyzer'

api = Api(app, version=str(__version__),
          title='Network Boosted Genome Wide Association Studies (NBGWAS) ',
          description=desc, example='put example here')

# need to clear out the default namespace
api.namespaces.clear()

ns = api.namespace(SNP_ANALYZER_NS, description='snp analyzer')

app.config.SWAGGER_UI_DOC_EXPANSION = 'list'

ALPHA_PARAM = 'alpha'
NETWORK_PARAM = 'network'
NDEX_PARAM = 'ndex'
REMOTEIP_PARAM = 'remoteip'
UUID_PARAM = 'uuid'
ERROR_PARAM = 'error'
WINDOW_PARAM = 'window'
SNP_LEVEL_SUMMARY_PARAM = 'snp_level_summary'
PROTEIN_CODING_PARAM = 'protein_coding'

SNP_ANALYZER_TASK = 'snpanalyzer'

uuid_counter = 1


def get_uuid():
    """
    Generates UUID and returns as string. With one caveat,
    if app.config[USE_SEQUENTIAL_UUID] is set and True
    then uuid_counter is returned and incremented
    :return: uuid as string
    """
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
    params['tasktype'] = SNP_ANALYZER_TASK
    taskpath = os.path.join(get_submit_dir(), str(params['remoteip']),
                            str(params['uuid']))
    os.makedirs(taskpath, mode=0o755)

    # Getting network
    if SNP_LEVEL_SUMMARY_PARAM not in params or \
        params[SNP_LEVEL_SUMMARY_PARAM] is None:
        raise Exception(SNP_LEVEL_SUMMARY_PARAM + ' is required')

    app.logger.debug('snp level summary: ' + str(params[SNP_LEVEL_SUMMARY_PARAM]))
    networkfile_path = os.path.join(taskpath, SNP_LEVEL_SUMMARY_PARAM)
    with open(networkfile_path, 'wb') as f:
        shutil.copyfileobj(params[SNP_LEVEL_SUMMARY_PARAM].stream, f)
        f.flush()
    params[SNP_LEVEL_SUMMARY_PARAM] = SNP_LEVEL_SUMMARY_PARAM
    app.logger.debug(networkfile_path + ' saved and it is ' +
                     str(os.path.getsize(networkfile_path)) + ' bytes')

    if NDEX_PARAM not in params or params[NDEX_PARAM] is None:
        raise Exception(NDEX_PARAM + ' is required')

    app.logger.debug("Validating ndex id")
    params[NDEX_PARAM] = str(params[NDEX_PARAM]).strip()
    if len(params[NDEX_PARAM]) > 40:
        raise Exception(NDEX_PARAM + ' parameter value is too long to '
                                     'be an NDex UUID')

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
post_parser.add_argument(PROTEIN_CODING_PARAM, choices=['hg18', 'hg19'],
                         default='hg19', required=True,
                         help='Sets which protein coding table to use. '
                              ' Values correspond to NCBI Human Genome Builds',
                         location='form')
post_parser.add_argument(NDEX_PARAM, required=True,
                         help='NDEx (http://www.ndexbio.org) UUID of network '
                              'to load. For example, to use the Parsimonious '
                              'Composite Network (PCNet), one would use this:'
                              ' f93f402c-86d4-11e7-a10d-0ac135e8bacf',
                         location='form')
post_parser.add_argument(SNP_LEVEL_SUMMARY_PARAM, type=reqparse.FileStorage,
                         required=True,
                         help='Comma or tab delimited file with format of'
                              ' chromosome,basepair,p_value. To dictate '
                              'columns from the file, please directly '
                              'install the nbgwas library directly. See '
                              ' https://github.com/shfong/nbgwas for '
                              'more information. **NOTE:** This'
                              ' code assumes the first line of the file is'
                              ' the header', location='files')
post_parser.add_argument(ALPHA_PARAM, type=float,
                         help='Sets propagation constant alpha with allowed '
                              'values between 0 and 1, representing the '
                              'probability of walking to network neighbors '
                              'as opposed to reseting to the original '
                              'distribution. Larger values induce more '
                              'spread on the network. If unset, then optimal'
                              ' parameter is selected by linear model derived'
                              ' from (huang, cell systems 2018 '
                              'https://doi.org/10.1016/j.cels.2018.03.001)',
                         location='form')
post_parser.add_argument(WINDOW_PARAM, type=int, default=10000,
                         help='Window search size in base pairs used in snp search',
                         location='form')


@api.doc('Runs NEtwork boosted gwas')
@ns.route('/', strict_slashes=False)
class TaskBasedRestApp(Resource):
    @api.doc('Runs Network Boosted GWAS',
             responses={
                 202: 'The task was successfully submitted to the service. Visit the URL'
                      ' specified in **Location** field in HEADERS to status and results',
                 500: 'Internal server error'
             })
    @api.header(LOCATION, 'URL endpoint to poll for result of task for '
                          'successful call')
    @api.expect(post_parser)
    def post(self):
        """
        Submits NAGA task for processing

        """
        app.logger.debug("Post snpanalyzer received")

        try:
            params = post_parser.parse_args(request, strict=True)
            params['remoteip'] = request.remote_addr

            res = create_task(params)

            resp = flask.make_response()
            resp.headers[LOCATION] = SNP_ANALYZER_NS + '/' + res
            resp.status_code = 202
            return resp
        except OSError as e:
            app.logger.exception('Error creating task due to OSError' + str(e))
            abort(500, 'Unable to create task ' + str(e))
        except Exception as ea:
            app.logger.exception('Error creating task due to Exception ' + str(ea))
            abort(500, 'Unable to create task ' + str(ea))


@ns.route('/<string:id>', strict_slashes=False)
class GetTask(Resource):

    @api.doc('Gets status and response of submitted NBGWAS snpanalyzer',
             responses={
                 200: 'Success in asking server, but does not mean'
                      'snpanalyzer has completed. See the json response'
                      'in body for status',
                 410: 'Task not found',
                 500: 'Internal server error'
             })
    def get(self, id):
        """
        Gets result of snpanalyzer if completed

        **{id}** is the id of the snpanalyzer obtained from **Location** field in
        **HEADERS** of **/nbgwas/snpanalyzer POST** endpoint


        The status will be returned in this json format:

        For incomplete/failed jobs

        &nbsp;&nbsp;

        ```Bash
        {
          "status" : "notfound|submitted|processing|error"
        }
        ```

        &nbsp;&nbsp;

        For complete jobs an additional field result is included:

        &nbsp;&nbsp;

        ```Bash
        {
          "status" : "done",
          "result" : { "GENE1": SCORE, "GENE2", SCORE2 }
        }
        ```
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
        Deletes task associated with {id} passed in

        Currently **NOT** implemented and will always return status code
        **503**
        """
        resp = flask.make_response()
        resp.data = 'Currently not implemented'
        resp.status_code = 503
        return resp


@ns.route('/status', strict_slashes=False, doc=False)
class SystemStatus(Resource):

    OK_STATUS = 'ok'
    @api.doc('Gets status',
             responses={
                 200: 'Success',
                 500: 'Internal server error'
             })
    def get(self):
        """
        Gets status of service

        ```Bash
        {
          "status" : "ok|error"
        }
        ```
        """

        resp = jsonify({STATUS_RESULT_KEY: SystemStatus.OK_STATUS})
        resp.status_code = 200
        return resp
