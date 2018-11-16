# -*- coding: utf-8 -*-

"""Top-level package for nbgwas_rest."""

__author__ = """Chris Churas"""
__email__ = 'churas.camera@gmail.com'
__version__ = '0.1.0'

from nbgwas import Nbgwas
from flask import Flask, request, jsonify
from flask_restplus import reqparse, abort, Api, Resource
import pandas as pd
import networkx as nx
import logging
import json
from ndex2 import create_nice_cx_from_server

from nbgwas_rest import bigim
desc = """A REST service for an accessible, fast and customizable network propagation system 
for pathway interpretation of Genome Wide Association Studies (GWAS)
"""
# global api object
app = Flask(__name__, instance_relative_config=True)
api = Api(app, version=str(__version__),
          title='Network Boosted Genome Wide Association Studies (NBGWAS) ',
          description=desc)
app.config.SWAGGER_UI_DOC_EXPANSION = 'list'


def create_gene_level_summary(genes, seeds):
    # Add heat to gene_level_summary

    genes_level_summary = pd.DataFrame([genes], index=['Genes']).T
    genes_level_summary['p-value'] = 1
    genes_level_summary.loc[genes_level_summary['Genes'].isin(seeds), 'p-value'] = 0

    return genes_level_summary


ALPHA_PARAM='alpha'
NETWORK_PARAM='network'
COLUMN_PARAM='column'
SEEDS_PARAM='seeds'
NDEX_PARAM='ndex'

@api.route('/nbgwas', endpoint='nbgwas')
class nbgwasapp(Resource):


    @api.doc('Runs Network Boosted GWAS',
             params={ALPHA_PARAM: 'Alpha parameter to use in random walk '
                                            'with restart model function should be set to values between 0-1',
                     NDEX_PARAM: 'If set, grabs network matching ID from NDEX http://http://www.ndexbio.org/',
                     NETWORK_PARAM: 'If set, loads network from file (TODO explain format)',
                     SEEDS_PARAM: 'Comma list of genes...',
                     COLUMN_PARAM: 'Setting this gets network from bigim?'

    },
        responses={
        200: 'Success'
    })
    def post(self):
        logging.info("Begin!")
        # Setting alpha
        alpha = float(request.values.get(ALPHA_PARAM, 0.5))
        dG = None
        # Getting network
        if NETWORK_PARAM in request.files:
            logging.info("Reading Network File")

            network_file = request.files[NETWORK_PARAM]
            network_df = pd.read_csv(
                network_file.stream,
                sep='\t',
                names=['Gene1', 'Gene2', 'Val']
            )
        elif COLUMN_PARAM in request.values:
            logging.info("Getting file from BigGIM")
            network_df = bigim.get_table_from_biggim(request.values[COLUMN_PARAM], 0.8)
            network_df = network_df.astype(str)

        elif NDEX_PARAM in request.values:
            logging.info("Getting network from NDEx")
            ndex_uuid = request.values[NDEX_PARAM]
            network_niceCx = create_nice_cx_from_server(
                server='public.ndexbio.org',
                uuid=ndex_uuid
            )
            dG = network_niceCx.to_networkx()
            node_name_mapping = {i: j['name'] for i, j in dG.node.items()}

            dG = nx.relabel_nodes(dG, node_name_mapping)

        else:
            return "Query fields are not understood!"

        logging.info("Finished getting network_df")

        # Making networkx object
        if dG is None:
            dG = nx.from_pandas_dataframe(network_df, 'Gene1', 'Gene2')

        logging.info("Finished making network")

        # Parsing seeds
        seeds = request.values[SEEDS_PARAM]
        seeds = seeds.split(',')

        logging.info("Finished converting seeds")

        # Making sure the seeds are in the network
        for i in seeds:
            if i not in dG.nodes():
                seeds.remove(i)
                logging.info(f"{i} not in nodes")

        if len(seeds) == 0:
            logging.info("No seeds left!")
            return "failed"

        gene_level_summary = create_gene_level_summary(dG.nodes(), seeds)

        logging.info("Finished gene level Summary")

        g = Nbgwas(
            gene_level_summary=gene_level_summary,
            gene_col='Genes',
            gene_pval_col='p-value',
            network=dG,
        )

        g.convert_to_heat()
        g.diffuse(method='random_walk', alpha=alpha)

        logging.info("Done!")
        return_json = json.loads(g.heat.iloc[:, -1].to_json())
        return return_json  # + '\n'
