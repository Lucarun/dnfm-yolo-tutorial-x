#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author  : huxiansheng (you@example.org)
# @Date    : 2024/8/7
from device_manager.scrcpy_adb import ScrcpyADB
from game.dungeon import Dungeon
from game.game_action import GameAction


class DungeonChallenge:
    """
    副本挑战
    """

    def __init__(self, hero_name: str, dungeon_name: str, adb: ScrcpyADB):
        self.game_action = GameAction(hero_name, adb)
        self.dungeon = Dungeon(dungeon_name)
        self.room_coordinate = 0

    def move_to_dungeon(self, dungeon_name: str):
        """
        移动到副本门口
        :return:
        """
        pass

    def select_and_challenge_dungeon(self, dungeon_name: str):
        """
        选择并挑战副本
        :return:
        """
        pass

    def determine_fatigue_value(self) -> int:
        """
        检测当前角色的疲劳值
        :return:
        """
        pass

    def run(self):
        """
        挑战副本主入口
        :return:
        """
        if self.determine_fatigue_value() <= 0:
            return False
        self.move_to_dungeon()
        self.select_and_challenge_dungeon()
        self.game_action.room_kill_monsters()
