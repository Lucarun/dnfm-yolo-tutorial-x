#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author  : huxiansheng (you@example.org)
# @Date    : 2024/8/2
import os


class PathManager:
    """
    路劲管理
    """
    ROOT_OATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace('\\', '/')

    PROJECT_NAME = ROOT_OATH.split('/')[-1]

    LOG_PATH = ROOT_OATH + '/logs/'
