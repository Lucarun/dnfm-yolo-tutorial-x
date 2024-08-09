#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author  : huxiansheng (you@example.org)
# @Date    : 2024/8/7
from typing import Tuple

from device_manager.scrcpy_adb import ScrcpyADB
from game.dengeon.dungeon import DungeonInfo
from game.game_action import GameAction
from utils.logger import logger


class DungeonChallenge:
    """
    副本挑战
    """

    def __init__(self, hero_name: str, dungeon_name: str, adb: ScrcpyADB):
        self.game_action = GameAction(hero_name, adb)
        self.dungeon = DungeonInfo(dungeon_name)
        self.room_coordinate = 0, 0  # 当前地图坐标

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

    def calculate_the_direction_of_the_next_room(self, room_coordinate) -> str:
        """
        计算下一个房间的方向
        :param room_coordinate: 当前房间的坐标
        :return:
        """

    def reward_flip(self):
        """
        通关后翻牌
        :return:
        """
        pass

    def again_challenge(self):
        """
        再次挑战
        :return:
        """
        pass

    def exit_dungeon(self):
        """
        退出副本
        :return:
        """
        pass

    def run(self):
        """
        挑战副本主入口
        :return:
        """
        # 没有 PL 了
        if self.determine_fatigue_value() <= 0:
            return False

        # 移动，选择副本
        self.move_to_dungeon()
        self.select_and_challenge_dungeon()

        # 循环通关路线
        for room_coordinate in self.dungeon.clearance_path:
            kill_monsters = get_items = move = boss_room = False

            if room_coordinate == self.dungeon.szt:
                logger.info("进入狮子头房间")
            elif room_coordinate == self.dungeon.clearance_path[-1]:
                logger.info("进入 Boss 房间")
                boss_room = True
            else:
                logger.info(f"进入房间：{room_coordinate}")
            while 1:
                # 获取当前房间信息，判断房间状态，打怪>捡东西>移动
                map_info = self.game_action.get_map_info()
                if self.game_action.is_exist_monster(map_info):
                    kill_monsters = self.game_action.room_kill_monsters()
                elif self.game_action.is_exist_item(map_info):
                    get_items = self.game_action.get_items()
                else:
                    # 打完 boss 要翻牌子，再次挑战
                    if boss_room:
                        self.reward_flip()
                        if self.determine_fatigue_value() <= 0:
                            logger.info("PL 耗尽")
                            self.exit_dungeon()
                            return True
                        else:
                            self.again_challenge()
                            move = True
                    else:
                        direction = self.calculate_the_direction_of_the_next_room(room_coordinate)
                        move = self.game_action.mov_to_next_room(direction)

                if kill_monsters and get_items and move:
                    break
