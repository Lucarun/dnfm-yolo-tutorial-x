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
from utils.logger import logger
from utils.yolov5 import YoloV5s


class ScrcpyADB:
    """
    连接设备，并启动 scrcpy
    """

    def __init__(self):
        devices = adb.device_list()
        if not devices:
            raise Exception("No devices connected")
        adb.connect("127.0.0.1:5555")

        self.client = scrcpy.Client(device=devices[0],max_width=2688,max_fps=15)
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
            try:
                result = self.yolo(frame)
                for obj in result:
                    color = (0, 255, 0)
                    if obj.label == 0:
                        color = (255, 0, 0)
                    elif obj.label == 5:
                        color = (0, 0, 255)

                    cv.rectangle(frame, (int(obj.rect.x), int(obj.rect.y)), (int(obj.rect.x + obj.rect.w), int(obj.rect.y + + obj.rect.h)), color, 2)
                    cv.imshow('frame', frame)
                    cv.waitKey(1)

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

    def get_device_resolution(self):
        """
        获取设备分辨率
        :return:
        """
        width, height = self.d.window_size()
        return width, height

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

    def touch(self, x: int or float, y: int or float):
        """
        :param x:
        :param y:
        :return:
        """
        print(22222)
        self.touch_start(x, y)
        time.sleep(0.01)
        self.touch_end(x, y)


if __name__ == '__main__':
    sadb = ScrcpyADB()
    # print(sadb.get_device_resolution())
    # debug_img = "/Users/admin/project/dnfm-yolo-tutorial/data/debug_img/local_send.png"
    # screenshot = sadb.d.screenshot(format="opencv")
    time.sleep(1)
    sadb.touch(2257, 949)

    # sadb.display_frames()
    time.sleep(222)
