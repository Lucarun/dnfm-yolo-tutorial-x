import os.path
import random
import sys
from typing import Tuple, List

from utils.yolov5 import YoloV5s
from utils.logger import logger
from device_manager.scrcpy_adb import ScrcpyADB
from game.hero_control.hero_control import get_hero_control
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
    # 计算两点之间的水平和垂直距离,这里需要注意的是，手机玩游戏的时候是横屏，所以 X 坐标和 Y 坐标是需要对调的
    delta_y = hero_pos[1] - target_pos[1]
    delta_x = hero_pos[0] - target_pos[0]

    # 计算角度（以正右方向为0度，正上方为90度）
    angle_rad = math.atan2(delta_y, delta_x)
    angle_deg = 180 - int(angle_rad * 180 / math.pi)

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


def get_door_coordinate_by_direction(direction):
    """
    根据方向计算下一个房间的门 lable
    :param direction:
    :return:
    """
    direction_to_direction = {
        "up": "opendoor_u",
        "down": "opendoor_d",
        "left": "opendoor_l",
        "right": "opendoor_r",
    }
    return direction_to_direction.get(direction, "")


class GameAction:
    """
    游戏控制
    """
    LABLE_LIST = [line.strip() for line in open(os.path.join(PathManager.MODEL_PATH, "new.txt")).readlines()]

    LABLE_INDEX = {}
    for i, lable in enumerate(LABLE_LIST):
        LABLE_INDEX[i] = lable

    def __init__(self, hero_name: str, adb: ScrcpyADB):
        self.hero_ctrl = get_hero_control(hero_name, adb)
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
        self.hero_ctrl.move(random.randint(0, 360), 0.5)

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
            itme_list = self.is_exist_item(map_info)
            if not itme_list:
                logger.info("材料全部捡完")
                self.adb.touch_end()
                return True
            else:
                if map_info["hero"]["count"] != 1:
                    self.random_move()
                    continue
                else:
                    # 循环捡东西
                    hx, hy = map_info["hero"]["bottom_centers"][0]
                    closest_item = find_nearest_target_to_the_hero((hx, hy), itme_list)
                    angle = calc_angle((hx, hy), closest_item)
                    if not start_move:
                        self.hero_ctrl.touch_roulette_wheel()
                        start_move = True
                    else:
                        self.hero_ctrl.swipe_roulette_wheel(angle)

    def _kill_monsters(self, hero_pos: Tuple[int, int], monster_pos: List[Tuple[int, int]]):
        """
        击杀怪物
        :return:
        """

        closest_monster = find_nearest_target_to_the_hero(hero_pos, monster_pos)

        if is_within_error_margin(hero_pos, closest_monster):
            self.hero_ctrl.skill_combo_1()
            self.hero_ctrl.normal_attack(3)
        else:
            angle = calc_angle(hero_pos, closest_monster)
            self.hero_ctrl.move(angle, 0.2)

    def room_kill_monsters(self, room_coordinate):
        """
        击杀房间内的怪物
        :param room_coordinate: 当前房间的坐标
        :return:
        """
        # TODO 目前还有两个问题，1：怪物多的时候，视频比较卡，导致画面信息和实际游戏画面不一致，操作变形；2：有时候英雄会把怪物挡住，导致以为怪物击杀完毕，实际还没杀完
        logger.info("开始击杀怪物")
        room_skill_combo_status = False
        while True:
            # 使用技能连招
            room_skill_combo = self.hero_ctrl.room_skill_combo.get(room_coordinate, None)
            if room_skill_combo and not room_skill_combo_status:
                room_skill_combo()
                room_skill_combo_status = True

            map_info = self.get_map_info(show=True)
            monster_list = self.is_exist_monster(map_info)
            if not monster_list:
                logger.info("怪物击杀完毕")
                return True
            else:
                if map_info["hero"]["count"] != 1:
                    self.random_move()
                    continue
                else:
                    hx, hy = map_info["hero"]["bottom_centers"][0]
                    self._kill_monsters((hx, hy), monster_list)

    @staticmethod
    def is_exist_monster(map_info):
        """
        判断房间是否存在怪物,如果存在怪物就把怪物坐标返回去，否则返回空
        :return:
        """
        if map_info["Monster"]["count"] and map_info["Monster_ds"]["count"] and map_info["Monster_szt"]["count"] == 0:
            return []
        else:
            monster = []
            if map_info["Monster"]["count"] > 0:
                monster.extend(map_info["Monster"]["bottom_centers"])
            if map_info["Monster_ds"]["count"] > 0:
                monster.extend(map_info["Monster_ds"]["bottom_centers"])
            if map_info["Monster_szt"]["count"] > 0:
                monster.extend(map_info["Monster_szt"]["bottom_centers"])
            return monster

    @staticmethod
    def is_exist_item(map_info):
        """
        判断房间是否材料
        :return:
        """
        if map_info["equipment"]["count"] == 0:
            return []
        else:
            return map_info["equipment"]["bottom_centers"]

    @staticmethod
    def is_exist_reward(map_info):
        """
        判断是否存在翻牌奖励
        :return:
        """
        if map_info["card"]["count"] == 0:
            return []
        else:
            return map_info["card"]["bottom_centers"]

    def is_allow_move(self, map_info):
        """
        判断是否满足移动条件，如果不满足返回原因
        :return:
        """
        if self.is_exist_monster(map_info):
            logger.info("怪物未击杀完毕，不满足过图条件,结束跑图")
            return False, "怪物未击杀"
        if self.is_exist_item(map_info):
            logger.info("存在没检的材料，不满足过图条件,结束跑图")
            return False, "存在没检的材料"
        return True, ""

    def mov_to_next_room(self, direction=None):
        """
        移动到下一个房间
        :param direction:
        :return:
        """
        # TODO 偶现角色突然就不动了，也没卡死，就是不走了
        start_move = False
        hlx, hly = 0, 0
        logger.info("开始跑图")
        move_count = 0
        kasi = 0
        while True:
            screen = self.hero_ctrl.adb.last_screen
            if screen is None:
                continue

            ada_image = cv.adaptiveThreshold(cv.cvtColor(screen, cv.COLOR_BGR2GRAY), 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY_INV, 13, 3)
            if np.sum(ada_image) == 0:
                logger.info("过图成功")
                self.adb.touch_end()
                return True

            if kasi == 50:
                logger.info("卡死次数超过 50 次，过图失败")
                self.adb.touch_end()
                return False, "过图失败"

            map_info = self.get_map_info(screen, show=True)
            if map_info["hero"]["count"] == 0:
                logger.info("没有找到英雄")
                self.random_move()
                continue
            else:
                hx, hy = map_info["hero"]["bottom_centers"][0]
                if move_count > 10:
                    kasi = is_within_error_margin((hlx, hly), (hx, hy), 50, 50)
                    if kasi:
                        logger.info(f"英雄坐标长时间未变化，应该是卡死了，10 次前坐标：{hlx, hly}，当前坐标{hx, hy}，随机移动一下")
                        self.random_move()
                        kasi += 1
                        continue

            # 判断是否达到移动下一个房间的条件
            conditions, reason = self.is_allow_move(map_info)
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
            angle = calc_angle((hx, hy), (mx, my))
            # 根据箭头方向和下一步前行的方向判断要不要跟着箭头走
            mark_direction = calculate_direction_based_on_angle(angle)
            move_count += 1
            if direction in mark_direction:
                if not start_move:
                    self.hero_ctrl.touch_roulette_wheel()
                    start_move = True
                else:
                    self.hero_ctrl.swipe_roulette_wheel(angle)
            # 狮子头房间的反向和箭头指引方向不一致，这里要处理一下进入狮子头的房间
            # 获取到门的坐标后进行移动，需要考虑的是可能当前视野内没有获取到狮子头的门，别进错了
            else:
                logger.info("箭头和指引反向不一致，开始找门过图")
                lable_name = get_door_coordinate_by_direction(direction)
                if map_info[lable_name]["count"] == 0:
                    logger.info(f"没有找到{direction} 方向门的坐标")
                    self.random_move()
                    continue
                dx, dy = map_info[lable_name]["bottom_centers"][0]
                angle = calc_angle((hx, hy), (dx, dy))
                if not start_move:
                    self.hero_ctrl.touch_roulette_wheel()
                    start_move = True
                else:
                    self.hero_ctrl.swipe_roulette_wheel(angle)
                    continue


if __name__ == '__main__':
    action = GameAction('nv_qi_gong', ScrcpyADB())
    # for i in range(5):
    action.mov_to_next_room("right")
    # action.mov_to_next_room()
    #     # action.get_items()
    #     time.sleep(3)
    # print(calc_angle((472, 1328), (788, 1655)))
