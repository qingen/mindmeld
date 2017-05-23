"""A module containing various utility functions for Workbench.
These are capabilities that do not have an obvious home within the existing
project structure.
"""

from __future__ import unicode_literals
from builtins import object

from datetime import datetime
from email.utils import parsedate
import logging
import os
import shutil

try:
    from urllib.request import urlretrieve
    from urllib.parse import urljoin
except ImportError:
    from urllib import urlretrieve
    from urlparse import urljoin

import requests

from . import path
from .components import QuestionAnswerer


logger = logging.getLogger(__name__)

BLUEPRINT_S3_URL_BASE = 'https://s3-us-west-2.amazonaws.com/mindmeld/workbench-data/blueprints/'
BLUEPRINT_APP_ARCHIVE = 'app.tar.gz'
BLUEPRINT_KB_ARCHIVE = 'kb.tar.gz'
BLUEPRINTS = {
    'quick_start': {},
    'food_ordering': {}
}


class Blueprint(object):
    """This is a callable class used to set up a blueprint app.

    In S3 the directory structure looks like this:

       - s3://mindmeld/workbench-data/blueprints/
       |-food_ordering
       |  |-app.tar.gz
       |  |-kb.tar.gz
       |-quick_start
          |-app.tar.gz
          |-kb.tar.gz


    Within each blueprint dir `app.tar.gz` contains the workbench application
    data (`app.py`, `domains`, `entities`, etc.) and `kb.tar.gz`

    The blueprint method will check S3 for when the blueprint files were last
    updated and compare that with any files in a local blueprint cache at
    ~/.mmworkbench/blueprints. If the cache is out of date, the updated archive
    is downloaded. The archive is then extracted into a directory named for the
    blueprint.
    """
    def __call__(self, name, app_path=None, es_host=None):
        if name not in BLUEPRINTS:
            raise ValueError('Unknown blueprint name : {!r}'.format(name))
        app_path = self.setup_app(name, app_path)
        self.setup_kb(name, app_path, es_host=es_host)
        return app_path

    @classmethod
    def setup_app(cls, name, app_path=None):
        """Setups up the app folder for the specified blueprint.

        Args:
            name (str): The name of the blueprint

        Raises:
            ValueError: When an unknown blueprint is specified
        """
        if name not in BLUEPRINTS:
            raise ValueError('Unknown blueprint name : {!r}'.format(name))

        app_path = app_path or os.path.join(os.getcwd(), name)
        app_path = os.path.abspath(app_path)

        local_archive = cls._fetch_archive(name, 'app')
        shutil.unpack_archive(local_archive, app_path)
        return app_path

    @classmethod
    def setup_kb(cls, name, app_path=None, es_host=None):
        """Sets up the knowledge base for the specified blueprint.

        Args:
            name (str): The name of the blueprint

        Raises:
            ValueError: When an unknown blueprint is specified
        """
        if name not in BLUEPRINTS:
            raise ValueError('Unknown blueprint name : {!r}'.format(name))

        app_path = app_path or os.path.join(os.getcwd(), name)
        app_path = os.path.abspath(app_path)
        _, app_name = os.path.split(app_path)

        if not es_host:
            try:
                es_host = os.environ['MM_ES_HOST']
            except KeyError:
                raise ValueError('Set the MM_ES_HOST env var or pass in es_host')

        cache_dir = path.get_cached_blueprint_path(name)
        local_archive = cls._fetch_archive(name, 'kb')
        kb_dir = os.path.join(cache_dir, 'kb')
        shutil.unpack_archive(local_archive, kb_dir)

        _, _, index_files = next(os.walk(kb_dir))

        for index in index_files:
            index_name, _ = os.path.splitext(index)
            data_file = os.path.join(kb_dir, index)
            QuestionAnswerer.load_index(app_name, index_name, data_file, es_host)

    @staticmethod
    def _fetch_archive(name, archive_type):
        cache_dir = path.get_cached_blueprint_path(name)
        try:
            os.makedirs(cache_dir)
        except FileExistsError:
            # dir already exists -- no worries
            pass

        filename = {'app': BLUEPRINT_APP_ARCHIVE, 'kb': BLUEPRINT_KB_ARCHIVE}.get(archive_type)
        local_archive = os.path.join(cache_dir, filename)
        blueprint_dir = urljoin(BLUEPRINT_S3_URL_BASE, name + '/')

        remote_archive = urljoin(blueprint_dir, filename)
        req = requests.head(remote_archive)
        remote_modified = datetime(*parsedate(req.headers.get('last-modified'))[:6])
        try:
            local_modified = datetime.fromtimestamp(os.path.getmtime(local_archive))
        except FileNotFoundError:
            local_modified = datetime.min

        if remote_modified < local_modified:
            logger.info('Using cached %r %s archive', name, archive_type)
        else:
            logger.info('Fetching %s archive from %r', archive_type, remote_archive)
            urlretrieve(remote_archive, local_archive)
        return local_archive


blueprint = Blueprint()  # pylint: disable=locally-disabled,invalid-name


def configure_logs(**kwargs):
    """Helper method for easily configuring logs from the python shell.
    Args:
        level (TYPE, optional): A logging level recognized by python's logging module.
    """
    import sys
    level = kwargs.get('level', logging.INFO)
    log_format = kwargs.get('format', '%(message)s')
    logging.basicConfig(stream=sys.stdout, format=log_format)
    package_logger = logging.getLogger(__package__)
    package_logger.setLevel(level)
