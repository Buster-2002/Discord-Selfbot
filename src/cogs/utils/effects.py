# -*- coding: utf-8 -*-
import colorsys
import warnings
from io import BytesIO
from itertools import cycle
from math import sin
from pathlib import Path
from random import random, randrange
from textwrap import fill, wrap
from typing import Tuple

import cv2
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
from discord import Colour, File
from glitch_this import ImageGlitcher
from PIL import (Image, ImageChops, ImageDraw, ImageEnhance, ImageFont,
                 ImageOps, ImageSequence)
from polaroid import Image as p_Image

from .gif import save_transparent_gif
from .enums import AIDataType

warnings.filterwarnings('ignore')
BEBASNEUE = str(Path('data/assets/fonts/BebasNeue.ttf'))
SOURCESANS = str(Path('data/assets/fonts/SourceSans.ttf'))
CONSOLAS = str(Path('data/assets/fonts/Consolas.ttf'))
BOMB = str(Path('data/assets/gifs/bomb.gif'))
BONK1 = str(Path('data/assets/images/bonk_0.png'))
BONK2 = str(Path('data/assets/images/bonk_1.png'))


def _from_bytes(
    im_bytes: bytes,
    resize: bool = False,
    *,
    mode: str = 'RGBA'
) -> Image:
    try:
        im = Image.open(BytesIO(im_bytes), mode)
    except ValueError:
        im = Image.open(BytesIO(im_bytes))
    if resize:
        if any(dimension > 256 for dimension in im.size):
            return im.resize((256, 256), Image.ANTIALIAS)
    return im


def draw_bounding_boxes(
    data: dict,
    im_bytes: bytes,
    confidence: float,
    data_type: AIDataType
) -> File:
    data = data['output']
    if data_type is AIDataType.content_moderation:
        get_data = lambda d: d['detections']
        get_confidence = lambda d: float(d['confidence'])
        get_label = lambda d: d['name']
    elif data_type is AIDataType.densecap:
        get_data = lambda d: d['captions']
        get_confidence = lambda d: round(d['confidence'], 2)
        get_label = lambda d: d['caption']
    elif data_type is AIDataType.demographic_recognition:
        get_data = lambda d: d['faces']
        get_confidence = lambda d: round(sum((d['cultural_appearance_confidence'], d['age_range_confidence'], d['gender_confidence'])) / 3, 2)
        get_label = lambda d: f"{d['cultural_appearance']} {d['gender']} ({'-'.join(map(str, d['age_range']))} y/o)"

    fp = BytesIO()
    fp.write(im_bytes)
    fp.seek(0)
    im = cv2.imdecode(
        np.asarray(
            bytearray(fp.read()),
            dtype=np.uint8
        ),
        cv2.IMREAD_COLOR
    )
    W, H = im.shape[:2]
    items = list(filter(
        lambda item: float(get_confidence(item)) > confidence,
        get_data(data)
    ))
    colours = cycle([Colour.random(seed=i).to_rgb() for i in range(len(items))])
    borderheight, borderwidth = int(0.05 * H) + 10, int(0.05 * W) + 10
    im = cv2.copyMakeBorder(
        im,
        borderwidth,
        0,
        0,
        borderheight,
        cv2.BORDER_CONSTANT,
        value=(0, 0, 0, 0)
    )
    for item in items:
        label = get_label(item)
        x, y, w, h = item['bounding_box']
        y += borderheight
        colour = next(colours)
        im = cv2.rectangle(
            im,
            (x, y),
            (x + w, y + h),
            colour,
            1
        )
        args = [
            im,
            f"{label.capitalize()} ({get_confidence(item) * 100:.1f}%)",
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            max(0.3, min(w, h) / (24 / 0.06)),
            (0, 0, 0),
            2
        ]
        cv2.putText(*args) # First time normal, second time with black border
        args[5], args[6] = colour, 1
        cv2.putText(*args)

    fp = BytesIO(cv2.imencode('.png', im)[1])
    fp.seek(0)
    return File(fp, 'labeled.png')


def piechart(
    title: str,
    data: list,
    backgroundcolour: Colour,
    randomcolours: bool
) -> File:
    labels, sizes = data[::2], data[1::2]
    colours = [str(Colour.random(seed=i)) for i in range(len(labels))] if randomcolours else None
    _, ax = plt.subplots(facecolor=str(backgroundcolour))
    patches, _, _ = ax.pie(
        sizes,
        autopct='%1.1f%%',
        shadow=True,
        colors=colours,
        startangle=90,
        normalize=True,
        wedgeprops={
            'edgecolor': 'black',
            'linewidth': 1,
            'antialiased': True
        }
    )
    plt.legend(
        patches,
        labels,
        loc='best',
        shadow=True,
        facecolor='#4f535c',
        labelcolor='w',
        edgecolor='black'
    )
    ax.set_title(
        title.title(),
        fontsize=24,
        color='w'
    ).set_path_effects([
        path_effects.Stroke(linewidth=2, foreground='black'),
        path_effects.Normal()
    ])
    ax.axis('equal')
    plt.tight_layout()

    fp = BytesIO()
    plt.savefig(fp, format='PNG')
    plt.close()
    fp.seek(0)
    return File(fp, 'piechart.png')


def explode_(im_bytes: bytes) -> File:
    im = _from_bytes(im_bytes)
    png = False
    frames = [
        frame.resize((256, 256)).convert('RGBA')
        for frame in ImageSequence.Iterator(im)
    ]
    if len(frames) == 1:
        png = True

    frame_count = len(frames)
    bomb_frame_count = 0

    for i, frame in enumerate(ImageSequence.Iterator(Image.open(BOMB))):
        if i == 0:
            continue
        frames.append(frame.resize((256, 256)).convert('RGBA'))
        bomb_frame_count += 1

    durations = (
        [600, * ([100] * bomb_frame_count)] if png
        else [im.info.get('duration', 64)] * frame_count + [100] * bomb_frame_count
    )

    fp = BytesIO()
    save_transparent_gif(frames, durations, fp)
    fp.seek(0)
    return File(fp, 'explode.gif')


def shake_(im_bytes: bytes, intensity: int) -> File:
    im = _from_bytes(im_bytes)
    frames = []
    im = im.resize((400, 400), Image.ANTIALIAS)

    for _ in range(20):
        frame = Image.new('RGBA', (600, 600), (0, 0, 0, 0))
        x_offset = 100 + round(intensity * 2 * (random() - 0.5))
        y_offset = 100 + round(intensity * 2 * (random() - 0.5))
        frame.paste(im, (x_offset, y_offset))
        frames.append(frame)

    fp = BytesIO()
    save_transparent_gif(frames, 50, fp)
    fp.seek(0)
    return File(fp, 'shake.gif')


def bounce_(im_bytes: bytes, speed: int) -> File:
    im = _from_bytes(im_bytes, True)
    frames = []

    for i in range(25):
        frame = Image.new('RGBA', (im.width, round(im.height * 1.6)), (0, 0, 0, 0))
        factor = ((0.25 * i) + (-0.01 * i ** 2)) / 2.2
        height_up = round(im.height * factor)
        difference = frame.height - im.height
        y = difference - height_up

        if factor < 0.2:
            height_ratio = 1 - (0.2 - factor)
            new_height = round(im.height * height_ratio)
            new = im.resize((im.width, new_height))
            height_offset = im.height - new_height
            frame.paste(new, (0, y+height_offset), new.convert('RGBA'))
        else:
            frame.paste(im, (0, y), im.convert('RGBA'))

        frames.append(frame)

    fp = BytesIO()
    save_transparent_gif(frames, speed, fp)
    fp.seek(0)
    return File(fp, 'bounce.gif')


def breathe_(im_bytes: bytes, speed: int) -> File:
    im = _from_bytes(im_bytes, True)
    frames = []

    for i in range(31):
        frame = Image.new('RGBA', im.size, (0, 0, 0, 0))
        factor = 0.1 * sin(i / 4.8) + 0.9
        new_size = (
            round(im.size[0] * factor),
            round(im.size[1] * factor)
        )
        resize = im.resize(new_size)
        box = (
            round((im.size[0] - new_size[0]) / 2),
            round((im.size[1] - new_size[1]) / 2)
        )
        frame.paste(resize, box, resize.convert('RGBA'))
        frames.append(frame)

    fp = BytesIO()
    save_transparent_gif(frames, speed, fp)
    fp.seek(0)
    return File(fp, 'breathe.gif')


def spin_(im_bytes: bytes, speed: int) -> File:
    im = _from_bytes(im_bytes, True)
    im = im.convert('RGBA')
    frames = [im.rotate(degree, resample=Image.BICUBIC, expand=0) for degree in range(0, 360, 6)]
    fp = BytesIO()
    save_transparent_gif(frames, speed, fp)
    fp.seek(0)
    return File(fp, 'spin.gif')


def pet_(im_bytes: bytes, intensity: int) -> File:
    im = _from_bytes(im_bytes)
    frames = []
    im = im.convert('RGBA')
    size = im.size
    big = (size[0] * 3, size[1] * 3)
    mask = Image.new("L", big, 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + big, fill=255)
    mask = mask.resize(size, Image.ANTIALIAS)
    mask = ImageChops.darker(mask, im.split()[-1])
    im.putalpha(mask)
    position_mapping = (
        (27, 31, 86, 90),
        (22, 36, 91, 90),
        (18, 41, 95, 90),
        (22, 41, 91, 91),
        (27, 28, 86, 91)
    )
    intensity_mapping = (
        (0, 0, 0, 0),
        (-7, 22, 8, 0),
        (-8, 30, 9, 6),
        (-3, 21, 5, 9),
        (0, 0, 0, 0)
    )
    im = im.convert('RGBA')
    translation_mapping = (0, 20, 34, 21, 0)

    for frame_index in range(5):
        spec = list(position_mapping[frame_index])
        for j, s in enumerate(spec):
            spec[j] = int(s + intensity_mapping[frame_index][j] * intensity)

        hand = Image.open(Path(f'data/assets/images/pet_{frame_index}.png')).convert('RGBA')
        im = im.resize((int((spec[2] - spec[0]) * 1.2), int((spec[3] - spec[1]) * 1.2)), Image.ANTIALIAS).convert('RGBA')
        gif_frame = Image.new('RGBA', (112, 112), (0, 0, 0, 0))
        gif_frame.paste(im, (spec[0], spec[1]), im)
        gif_frame.paste(hand, (0, int(intensity * translation_mapping[frame_index])), hand)
        frames.append(gif_frame.convert('RGBA'))

    fp = BytesIO()
    save_transparent_gif(frames, 64, fp)
    fp.seek(0)
    return File(fp, 'pet.gif')


def stretch_(im_bytes: bytes, speed: int) -> File:
    im = _from_bytes(im_bytes, True)
    frames = []

    for i in range(10, 41, 3):
        factor = i / 10
        width = int(im.size[0] * factor)
        new_size = (width, im.size[1])
        offset = int((width - im.size[0])/2)

        new = im.resize(new_size, Image.ANTIALIAS)
        new = new.crop((offset, 0, new.size[0] - offset, new.size[1]))
        frames.append(new)

    for i in range(39, 10, -2):
        factor = i / 10
        width = int(im.size[0] * factor)
        new_size = (width, im.size[1])
        offset = int((width - im.size[0]) / 2)

        new = im.resize(new_size, Image.ANTIALIAS)
        new = new.crop((offset, 0, new.size[0] - offset, new.size[1]))
        frames.append(new)

    fp = BytesIO()
    save_transparent_gif(frames, speed, fp)
    fp.seek(0)
    return File(fp, 'stretch.gif')


def bonk_(im_bytes: bytes, speed: int) -> File:
    im = _from_bytes(im_bytes).resize((156, 156), Image.ANTIALIAS)
    frames = []
    im = im.convert('RGBA')
    size = im.size
    big = (size[0] * 3, size[1] * 3)
    mask = Image.new("L", big, 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + big, fill=255)
    mask = mask.resize(size, Image.ANTIALIAS)
    mask = ImageChops.darker(mask, im.split()[-1])
    im.putalpha(mask)

    hammer = Image.open(BONK1)
    frame = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    frame.paste(hammer, (0, 0), hammer)
    frame.paste(im, (90, 90), im)
    frames.append(frame)

    hammer = Image.open(BONK2)
    frame = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    frame.paste(hammer, (0, 0), hammer)
    im = im.resize((im.width, 106), Image.ANTIALIAS)
    frame.paste(im, (90, 140), im)
    frames.append(frame)

    fp = BytesIO()
    save_transparent_gif(frames, speed, fp)
    fp.seek(0)
    return File(fp, 'bonk.gif')


def revolve_(im_bytes: bytes, speed: int) -> File:
    im = _from_bytes(im_bytes, True)
    frames = []

    for i in range(10, -1, -1):
        i /= 10
        new_width = max(2, round(im.width * i))
        frame = Image.new('RGBA', im.size, (0, 0, 0, 0))
        offset = round((frame.width-new_width) / 2)
        resize = im.resize((new_width, im.height))
        frame.paste(resize, (offset, 0), resize.convert('RGBA'))
        frames.append(frame)

    for i in range(1, 10):
        i /= 10
        new_width = max(2, round(im.width * i))
        frame = Image.new('RGBA', im.size, (0, 0, 0, 0))
        offset = round((frame.width-new_width) / 2)
        resize = im.resize((new_width, im.height))
        frame.paste(resize, (offset, 0), resize.convert('RGBA'))
        frames.append(ImageOps.mirror(frame))

    for i in range(10, -1, -1):
        i /= 10
        new_width = max(2, round(im.width * i))
        frame = Image.new('RGBA', im.size, (0, 0, 0, 0))
        offset = round((frame.width - new_width) / 2)
        resize = im.resize((new_width, im.height))
        frame.paste(resize, (offset, 0), resize.convert('RGBA'))
        frames.append(ImageOps.mirror(frame))

    for i in range(1, 10):
        i /= 10
        new_width = max(2, round(im.width*i))
        frame = Image.new('RGBA', im.size, (0, 0, 0, 0))
        offset = round((frame.width-new_width) / 2)
        resize = im.resize((new_width, im.height))
        frame.paste(resize, (offset, 0), resize.convert('RGBA'))
        frames.append(frame)

    fp = BytesIO()
    save_transparent_gif(frames, speed, fp)
    fp.seek(0)
    return File(fp, 'revolve.gif')


def rotatehue_(im_bytes: bytes, speed: int) -> File:
    im = _from_bytes(im_bytes, True)

    def shift_hue(arr, hout):
        r, g, b, a = np.rollaxis(arr, axis=-1)
        h, s, v = np.vectorize(colorsys.rgb_to_hsv)(r, g, b)
        h = hout
        r, g, b = np.vectorize(colorsys.hsv_to_rgb)(h, s, v)
        return np.dstack((r, g, b, a))

    def colorize(img, hue):
        img = img.convert('RGBA')
        arr = np.array(np.asarray(img).astype('float'))
        return Image.fromarray(shift_hue(arr, hue / 360.).astype('uint8'), 'RGBA')

    frames = [colorize(im, degree) for degree in range(0, 360, 8)]
    fp = BytesIO()
    save_transparent_gif(frames, speed, fp)
    fp.seek(0)
    return File(fp, 'huerotate.gif')


def glitch_(
    im_bytes: bytes,
    glitchamount: float,
    seed: int,
    glitch_change: float,
    scanlines: bool,
    step: bool,
    colouroffset: bool,
    _cycle: bool
) -> File:
    im = _from_bytes(im_bytes)
    ft = im.format.lower()
    glitcher = ImageGlitcher()
    options = (
        im,
        glitchamount,
        seed,
        glitch_change,
        colouroffset,
        scanlines,
        True,
        _cycle
    )
    duration = 120
    if ft == 'gif':
        frames, duration, _ = glitcher.glitch_gif(*options, step)
    else:
        frames = glitcher.glitch_image(*options, 15, step)
    fp = BytesIO()
    save_transparent_gif(frames, duration, fp)
    fp.seek(0)
    return File(fp, 'glitch.gif')


def typeout_(
    message: str,
    speed: int,
    size: int,
    rgb: bool
) -> File:
    frames = []
    buffer = ''
    font = ImageFont.truetype(SOURCESANS, size)
    colours = cycle([Colour.random(seed=i).to_rgb() for i in range(len(message))])
    message = fill(message[:400], 28)
    textsize = font.getsize_multiline(message, stroke_width=(size // 4))
    frames.append(Image.new('RGBA', textsize))

    for char in message:
        buffer += char
        new = Image.new('RGBA', textsize)
        draw = ImageDraw.Draw(new)
        draw.text((4, 4), buffer, next(colours) if rgb else 'white', font)
        frames.append(new)

    fp = BytesIO()
    durations = [speed] * len(frames)
    durations[-1] = 4000
    save_transparent_gif(frames, durations, fp)
    fp.seek(0)
    return File(fp, 'type.gif')


def caption_(im_bytes: bytes, text: str) -> Tuple[File, str]:
    im = _from_bytes(im_bytes)
    frames = []
    font = ImageFont.truetype(BEBASNEUE, 1)
    ft = im.format.lower()
    W = im.size[0]

    fontsize = 1
    if len(text) < 23:
        while font.getsize(text)[0] < (0.9 * W):
            fontsize += 1
            font = ImageFont.truetype(BEBASNEUE, fontsize)
    else:
        font = ImageFont.truetype(BEBASNEUE, 50)

    width = 1
    lines = wrap(text, width)
    while font.getsize(max(lines, key=len))[0] < (0.9 * W):
        width += 1
        lines = wrap(text, width)
        if width > 50:
            break

    bar_height = int((len(lines) * font.getsize(lines[0])[1])) + 8

    for frame in ImageSequence.Iterator(im):
        frame = frame.convert('RGBA')
        frame = ImageOps.expand(frame, (0, bar_height, 0, 0), 'white')
        draw = ImageDraw.Draw(frame)
        for i, line in enumerate(lines):
            w, h = draw.multiline_textsize(line, font=font)
            draw.text(((W - w) / 2, i * h), line, 'black', font)
        frames.append(frame)

    fp = BytesIO()
    save_transparent_gif(frames, im.info.get('duration', 64), fp)
    fp.seek(0)
    return File(fp, f'caption.{ft}'), ft


def reverse_(im_bytes: bytes) -> File:
    im = _from_bytes(im_bytes)
    frames = []

    for frame in ImageSequence.Iterator(im):
        frames.insert(0, frame.copy())

    fp = BytesIO()
    save_transparent_gif(frames, im.info.get('duration', 64), fp)
    fp.seek(0)
    return File(fp, 'reverse.gif')


def adjustspeed_(im_bytes: bytes, factor: float) -> File:
    im = _from_bytes(im_bytes)
    frames = []
    total_frames, total_delay = 0, 0

    for frame in ImageSequence.Iterator(im):
        try:
            frames.append(frame.convert('RGBA'))
            total_delay += frame.info['duration']
            total_frames += 1
        except KeyError:
            fp = BytesIO()
            frame.save(fp, format='PNG')
            fp.seek(0)
            return fp

    average_delay = total_delay / total_frames
    future_duration = average_delay / factor

    while future_duration < 20:
        try:
            pop_index = randrange(1, len(frames) - 2)
            frames.pop(pop_index)
        except (IndexError, KeyError, ValueError):
            break
        average_delay = total_delay / len(frames)
        future_duration = average_delay / factor

    fp = BytesIO()
    save_transparent_gif(frames, future_duration, fp)
    fp.seek(0)
    return File(fp, 'speed.gif')


def shine_(
    im_bytes: bytes,
    speed: int,
    rgb: tuple
) -> File:
    im = _from_bytes(im_bytes, True)
    frames = []
    width = max(2, int(im.size[0] / 17))
    im = im.convert('RGBA')

    for box in range(0, im.width * 2 + 1, round(im.width / 8)):
        im_clone = im.resize(im.size, Image.ANTIALIAS)
        frame = Image.new('RGBA', im.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)
        draw.line((-4, box + 4, box + 4, -4), rgb, width)
        composite = Image.composite(frame, im_clone, im_clone)
        im_clone.paste(composite, mask=composite)
        frames.append(im_clone)

    frames.append(im)
    fp = BytesIO()
    durations = [speed] * len(frames)
    durations[-1] = 2000
    save_transparent_gif(frames, durations, fp)
    fp.seek(0)
    return File(fp, 'shine.gif')


def fade_(im_bytes: bytes, speed: int) -> File:
    im = _from_bytes(im_bytes, True)
    frames = []
    im = im.convert('RGBA')

    for i in range(21):
        new = Image.new('RGBA', im.size, (0, 0, 0, 0))
        frame = im.copy()
        enhancer = ImageEnhance.Brightness(frame)
        result = enhancer.enhance(1 - i / 20)
        new.alpha_composite(result, (0, 0))
        frames.append(new.convert('RGBA'))

    fp = BytesIO()
    durations = [speed] * len(frames)
    durations[-1] = 2000
    save_transparent_gif(frames, durations, fp)
    fp.seek(0)
    return File(fp, 'fade.gif')


def deepfry_(im_bytes: bytes, intensity: int) -> Tuple[File, str]:
    im = _from_bytes(im_bytes)
    frames = []
    ft = im.format.lower()
    W, H = im.width, im.height

    for frame in ImageSequence.Iterator(im):
        frame = frame.convert('RGB')
        frame = frame.resize((int(W ** 0.75), int(H ** 0.75)), resample=Image.LANCZOS)
        frame = frame.resize((int(W ** 0.88), int(H ** 0.88)), resample=Image.BILINEAR)
        frame = frame.resize((int(W ** 0.9), int(H ** 0.9)), resample=Image.BICUBIC)
        frame = frame.resize((W, H), resample=Image.BICUBIC)
        frame = ImageOps.posterize(frame, intensity // 25)
        r = frame.split()[0]
        r = ImageEnhance.Contrast(r).enhance(2)
        r = ImageEnhance.Brightness(r).enhance(1.5)
        r = ImageOps.colorize(r, (254, 0, 2), (255, 255, 15))
        frame = Image.blend(frame, r, 0.75)
        frame = ImageEnhance.Sharpness(frame).enhance(intensity)
        frames.append(frame.convert('RGB'))

    fp = BytesIO()
    save_transparent_gif(frames, im.info.get('duration', 64), fp)
    fp.seek(0)
    return File(fp, f'deepfry.{ft}'), ft


def ascii_(
    im_bytes: bytes,
    scale: float,
    intensity: float,
    density: float,
    rgb: bool
) -> Tuple[File, str]:
    im = _from_bytes(im_bytes)
    frames = []
    ft = im.format.lower()
    font = ImageFont.truetype(CONSOLAS, 50)
    colours = cycle([Colour.random(seed=i).to_rgb() for i in range(1, im.n_frames)])
    chars = np.array([
        '$', '@', 'B', '%', '8', '&', 'W', 'M', '#', '*', 'o', 'a', 'h',
        'k', 'b', 'd', 'p', 'q', 'w', 'm', 'Z', 'O', '0', 'Q', 'L', 'C',
        'J', 'U', 'Y', 'X', 'z', 'c', 'v', 'u', 'n', 'x', 'r', 'j', 'f',
        't', '/', '\\', '|', '(', ')', '1', '{', '}', '[', ']', '?', '-',
        '_', '+', '~', '<', '>', 'i', '!', 'l', 'I', ';', ':', ',', '\\',
        '^', '`', '\'', '.', ' '
    ], dtype='<U1')

    for frame in ImageSequence.Iterator(im):
        frame = frame.convert('RGBA')
        new_size = (round(im.size[0] * scale * (7 / 4)), round(im.size[1] * scale))
        frame = np.sum(np.asarray(frame.resize(new_size)), axis=2)
        frame -= frame.min()
        frame = (intensity - frame / frame.max()) ** density * (chars.size - 1)
        text = '\n'.join((''.join(r) for r in chars[frame.astype(int)]))
        new = Image.new('RGBA', font.getsize_multiline(text))
        draw = ImageDraw.Draw(new)
        draw.multiline_text((0, 0), text, next(colours) if rgb else 'white', font)
        frames.append(new.convert('RGBA'))

    fp = BytesIO()
    save_transparent_gif(frames, im.info.get('duration', 64), fp)
    fp.seek(0)
    return File(fp, f'ascii.{ft}'), ft


def use_polaroid(im_bytes: bytes, action: str, *args) -> Tuple[File, str]:
    im = _from_bytes(im_bytes)
    frames = []
    ft = im.format.lower()

    for frame in ImageSequence.Iterator(im):
        fp = BytesIO()
        frame.save(fp, 'PNG')
        fp.seek(0)
        frame = p_Image(fp.read())
        if method := getattr(frame, action, None):
            method(*args)
        else:
            frame.filter(action)
        frame = Image.open(BytesIO(frame.save_bytes()))
        frames.append(frame.convert('RGBA'))

    fp = BytesIO()
    save_transparent_gif(frames, im.info.get('duration', 64), fp)
    fp.seek(0)
    return File(fp, f'{action}.{ft}'), ft

