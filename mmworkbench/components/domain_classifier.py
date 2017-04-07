# -*- coding: utf-8 -*-
"""
This module contains the domain classifier component of the Workbench natural language processor.
"""
from __future__ import unicode_literals
from builtins import super

import logging

from ..models import QUERY_EXAMPLE_TYPE, CLASS_LABEL_TYPE

from .classifier import Classifier

logger = logging.getLogger(__name__)


class DomainClassifier(Classifier):
    """A domain classifier is used to determine the target domain for a given query. It is trained
    using all of the labeled queries across all intents for all domains in an application. The
    labels for the training data are the domain names associated with each query.
    """

    DEFAULT_CONFIG = {
        'default_model': 'main',
        'models': {
            'main': {
                'model_type': 'text',
                'model_settings': {
                    'classifier_type': 'logreg',
                },
                'param_selection': {
                    'type': 'k-fold',
                    'k': 10,
                    'grid': {
                        'fit_intercept': [True, False],
                        'C': [10, 100, 1000, 10000, 100000]
                    },
                },
                'features': {
                    'bag-of-words': {
                        'lengths': [1]
                    },
                    'freq': {'bins': 5},
                    'in-gaz': {}
                }
            }
        }
    }

    def _get_model_config(self, config_name, **kwargs):
        """Gets a machine learning model configuration

        Args:
             config_name: Name of the configuration

        Returns:
            ModelConfig: The model configuration corresponding to the provided config name
        """
        kwargs['example_type'] = QUERY_EXAMPLE_TYPE
        kwargs['label_type'] = CLASS_LABEL_TYPE
        return super()._get_model_config(config_name, **kwargs)

    def fit(self, *args, **kwargs):
        """Trains the domain classification model using the provided training queries

        Args:
            model_type (str): The type of machine learning model to use. If omitted, the default
                model type will be used.
            features (dict): Features to extract from each example instance to form the feature
                vector used for model training. If omitted, the default feature set for the model
                type will be used.
            params_grid (dict): The grid of hyper-parameters to search, for finding the optimal
                hyper-parameter settings for the model. If omitted, the default hyper-parameter
                search grid will be used.
            cv (None, optional): Cross-validation settings
            queries (list of ProcessedQuery): The labeled queries to use as training data

        """
        logger.info('Fitting domain classifier')
        super().fit(*args, **kwargs)

    def dump(self, *args, **kwargs):
        """Persists the trained domain classification model to disk.

        Args:
            model_path (str): The location on disk where the model should be stored
        """
        logger.info('Saving domain classifier')
        super().dump(*args, **kwargs)

    def load(self, *args, **kwargs):
        """Loads the trained domain classification model from disk

        Args:
            model_path (str): The location on disk where the model is stored
        """
        logger.info('Loading domain classifier')
        super().load(*args, **kwargs)

    def _get_queries_and_labels(self, queries=None, label_set='train'):
        """Returns a set of queries and their labels based on the label set

        Args:
            queries (list, optional): A list of ProcessedQuery objects, to
                train. If not specified, a label set will be loaded.
            label_set (list, optional): A label set to load. If not specified,
                the default training set will be loaded.
        """
        if not queries:
            query_tree = self._resource_loader.get_labeled_queries(label_set=label_set)
            queries = self._resource_loader.flatten_query_tree(query_tree)
        return list(zip(*[(q.query, q.domain) for q in queries]))