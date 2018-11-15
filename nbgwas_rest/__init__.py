# -*- coding: utf-8 -*-

"""Top-level package for nbgwas_rest."""

__author__ = """Chris Churas"""
__email__ = 'churas.camera@gmail.com'
__version__ = '0.1.0'

from nbgwas import Nbgwas
from flask import Flask, request, jsonify
from flask_restful import reqparse, abort, Api, Resource
import pandas as pd
import networkx as nx
import logging
import json
from ndex2 import create_nice_cx_from_server

from nbgwas_rest import bigim


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    api = Api(app)
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
    api.add_resource(nbgwasapp, '/nbgwas', endpoint='nbgwas')
    return app

def create_gene_level_summary(genes, seeds):
    # Add heat to gene_level_summary

    genes_level_summary = pd.DataFrame([genes], index=['Genes']).T
    genes_level_summary['p-value'] = 1
    genes_level_summary.loc[genes_level_summary['Genes'].isin(seeds), 'p-value'] = 0

    return genes_level_summary


class nbgwasapp(Resource):

    def post(self):

        logging.info("Begin!")

        # Setting alpha
        alpha = float(request.values.get("alpha", 0.5))

        dG = None

        # Getting network
        if "network" in request.files:
            logging.info("Reading Network File")

            network_file = request.files['network']
            network_df = pd.read_csv(
                network_file.stream,
                sep='\t',
                names=['Gene1', 'Gene2', 'Val']
            )
        elif "column" in request.values:
            logging.info("Getting file from BigGIM")
            network_df = bigim.get_table_from_biggim(request.values['column'], 0.8)
            network_df = network_df.astype(str)

        elif "ndex" in request.values:
            logging.info("Getting network from NDEx")
            ndex_uuid = request.values['ndex']
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
        seeds = request.values['seeds']
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
