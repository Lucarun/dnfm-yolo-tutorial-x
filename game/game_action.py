import random
import sys
from typing import Tuple, List

from utils.yolov5 import YoloV5s
from utils.logger import logger
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


def calc_angle(x1, y1, x2, y2):
    """
    计算两个点之间的角度
    :return:
    """
    angle = 180 - int(math.atan2(y1 - y2, x1 - x2) * 180 / math.pi)
    return angle


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


def calculate_distance(coord1: Tuple[int, int], coord2: Tuple[int, int]) -> float:
    """
    计算两个坐标之间的欧几里得距离
    :param coord1: 第一个坐标 (x, y)
    :param coord2: 第二个坐标 (x, y)
    :return: 距离
    """
    return math.sqrt((coord1[0] - coord2[0]) ** 2 + (coord1[1] - coord2[1]) ** 2)


def find_nearest_target_to_the_hero(hero: Tuple[int, int], target: List[Tuple[int, int]]):
    """
    寻找到距离英雄最近的目标
    :param hero: 英雄的坐标 (x, y)
    :param target: 怪物坐标的列表 [(x1, y1), (x2, y2), ...]
    :return: 距离英雄最近的怪物坐标 (x, y)
    """
    if not target:
        return None

    closest_target = min(target, key=lambda t: calculate_distance(hero, t))
    return closest_target


class GameAction:
    """
    游戏控制
    """
    LABLE_INDEX = {
        0.0: "Hero",
        1.0: "Monster",
        2.0: "npc",
        3.0: "Gate",
        4.0: "Item",
        5.0: "Mark",
        6.0: "Monster_Fake",
        7.0: "Switch"
    }

    def __init__(self, hero_name: str, adb: ScrcpyADB):
        self.ctrl = get_hero_control(hero_name, adb)
        self.yolo = YoloV5s(num_threads=4, use_gpu=True)
        self.adb = adb
        self.room_index = 0
        self.special_room = False  # 狮子头
        self.boss_room = False  # boss

    def random_move(self):
        """
        防卡死
        :return:
        """
        logger.info("随机移动一下")
        self.ctrl.move(random.randint(0, 360), 0.2)

    def get_map_info(self, frame=None, show=False):
        """
        获取当前地图信息
        :return:
        """
        if sys.platform.startswith("win"):
            frame = self.adb.last_screen if frame is None else frame
        else:
            frame = self.adb.frame_queue.get(timeout=1) if frame is None else frame
        result = self.yolo(frame)

        if show:
            for obj in result:
                color = (0, 0, 0)
                if obj.label == 0:
                    color = (255, 255, 0)
                elif obj.label == 1:
                    color = (255, 0, 0)
                elif obj.label == 5:
                    color = (0, 0, 255)
                cv.rectangle(frame, (int(obj.rect.x), int(obj.rect.y)), (int(obj.rect.x + obj.rect.w), int(obj.rect.y + + obj.rect.h)), color, 2)
                cv.imshow('frame', frame)
                cv.waitKey(1)

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
            label = GameAction.LABLE_INDEX.get(detection.label)
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
        logger.info("开始捡材料")
        start_move = False
        while True:
            map_info = self.get_map_info(show=True)
            if map_info["Item"]["count"] == 0:
                logger.info("材料全部捡完")
                self.adb.touch_end(0, 0)
                return True
            else:
                if map_info["Hero"]["count"] != 1:
                    self.random_move()
                    continue
                else:
                    # 循环捡东西
                    hx, hy = map_info["Hero"]["bottom_centers"][0]
                    item_bottom_centers = map_info["Item"]["bottom_centers"]
                    closest_item = find_nearest_target_to_the_hero((hx, hy), item_bottom_centers)
                    ix, iy = closest_item
                    angle = calc_angle(hx, hy, ix, iy)
                    if not start_move:
                        self.ctrl.touch_roulette_wheel()
                        start_move = True
                    else:
                        self.ctrl.swipe_roulette_wheel(angle)

    def _kill_monsters(self, map_info):
        """
        击杀怪物
        :return:
        """
        hx, hy = map_info["Hero"]["bottom_centers"][0]
        monster = map_info["Monster"]["bottom_centers"]

        closest_monster = find_nearest_target_to_the_hero((hx, hy), monster)
        mx, my = closest_monster

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
        logger.info("开始击杀怪物")
        room_skill_combo_status = False
        while True:
            # 使用技能连招
            room_skill_combo = self.ctrl.room_skill_combo.get(self.room_index, None)
            if room_skill_combo and not room_skill_combo_status:
                room_skill_combo()
                room_skill_combo_status = True

            map_info = self.get_map_info(show=True)
            # 没有怪物了就认为当前房间击杀成功了
            if map_info["Monster"]["count"] == 0:
                logger.info("怪物击杀完毕")
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
        start_move = False
        logger.info("开始跑图")
        while True:
            screen = self.ctrl.adb.last_screen
            if screen is None:
                continue

            ada_image = cv.adaptiveThreshold(cv.cvtColor(screen, cv.COLOR_BGR2GRAY), 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY_INV, 13, 3)
            if np.sum(ada_image) == 0:
                logger.info("过图成功")
                self.adb.touch_end(0, 0)
                return True

            map_info = self.get_map_info(screen, show=True)
            if map_info["Hero"]["count"] == 0:
                logger.info("没有找到英雄")
                self.random_move()
                continue
            else:
                hx, hy = map_info["Hero"]["bottom_centers"][0]

            if map_info["Mark"]["count"] == 0:
                logger.info("没有找到标记")
                self.random_move()
                continue
            else:
                marks = map_info["Mark"]["bottom_centers"]

            closest_mark = find_nearest_target_to_the_hero((hx, hy), marks)
            if closest_mark is None:
                continue
            mx, my = closest_mark
            cv.circle(screen, (hx, hy), 5, (0, 255, 0), 5)
            cv.arrowedLine(screen, (hx, hy), (mx, my), (255, 0, 0), 3)
            cv.imshow('screen', screen)
            cv.waitKey(1)
            angle = calc_angle(hx, hy, mx, my)
            if not start_move:
                self.ctrl.touch_roulette_wheel()
                start_move = True
            else:
                self.ctrl.swipe_roulette_wheel(angle)


if __name__ == '__main__':
    action = GameAction('nv_qi_gong', ScrcpyADB())
    for i in range(5):
        action.mov_to_next_room()
        # action.get_items()
        time.sleep(3)
