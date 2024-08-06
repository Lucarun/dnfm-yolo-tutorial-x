#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author  : huxiansheng (you@example.org)
# @Date    : 2024/8/6

import time
from typing import Tuple

from device_manager.scrcpy_adb import ScrcpyADB
from data.coordinate.game_coordinate import *
import math
from utils.logger import logger

class HeroControlBase:
    """
    英雄控制基类
    """

    def __init__(self, adb: ScrcpyADB):
        self.adb = adb

    @staticmethod
    def calc_mov_point(angle: float) -> Tuple[int, int]:
        """
        根据角度计算轮盘 x y 坐标
        :param angle:
        :return:
        """
        rx, ry = roulette_wheel
        r = 125

        x = rx + r * math.cos(angle * math.pi / 180)
        y = ry - r * math.sin(angle * math.pi / 180)
        return int(x), int(y)

    def move(self, angle: float, t: float):
        """
        角色移动
        :param angle:
        :param t:
        :return:
        """
        # 计算轮盘x, y坐标
        x, y = self.calc_mov_point(angle)
        logger.info(f"移动到坐标:{x},{y}")
        self.adb.touch_start(x, y)
        time.sleep(t)
        self.adb.touch_end(x, y)

    def _attack(self,x:int, y:int, t: float = 0.01):
        """
        攻击
        :param x:
        :param y:
        :param t:
        :return:
        """
        self.adb.touch_start(x, y)
        time.sleep(t)
        self.adb.touch_end(x, y)

    def normal_attack(self, t: float or int = 1):
        """
        普通攻击
        :return:
        """
        x, y = attack
        self._attack(x, y, t)

    def skill_attack(self,skill_coordinate:Tuple[int,int],t: float or int = 0.1):
        """
        技能攻击
        :param skill_coordinate: 技能坐标
        :param t:
        :return:
        """
        x, y = skill_coordinate
        self._attack(x, y, t)

    def awaken_attack(self,t: float or int = 0.1):
        """
        觉醒技能攻击
        :param t:
        :return:
        """
        x, y = awaken_skill
        self._attack(x, y, t)



if __name__ == '__main__':
    ctl = HeroControlBase(ScrcpyADB())
# ctl.move(180, 3)
# time.sleep(0.3)
# ctl.attack()
# time.sleep(0.3)
# ctl.move(270, 5)
# time.sleep(0.3)
# ctl.attack(3)
