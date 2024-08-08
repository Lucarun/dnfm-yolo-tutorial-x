import os.path
import random
import sys
from typing import Tuple, List

from utils.yolov5 import YoloV5s
from utils.logger import logger
from device_manager.scrcpy_adb import ScrcpyADB
from hero_control.hero_control import get_hero_control
from utils.path_manager import PathManager
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


def calc_angle(hero_pos: Tuple[int, int], target_pos: Tuple[int, int]) -> float:
    """
    计算英雄和目标的角度
    角度从正 x 轴（向右方向）逆时针计算
    :return:
    """
    dx = target_pos[0] - hero_pos[0]
    dy = target_pos[1] - hero_pos[1]

    # 计算弧度角
    angle_rad = math.atan2(dy, dx)

    # 将弧度转换为角度
    angle_deg = math.degrees(angle_rad)

    # 确保角度在 [0, 360) 范围内
    if angle_deg < 0:
        angle_deg += 360

    return angle_deg


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


def calculate_direction_based_on_angle(angle: int or float):
    """
    根据角度计算方向
    :param angle:
    :return:
    """
    if 0 <= angle <= 360:
        if 0 <= angle <= 90:
            return ["up", "right"]
        elif 90 < angle <= 180:
            return ["up", "left"]
        elif 180 < angle <= 270:
            return ["down", "left"]
        else:
            return ["down", "right"]
    else:
        return None


def find_door_in_direction(doors: List[Tuple[int, int]], direction: str) -> Tuple[int, int]:
    """
    找到符合前进方向的门
    :param doors:
    :param direction:
    :return:
    """
    if direction == 'left':
        return min(doors, key=lambda door: door[0])
    elif direction == 'right':
        return max(doors, key=lambda door: door[0])
    elif direction == 'up':
        return min(doors, key=lambda door: door[1])
    elif direction == 'down':
        return max(doors, key=lambda door: door[1])
    else:
        raise ValueError("Invalid direction")


class GameAction:
    """
    游戏控制
    """
    LABLE_LIST = [line.strip() for line in open(os.path.join(PathManager.MODEL_PATH, "new.txt")).readlines()]

    LABLE_INDEX = {}
    for i, lable in enumerate(LABLE_LIST):
        LABLE_INDEX[i] = lable

    def __init__(self, hero_name: str, adb: ScrcpyADB):
        self.ctrl = get_hero_control(hero_name, adb)
        self.yolo = YoloV5s(num_threads=4, use_gpu=True)
        self.adb = adb
        self.room_index = 0
        self.special_room = False  # 狮子头
        self.boss_room = False  # boss
        self.next_room_direction = "down"  # 下一个房间的方向

    def random_move(self):
        """
        防卡死
        :return:
        """
        logger.info("随机移动一下")
        self.ctrl.move(random.randint(0, 360), 0.5)

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
        self.adb.picture_frame(frame, result)

        lable_list = [line.strip() for line in open(os.path.join(PathManager.MODEL_PATH, "new.txt")).readlines()]
        result_dict = {}
        for lable in lable_list:
            result_dict[lable] = []

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
                    hx, hy = map_info["hero"]["bottom_centers"][0]
                    item_bottom_centers = map_info["equipment"]["bottom_centers"]
                    closest_item = find_nearest_target_to_the_hero((hx, hy), item_bottom_centers)
                    ix, iy = closest_item
                    angle = calc_angle((hx, hy), (ix, iy))
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
            self.ctrl.normal_attack(3)
        else:
            angle = calc_angle((hx, hy), (mx, my))
            self.ctrl.move(angle, 0.2)

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
                if map_info["hero"]["count"] != 1:
                    self.random_move()
                    continue
                else:
                    self._kill_monsters(map_info)

    @staticmethod
    def is_meet_the_conditions_for_mobility(map_info):
        """
        判断是否满足移动条件，如果不满足返回原因
        :return:
        """
        if map_info["Monster"]["count"] or map_info["Monster_ds"]["count"] or map_info["Monster_szt"]["count"] != 0:
            logger.info("怪物未击杀完毕，不满足过图条件")
            return False, "怪物未击杀"
        if map_info["equipment"]["count"] != 0:
            logger.info("存在没检的材料，不满足过图条件")
            return False, "存在没检的材料"
        return True, ""

    def mov_to_next_room(self):
        """
        根据门的位置移动到下一个房间
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
            if map_info["hero"]["count"] == 0:
                logger.info("没有找到英雄")
                self.random_move()
                continue
            else:
                hx, hy = map_info["hero"]["bottom_centers"][0]

            # 判断是否达到移动下一个房间的条件
            conditions, reason = self.is_meet_the_conditions_for_mobility(map_info)
            if not conditions:
                return False, reason

            if map_info["go"]["count"] == 0:
                logger.info("没有找到标记")
                self.random_move()
                continue
            else:
                marks = map_info["go"]["bottom_centers"]

            closest_mark = find_nearest_target_to_the_hero((hx, hy), marks)
            if closest_mark is None:
                continue
            mx, my = closest_mark
            # TODO 这里有 bug，不能直接这样计算坐标，要以 0.0 坐标计算
            angle = calc_angle((hx, hy), (mx, my))
            # 根据箭头方向和下一步前行的方向判断要不要跟着箭头走
            mark_direction = calculate_direction_based_on_angle(angle)
            if self.next_room_direction in mark_direction:
                if not start_move:
                    self.ctrl.touch_roulette_wheel()
                    start_move = True
                else:
                    self.ctrl.swipe_roulette_wheel(angle)
            # 狮子头房间的反向和箭头指引方向不一致，这里要处理一下进入狮子头的房间
            # 获取到门的坐标后进行移动，需要考虑的是可能当前视野内没有获取到狮子头的门，别进错了
            else:
                logger.info("箭头和指引反向不一致，开始找门过图")
                # if map_info["Gate"]["count"] == 0:
                #     logger.info("没有找到门的坐标")
                #     self.random_move()
                #     continue
                # else:
                #     gates = map_info["Gate"]["bottom_centers"]
                # gx, gy = find_door_in_direction(gates, self.next_room_direction)
                # angle = calc_angle((hx, hy), (gx, gy))
                # if not start_move:
                #     self.ctrl.touch_roulette_wheel()
                #     start_move = True
                # else:
                #     self.ctrl.swipe_roulette_wheel(angle)
                self.random_move()
                continue


if __name__ == '__main__':
    action = GameAction('nv_qi_gong', ScrcpyADB())
    # for i in range(5):
    action.mov_to_next_room()
#     # action.get_items()
#     time.sleep(3)
# print(calc_angle((100, 100), (0, 100)))
