#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author  : huxiansheng (you@example.org)
# @Date    : 2024/8/6
import time

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
        self.buff1 = buff1
        self.buff2 = buff2
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
        self.adb.touch(buff1)
        time.sleep(0.5)
        self.adb.touch(buff2)

    def skill_combo_1(self):
        """
        技能连招1
        :return:
        """
        self.add_buff()
        self.quick_move("right_down", 0.2)
        self.skill_attack(skill4, 1)
        self.combination_skill_attack([skill2, skill3])

    def skill_combo_2(self):
        """
        技能连招2
        :return:
        """
        self.quick_move("right_down", 0.4)
        self.combination_skill_attack([skill5, skill7])

    def skill_combo_3(self):
        """
        技能连招3
        :return:
        """
        self.quick_move("down", 0.2)
        self.skill_attack(skill4, 1)
        self.combination_skill_attack([skill2, skill3])

    def skill_combo_4(self):
        """
        技能连招3
        :return:
        """
        self.quick_move("right", 0.5)
        self.skill_attack(skill4, 1)
        self.combination_skill_attack([skill2, skill3])
