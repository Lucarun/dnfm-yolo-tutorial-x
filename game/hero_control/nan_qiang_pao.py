#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author  : huxiansheng (you@example.org)
# @Date    : 2024/8/6

from data.coordinate.game_coordinate import *
from device_manager.scrcpy_adb import ScrcpyADB
from game.hero_control.hero_control_base import HeroControlBase


class NanQiangPao(HeroControlBase):
    """
    男枪炮
    """

    def __init__(self, adb: ScrcpyADB):
        super().__init__(adb)
        self.buff = buff1  # 勇气祝福
        self.awaken_skill = awaken_skill  # 觉醒
        self.attack = attack  # 普通攻击

    def skill_combo_1(self):
        """
        技能连招1
        :return:
        """
        pass

    def skill_combo_2(self):
        """
        技能连招2
        :return:
        """
        pass

    def skill_combo_3(self):
        """
        技能连招3
        :return:
        """
        pass
