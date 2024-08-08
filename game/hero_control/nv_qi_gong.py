#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author  : huxiansheng (you@example.org)
# @Date    : 2024/8/6
from data.coordinate.game_coordinate import *
from device_manager.scrcpy_adb import ScrcpyADB
from game.hero_control.hero_control_base import HeroControlBase
from utils.logger import logger


class NvQiGong(HeroControlBase):
    """
    女气功
    """

    def __init__(self, adb: ScrcpyADB):
        super().__init__(adb)
        self.buff = buff1
        self.awaken_skill = awaken_skill
        self.attack = attack
        self.room_skill_combo = {
            1: self.skill_combo_1,
            2: self.skill_combo_2,
        }

    def add_buff(self):
        """
        添加buff
        :return:
        """
        x, y = self.buff
        self.adb.touch(x, y)
        pass

    def skill_combo_1(self):
        """
        技能连招1
        :return:
        """
        self.add_buff()
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
