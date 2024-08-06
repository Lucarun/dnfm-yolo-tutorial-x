import random
from typing import Tuple

from utils.yolov5 import YoloV5s
from utils.logger import logger
from game_control import GameControl
from device_manager.scrcpy_adb import ScrcpyADB
from hero_control.hero_control import get_hero_control
import time
import cv2 as cv
from ncnn.utils.objects import Detect_Object
import math
import numpy as np


def get_detect_obj_bottom(obj: Detect_Object) -> Tuple[int, int]:
    """
    获取检测对象的底部坐标
    :param obj:
    :return:
    """
    return int(obj.rect.x + obj.rect.w / 2), int(obj.rect.y + obj.rect.h)


def distance_detect_object(a: Detect_Object, b: Detect_Object):
    return math.sqrt((a.rect.x - b.rect.x) ** 2 + (a.rect.y - b.rect.y) ** 2)


def calc_angle(x1, y1, x2, y2):
    """
    计算两个点之间的角度
    :return:
    """
    angle = math.atan2(y1 - y2, x1 - x2)
    return 180 - int(angle * 180 / math.pi)


def is_within_error_margin(coord1: Tuple[int, int], coord2: Tuple[int, int], x_error_margin: int = 100, y_error_margin: int = 50) -> bool:
    """
    检查两个坐标点之间的误差是否在指定范围内。

    :param coord1: 第一个坐标点 (x1, y1)
    :param coord2: 第二个坐标点 (x2, y2)
    :param x_error_margin: x 坐标的误差范围
    :param y_error_margin: y 坐标的误差范围
    :return: 如果误差在范围内返回 True，否则返回 False
    """
    x1, y1 = coord1
    x2, y2 = coord2

    x_error = abs(x1 - x2)
    y_error = abs(y1 - y2)

    return x_error <= x_error_margin and y_error <= y_error_margin


class GameAction:
    """
    游戏控制
    """

    def __init__(self, hero_name: str, adb: ScrcpyADB):
        self.ctrl = get_hero_control(hero_name, adb)
        self.yolo = YoloV5s(num_threads=4, use_gpu=True)
        self.adb = adb
        self.room_index = 1
        self.special_room = False  # 狮子头
        self.boss_room = False  # boss

    def random_move(self):
        """
        防卡死
        :return:
        """
        pass

    def get_map_info(self):
        """
        获取当前地图信息
        :return:
        """
        result = self.yolo(self.adb.last_screen)

        result_dict = {
            "Hero": [],
            "Monster": [],
            "npc": [],
            "Gate": [],
            "Item": [],
            "Mark": [],
            "Monster_Fake": [],
            "Switch": []
        }

        for detection in result:
            label = detection.label
            if label in result_dict:
                result_dict[label].append(detection)

        final_result = {}
        for label, objects in result_dict.items():
            count = len(objects)
            bottom_centers = [get_detect_obj_bottom(obj) for obj in objects]
            final_result[label] = {
                "count": count,
                "objects": objects,
                "bottom_centers": bottom_centers
            }

        return final_result

    def get_items(self):
        """
        捡材料
        :return:
        """
        while True:
            logger.info("开始捡材料")
            map_info = self.get_map_info()
            if map_info["Item"]["count"] == 0:
                return True
            else:
                if map_info["Hero"]["count"] != 1:
                    self.random_move()
                    continue
                else:
                    # 循环捡东西
                    hx, hy = map_info["Hero"]["bottom_centers"][0]
                    item_bottom_centers = map_info["Item"]["bottom_centers"]
                    for ix, iy in item_bottom_centers:
                        self.ctrl.move(calc_angle(hx, hy, ix, iy), 0.2)

    def _kill_monsters(self, map_info):
        """
        击杀怪物
        :return:
        """
        hx, hy = map_info["Hero"]["bottom_centers"][0]
        mx, my = map_info["Monster"]["bottom_centers"][0]

        if is_within_error_margin((hx, hy), (mx, my)):
            self.ctrl.skill_combo_1()
            self.ctrl.normal_attack()
        else:
            self.ctrl.move(calc_angle(hx, hy, mx, my), 0.2)

    def room_kill_monsters(self):
        """
        击杀房间内的怪物
        :return:
        """
        room_skill_combo_status = False
        while True:
            # 使用技能连招
            room_skill_combo = self.ctrl.room_skill_combo.get(self.room_index, None)
            if room_skill_combo and not room_skill_combo_status:
                room_skill_combo()
                room_skill_combo_status = True

            map_info = self.get_map_info()
            # 没有怪物了就认为当前房间击杀成功了
            if map_info["Monster"]["count"] == 0:
                return True
            else:
                if map_info["Hero"]["count"] != 1:
                    self.random_move()
                    continue
                else:
                    self._kill_monsters(map_info)

    def mov_to_next_room(self):
        """
        移动到下一个房间
        :return:
        """
        mov_start = False
        logger.info("开始跑图")
        while True:
            time.sleep(0.1)
            screen = self.ctrl.adb.last_screen
            if screen is None:
                continue

            ada_image = cv.adaptiveThreshold(cv.cvtColor(screen, cv.COLOR_BGR2GRAY), 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY_INV, 13, 3)
            cv.imshow('ada_image', ada_image)
            cv.waitKey(1)
            if np.sum(ada_image) == 0:
                logger.info("过图成功")
                self.adb.touch_end(0, 0)
                return

            result = self.yolo(screen)
            for obj in result:
                color = (0, 255, 0)
                if obj.label == 1:
                    color = (255, 0, 0)
                elif obj.label == 5:
                    color = (0, 0, 255)
                cv.rectangle(screen, (int(obj.rect.x), int(obj.rect.y)), (int(obj.rect.x + obj.rect.w), int(obj.rect.y + + obj.rect.h)), color, 2)

            hero = [x for x in result if x.label == 0.0]
            if len(hero) == 0:
                logger.info("没有找到英雄")
                self.random_move()
                hero = None
                continue
            else:
                hero = hero[0]
                hx, hy = get_detect_obj_bottom(hero)
                cv.circle(screen, (hx, hy), 5, (0, 0, 125), 5)

            arrow = [x for x in result if x.label == 5]
            if len(arrow) == 0:
                continue
            min_distance_arrow = min(arrow, key=lambda a: distance_detect_object(hero, a))

            ax, ay = get_detect_obj_bottom(min_distance_arrow)
            cv.circle(screen, (hx, hy), 5, (0, 255, 0), 5)
            cv.arrowedLine(screen, (hx, hy), (ax, ay), (255, 0, 0), 3)
            angle = calc_angle(hx, hy, ax, ay)
            sx, sy = self.ctrl.calc_mov_point(angle)
            logger.info(f"angle:{angle},sx:{sx},sy:{sy}")

            if not mov_start:
                self.adb.touch_start(sx, sy)
                mov_start = True
            else:
                self.adb.touch_move(sx, sy)

            cv.imshow('screen', screen)
            cv.waitKey(1)


if __name__ == '__main__':
    action = GameAction('hong_yan',ScrcpyADB())
    while True:
        action.mov_to_next_room()
        time.sleep(3)
