# -*- coding:utf-8 -*-
import os
import json
import mxnet as mx
from mxnet import nd
from mxnet.gluon.data import dataset
import numpy as np

IMAGE_MEAN = nd.array([169.690778, 140.644055, 127.968828]).reshape(1, 1, 3)  # broadcast


class ImageWithHeatMapDataset(dataset.Dataset):
    """
    A dataset for loading images (with masks) stored as `xyz.jpg` and `xyz_mask.png`.

    Parameters
    ----------
    root : str
        Path to root directory.
    transform : callable, default None
        A function that takes data and label and transforms them:
    ::
        transform = lambda data, label: (data.astype(np.float32)/255, label)
    """

    def __init__(self, root, transform=lambda data, label: (
    nd.transpose(data.astype('float32') - IMAGE_MEAN, (2, 0, 1)), label.astype('float32'))):  # 368*368*3 -> 3*368*368
        self.root = root
        self._list_images()
        self._transform = transform
        self._exts = ['.jpg', '.jpeg', '.png']

    def _list_images(self):
        img_list = []
        f_list = os.listdir(self.root)
        for item in f_list:
            if item.endswith('.json') and item.split('.json')[0] + '.jpg' in f_list:
                img_name = item.split('.json')[0] + '.jpg'
                img_list.append(img_name)
        self._image_list = img_list

    def CenterGaussianHeatMap(self, img_height, img_width, c_x, c_y, variance=1):
        gaussian_map = np.zeros((img_height, img_width))  # 图片长宽转成数组 维度
        for x_p in range(img_width):
            for y_p in range(img_height):  # 这里x,y 是从坐标系角度
                dist_sq = (x_p - c_x) * (x_p - c_x) + \
                          (y_p - c_y) * (y_p - c_y)
                exponent = dist_sq / 2.0 / variance / variance
                gaussian_map[y_p, x_p] = np.exp(-exponent)  # 输出 array 形式
        return gaussian_map * 30.0  # 神经网络输入的label

    def __getitem__(self, idx):
        img = mx.image.imread(self.root + self._image_list[idx])
        # img的预处理在transform函数中完成
        js_name = (self._image_list[idx]).split('.jpg')[0] + '.json'
        with open(os.path.join(self.root, js_name)) as js_file:
            js = json.load(js_file)
            pts = np.array(js['hand_pts'])
            pts_ls = list(pts[:, :2])
        height, width, _ = img.shape
        heatmaps = []
        # background = np.zeros((height / 8, width / 8))
        for i, point in enumerate(pts_ls):
            heatmap = self.CenterGaussianHeatMap(height / 8, width / 8, point[0] / 8.0,
                                                 point[1] / 8.0, 1)  # point[0] x轴坐标，1关联的是heatmap热点的半径
            heatmaps.append(heatmap)
        # heatmaps.append(background)
        label = mx.nd.array(heatmaps)
        # label_total = mx.nd.concat(label, label, label, label, label, label, dim=0)
        label_total = mx.nd.concat(label, label, label, dim=0)
        if self._transform is not None:
            return self._transform(img, label_total)
        else:
            return img, label_total

    def __len__(self):
        return len(self._image_list)
