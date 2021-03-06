#!/usr/bin/env python2
import os
import json
import shutil
import jinja2

from .page import Page
from .hooks import autoindex, sitemap
from .boilerplate import BOILERPLATE_INIT, BOILERPLATE_CONFIG


class Config(dict):
    def __init__(self, path, config={}):
        self.path = path
        dict.update(self, **config)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.update()

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).iteritems():
            self[k] = v
        with open(self.path, 'w') as f:
            f.write(json.dumps(self, sort_keys=True, indent=4, separators=(',', ': ')))


class Noise(object):
    hooks  = []
    routes = {}

    def __init__(self, project, routes=None, hooks=None):
        # set project path
        self.project_path = os.path.join(os.getcwd(), project)
        # set local paths
        self.config_path   = self.__localpath('config.json')
        self.static_path   = self.__localpath('static')
        self.template_path = self.__localpath('template')
        self.build_path    = self.__localpath('build')
        # set routes
        if routes is not None: self.routes = routes
        # set build hooks
        self.hooks = hooks or [autoindex(self), sitemap(self)]
        # initialize template engine
        self.jinja = jinja2.Environment(loader=jinja2.FileSystemLoader(self.template_path))

    def __localpath(self, path):
        # return path relative to project path
        return os.path.join(self.project_path, path)

    def __format_config(self, config):
        # remove trailing forward-slash from base url
        config['base'] = '/' if 'base' not in config else config['base'].rstrip('/') + '/'
        # return modified config
        return config

    def __format_route(self, route):
        # prepend forward-slash if none
        if not route.startswith('/'):
            route = "/" + route
        # append index if trailing forward-slash
        if route.endswith('/'):
            route += "index"
        # append file extension if none
        if len(route.split('/')[-1].split('.')) < 2:
            route += ".html"
        # return formatted route
        return route

    @property
    def config(self):
        # get current config
        config = getattr(self, '_config', None)
        # return current config
        if config is not None:
            return self.__format_config(config)
        # read config file
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = json.load(f)
        # create default config
        else: config = Config(self.config_path, BOILERPLATE_CONFIG)

        # format config
        config = self.__format_config(config)
        # set current config
        self.config = config
        # return current config
        return self.config

    @config.setter
    def config(self, config):
        self._config = config
        config.update()

    def route(self, route):
        def decorator(callback):
            # add route
            self.routes[self.__format_route(route)] = callback
            return callback
        return decorator

    def init(self, config=None):
        # determine project init path
        init_path = self.__localpath('__init__.py')
        # create project directory if needed
        if not os.path.exists(self.project_path):
            os.makedirs(self.project_path)
        # create project init file if needed
        if not os.path.exists(init_path):
            with open(init_path, 'w') as f:
                f.write(BOILERPLATE_INIT)
        # create project config file if needed
        if config or not os.path.exists(self.config_path):
            self.config = Config(self.config_path, config or BOILERPLATE_CONFIG)

    def build(self):
        # clear build directory
        if os.path.exists(self.build_path):
            shutil.rmtree(self.build_path)
        # copy static contents to build
        if os.path.exists(self.static_path):
            shutil.copytree(self.static_path, self.build_path)
        # create build directory
        else: os.mkdir(self.build_path)

        # perform render
        self._render()

    def _prerender(self):
        # iterate build files
        for root, dirs, files in os.walk(self.build_path):
            # iterate build hooks
            for hook in self.hooks:
                # pass data to hook
                hook.prerender(root, dirs, files)

    def _render(self):
        # perform pre-render
        self._prerender()
        # iterate routes
        for route, callback in self.routes.items():
            # callback could be a page
            page = callback
            # create page if needed
            if type(page) is not Page:
                # determine file name
                file_name = route.lstrip('/')
                # determine file path
                file_path = os.path.join(self.build_path, file_name)
                # create page
                page = Page(self, file_path, file_name)
                # perform callback on page
                callback(page)
            # iterate build hooks
            for hook in self.hooks:
                # pass data to hook
                hook.render(route, page)
            # render page
            page.render()
        # perform post-render
        self._postrender()

    def _postrender(self):
        # iterate build files
        for root, dirs, files in os.walk(self.build_path):
            # iterate build hooks
            for hook in self.hooks:
                # pass data to hook
                hook.postrender(root, dirs, files)


def main():
    import argparse
    # argument parser
    parser = argparse.ArgumentParser()
    # parser argument options
    parser.add_argument('action')
    parser.add_argument('project')
    # parse arguments
    args = parser.parse_args()

    # project directory
    project = args.project
    # initialize project
    if args.action == 'init':
        Noise(project).init()
    # import and build project
    elif args.action == 'build':
        __import__(project).app.build()
    # print script usage
    else:
        parser.print_usage()

if __name__ == '__main__':
    main()
