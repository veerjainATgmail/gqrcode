#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of GQRCode
#
# Copyright (c) 2012-2019 Lorenzo Carbonell Cerezo <a.k.a. atareao>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import gi
try:
    gi.require_version('GdkPixbuf', '2.0')
    gi.require_version('GLib', '2.0')
except Exception as e:
    print(e)
    exit(1)
from gi.repository import GdkPixbuf
from gi.repository import GLib
import os
from .mylibs import theqrmodule
from .mylibs.draw import image2pixbuf, pixbuf2image
from .gif import get_frames
from PIL import Image
from PIL import ImageSequence
from PIL import ImageEnhance

# Positional parameters
#   words: str
#
# Optional parameters
#   version: int, from 1 to 40
#   level: str, just one of ('L','M','Q','H')
#   picutre: str, a filename of a image
#   colorized: bool
#   constrast: float
#   brightness: float
#   save_name: str, the output filename like 'example.png'
#   save_dir: str, the output directory
#
# See [https://github.com/sylnsfar/qrcode] for more details!


def convert_w2t(image):
    image = image.convert('RGBA')
    newData = []
    for item in image.getdata():
        if item[0] == 255 and item[1] == 255 and item[2] == 255:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
    image.putdata(newData)
    return image


def paste(background, qr):
    newData = []
    for index, item in enumerate(qr.getdata()):
        if item[0] == 0 and item[1] == 0 and item[2] == 0:
            newData.append((0, 0, 0, 0))
        else:
            item = background.getdata()[index]
            newData.append(item)
    background.putdata(newData)
    return background


def get_gif_rate(filename):
    image = Image.open(filename)
    frames = 0
    durations = []
    for frame in ImageSequence.Iterator(image):
        try:
            frames += 1
            durations.append(frame.info['duration']/1000.0)
        except Exception as e:
            print(e)
    if len(durations) == 0:
        return None
    return float(frames)/sum(durations)


def combine_pilimage(ver, qr, filename, colorized, contrast, brightness):
    width, height = qr.size
    layer0 = Image.new('RGBA', qr.size, (0, 0, 0, 0))
    print(filename, type(filename))
    print(Image, type(Image))
    if isinstance(filename, GdkPixbuf.Pixbuf):
        layer1 = pixbuf2image(filename)
    elif isinstance(filename, Image.Image):
        layer1 = filename.convert('RGBA')
    else:
        layer1 = Image.open(filename)
        layer1 = layer1.convert('RGBA')
    layer1 = ImageEnhance.Contrast(layer1).enhance(contrast)
    layer1 = ImageEnhance.Brightness(layer1).enhance(brightness)
    layer1 = layer1.resize((int(width * 0.8), int(height * 0.8)),
                            Image.BICUBIC)
    layer0.paste(layer1, (int(width * 0.1), int(height * 0.1)))
    background = Image.blend(
        layer0, Image.new('RGBA', qr.size, (255, 255, 255, 255)), 0.3)
    background = Image.alpha_composite(background, convert_w2t(qr))

    return background


def create_qr(words, version=1, level='H', picture=None, colorized=False,
              contrast=1.0, brightness=1.0, progreso=None):
    print('----', picture, '----')
    supported_chars = r"0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZabcdefghijklmnñop\
qrstuvwxyz ··,.:;+-*/\~!@#$%^&`'=<>[]()?_{}|"

    # check every parameter
    if not isinstance(words, str) or\
            any(i not in supported_chars for i in words):
        raise ValueError(
            'Wrong words! Make sure the characters are supported!')
    if not isinstance(version, int) or version not in range(1, 41):
        raise ValueError(
            'Wrong version! Please choose a int-type value from 1 to 40!')
    if not isinstance(level, str) or len(level) > 1 or level not in 'LMQH':
        raise ValueError(
            "Wrong level! Please choose a level from {'L','M','Q','H'}!")
    if picture:
        if not isinstance(picture, str) or not os.path.isfile(picture) or\
                picture[-4:] not in ('.jpg', '.png', '.bmp', '.gif'):
            raise ValueError(
                "Wrong picture! Input a filename that exists and be tailed\
 with one of {'.jpg', '.png', '.bmp', '.gif'}!")
        if not isinstance(colorized, bool):
            raise ValueError('Wrong colorized! Input a bool-type value!')
        if not isinstance(contrast, float):
            raise ValueError('Wrong contrast! Input a float-type value!')
        if not isinstance(brightness, float):
            raise ValueError('Wrong brightness! Input a float-type value!')
    try:
        ver, pilimage = theqrmodule.get_qrcode_pilimage(version, level, words)
        if picture and picture[-4:] == '.gif':
            rate = get_gif_rate(picture)
            if rate is None:
                if progreso is not None:
                    GLib.idle_add(progreso.set_max_value, 1)
                qr = combine_pilimage(ver, pilimage, picture, colorized,
                                      contrast, brightness)
                if progreso is not None:
                    GLib.idle_add(progreso.increase)
                    GLib.idle_add(progreso.close)
                return image2pixbuf(qr), None
            frames = get_frames(picture)
            width, height = Image.open(picture).size
            simpleanim = GdkPixbuf.PixbufSimpleAnim.new(width,
                                                        height,
                                                        rate)
            image_frames = []
            if progreso is not None:
                GLib.idle_add(progreso.set_max_value, len(frames))
            for index, frame in enumerate(frames):
                print('Adding frame number: {0}'.format(index))
                image_frame = combine_pilimage(ver, pilimage, frame,
                                                colorized, contrast,
                                                brightness)
                image_frames.append(image_frame)
                simpleanim.add_frame(image2pixbuf(image_frame))
                if progreso is not None:
                    GLib.idle_add(progreso.increase)
            if progreso is not None:
                GLib.idle_add(progreso.close)
            return simpleanim, image_frames
        elif picture:
            if progreso is not None:
                GLib.idle_add(progreso.set_max_value, 1)
            qr = combine_pilimage(ver, pilimage, picture, colorized, contrast,
                                  brightness)
            if progreso is not None:
                GLib.idle_add(progreso.increase)
                GLib.idle_add(progreso.close)
            return image2pixbuf(qr), None
        if progreso is not None:
            GLib.idle_add(progreso.set_max_value, 1)
            GLib.idle_add(progreso.increase)
            GLib.idle_add(progreso.close)
        return image2pixbuf(pilimage), None
    except Exception as e:
        print(e)
