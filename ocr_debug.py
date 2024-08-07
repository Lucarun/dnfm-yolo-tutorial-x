import time

import cv2
import numpy as np
from adbutils import adb
import scrcpy
from PIL import Image
from pytesseract import pytesseract
# import matplotlib.pyplot as plt
import subprocess
import os
import easyocr

# 设置 Tesseract 可执行文件路径（Windows 用户需要设置）
pytesseract.tesseract_cmd = r'D:\tesseract_ocr\tesseract.exe'

def capture_screenshot():
    # 使用 scrcpy 截屏
    # devices = adb.device_list()[0]
    # if not devices:
    #     raise Exception("No devices connected")
    # adb.connect("127.0.0.1:5555")
    #
    # screenshot = devices.screenshot()
    #
    # # 将截图保存为图片文件
    # screenshot_path = "screenshot.png"
    # with open(screenshot_path, "wb") as f:
    #     f.write(screenshot)

    return 'saliya.jpg'


def read_text_with_easyocr(image_path):
    # 创建 EasyOCR 读者对象，指定语言
    reader = easyocr.Reader(['ch_sim', 'en'])  # 简体中文和英文
    # 读取图像
    results = reader.readtext(image_path)

    # 打印识别的文本和位置
    for result in results:
        text, bbox = result[1], result[0]
        print(f"Detected text: {text}")
        print(f"Bounding box: {bbox}")

    # 可视化识别结果
    image = cv2.imread(image_path)
    for result in results:
        bbox = result[0]
        for i in range(len(bbox)):
            start_point = tuple(bbox[i])
            end_point = tuple(bbox[(i + 1) % len(bbox)])
            image = cv2.line(image, start_point, end_point, (0, 255, 0), 2)

    # 使用 matplotlib 显示图像
    # plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    # plt.axis('off')
    # plt.show()


def test_ocr(image_path):
    image = cv2.imread(image_path)
    cv2.imshow("Screenshot", image)


    text = pytesseract.image_to_string(image, lang='chi_sim', config='--psm 6')
    time.sleep(111)
    print(text)

def get_text_coordinates1(image_path, target_text):
    # 打开图片
    img = Image.open(image_path)
    data = pytesseract.image_to_data(img, lang='chi_sim', output_type=pytesseract.Output.DICT)

    # 查找特定文字
    for i, word in enumerate(data['text']):
        if word == target_text:
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            center_x = x + w // 2
            center_y = y + h // 2
            return (center_x, center_y)
    return None

def get_text_coordinates2(image_path, target_text):
    # 加载 EAST 文本检测器模型
    net = cv2.dnn.readNet(r'D:\model\frozen_east_text_detection.pb-master\frozen_east_text_detection.pb')

    # 读取图像
    image = cv2.imread(image_path)
    orig = image.copy()
    (H, W) = image.shape[:2]

    # 设置新的宽度和高度，并计算比例
    (newW, newH) = (320, 320)
    rW = W / float(newW)
    rH = H / float(newH)

    # 调整图像大小
    image_resized = cv2.resize(image, (newW, newH))
    (H, W) = image_resized.shape[:2]

    # 创建 blob 并进行前向传播以获取文本块的几何信息和分数
    blob = cv2.dnn.blobFromImage(image_resized, 1.0, (W, H), (123.68, 116.78, 103.94), swapRB=True, crop=False)
    net.setInput(blob)
    (scores, geometry) = net.forward(['feature_fusion/Conv_7/Sigmoid', 'feature_fusion/concat_3'])

    # 解析文本检测器的输出
    (numRows, numCols) = scores.shape[2:4]
    rects = []
    confidences = []

    for y in range(numRows):
        scoresData = scores[0, 0, y]
        xData0 = geometry[0, 0, y]
        xData1 = geometry[0, 1, y]
        xData2 = geometry[0, 2, y]
        xData3 = geometry[0, 3, y]
        anglesData = geometry[0, 4, y]

        for x in range(numCols):
            if scoresData[x] < 0.5:
                continue

            (offsetX, offsetY) = (x * 4.0, y * 4.0)
            angle = anglesData[x]
            cos = np.cos(angle)
            sin = np.sin(angle)
            h = xData0[x] + xData2[x]
            w = xData1[x] + xData3[x]
            endX = int(offsetX + (cos * xData1[x]) + (sin * xData2[x]))
            endY = int(offsetY - (sin * xData1[x]) + (cos * xData2[x]))
            startX = int(endX - w)
            startY = int(endY - h)

            rects.append((startX, startY, endX, endY))
            confidences.append(scoresData[x])

    # 使用非最大值抑制消除冗余框
    boxes = cv2.dnn.NMSBoxes(rects, confidences, 0.5, 0.4)

    # 遍历检测到的文本块并进行 OCR 识别
    for i in range(len(boxes)):
        (startX, startY, endX, endY) = rects[boxes[i]]
        startX = int(startX * rW)
        startY = int(startY * rH)
        endX = int(endX * rW)
        endY = int(endY * rH)

        roi = image[startY:endY, startX:endX]
        text = pytesseract.image_to_string(roi, lang='chi_sim', config='--psm 6')

        if target_text in text:
            center_x = (startX + endX) // 2
            center_y = (startY + endY) // 2
            return (center_x, center_y)

    return None

# 捕获屏幕截图
screenshot_path = capture_screenshot()

# 目标文字
target_text = "32"

read_text_with_easyocr(screenshot_path)
# test_ocr(screenshot_path)

# 获取目标文字的中心坐标
# center_coords = get_text_coordinates1(screenshot_path, target_text)
#
# if center_coords:
#     print(f"文字: {target_text}, 中心坐标: {center_coords}")
# else:
#     print(f"未找到文字: {target_text}")
