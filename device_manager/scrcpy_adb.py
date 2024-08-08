#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author  : huxiansheng (you@example.org)
# @Date    : 2024/8/5
import queue
import sys
import threading
import time

import scrcpy
from adbutils import adb
import cv2 as cv
from ncnn.utils import Detect_Object

from device_manager.constant import TARGET_COLOUR
from utils.logger import logger
from utils.yolov5 import YoloV5s


class ScrcpyADB:
    """
    连接设备，并启动 scrcpy
    """

    def __init__(self):
        devices = adb.device_list()[0]
        if not devices:
            raise Exception("No devices connected")
        adb.connect("127.0.0.1:5555")

        self.client = scrcpy.Client(device=devices, max_width=2688, max_fps=15)
        self.client.add_listener(scrcpy.EVENT_FRAME, self.on_frame)
        self.client.start(threaded=True)

        self.last_screen = None
        self.yolo = self.init_yolov5()

        self.frame_queue = queue.Queue()
        self.stop_event = threading.Event()

    @staticmethod
    def init_yolov5():
        """
        初始化 yolo v5
        :return:
        """
        return YoloV5s(num_threads=4, use_gpu=True)

    def on_frame(self, frame: cv.Mat):
        """
        把当前帧添加到队列里面
        """
        if frame is not None:
            self.last_screen = frame
            # mac 系统需要把帧添加到队列
            if sys.platform.startswith('darwin'):
                self.frame_queue.put(frame)
            else:
                try:
                    result = self.yolo(frame)
                    self.picture_frame(frame, result)
                except Exception as e:
                    logger.error(e)

    def display_frames(self):
        """
        渲染帧
        :return:
        """
        # mac 系统需要把帧添加到队列
        if sys.platform.startswith('darwin'):
            while not self.stop_event.is_set():
                try:
                    frame = self.frame_queue.get(timeout=1)
                    if frame is not None:
                        cv.imshow('frame', frame)
                        cv.waitKey(1)
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(e)

    def picture_frame(self,frame: cv.Mat, objs: [Detect_Object]):
        """
        在 cv 中画出目标框，并显示标签名称和置信度
        :return:
        """
        font = cv.FONT_HERSHEY_SIMPLEX  # 字体样式
        font_scale = 1  # 字体大小
        thickness = 3  # 文本线条厚

        for obj in objs:
            color = TARGET_COLOUR.get(obj.label)
            cv.rectangle(frame, (int(obj.rect.x), int(obj.rect.y)), (int(obj.rect.x + obj.rect.w), int(obj.rect.y + + obj.rect.h)), color, 2)

            # 构造显示的标签文本
            label_text = f"{self.yolo.class_names[int(obj.label)]}:{obj.prob:.2f}"

            # 计算文本位置
            text_size, _ = cv.getTextSize(label_text, font, font_scale, thickness)
            text_x = int(obj.rect.x)
            text_y = int(obj.rect.y - 5)  # 将文本放置在矩形框上方

            # 如果文本超出边界，则将其放置在矩形框下方
            if text_y < 0:
                text_y = int(obj.rect.y + obj.rect.h + 5)

            # 绘制标签文本
            cv.putText(frame, label_text, (text_x, text_y), font, font_scale, color, thickness=thickness)

        cv.imshow('frame', frame)
        cv.waitKey(1)

    def touch_start(self, x: int or float, y: int or float):
        """
        触摸屏幕
        :param x:横坐标
        :param y:纵坐标
        :return:
        """
        logger.info(f"touch start {x},{y}")
        self.client.control.touch(int(x), int(y), scrcpy.ACTION_DOWN)

    def touch_move(self, x: int or float, y: int or float):
        """
        触摸拖动
        :param x: 横坐标
        :param y: 纵坐标
        :return:
        """
        self.client.control.touch(int(x), int(y), scrcpy.ACTION_MOVE)

    def touch_end(self, x: int or float, y: int or float):
        """
        释放触摸
        :param x:
        :param y:
        :return:
        """
        self.client.control.touch(int(x), int(y), scrcpy.ACTION_UP)

    def touch(self, x: int or float, y: int or float, t: int or float = 0.5):
        """
        :param x:
        :param y:
        :param t:
        :return:
        """
        self.touch_start(x, y)
        time.sleep(t)
        self.touch_end(x, y)

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, t: int or float = 0.5):
        """
        实现屏幕拖动（滑动手势）
        :param start_x: 起始点的 x 坐标
        :param start_y: 起始点的 y 坐标
        :param end_x: 终点的 x 坐标
        :param end_y: 终点的 y 坐标
        :param t: 持续时间，默认 0.5 秒
        """
        self.touch_start(start_x, start_y)
        time.sleep(0.2)
        self.touch_move(end_x, end_y)
        time.sleep(t)
        self.touch_end(end_x, end_y)


if __name__ == '__main__':
    sadb = ScrcpyADB()
    # print(sadb.get_device_resolution())
    # debug_img = "/Users/admin/project/dnfm-yolo-tutorial/data/debug_img/local_send.png"
    # screenshot = sadb.d.screenshot(format="opencv")
    time.sleep(1)
    sadb.touch(2257, 949)

    # sadb.display_frames()
    time.sleep(222)
