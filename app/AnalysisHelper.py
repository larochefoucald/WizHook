from . import config
from typing import NoReturn, AsyncIterable, Callable
from bisect import bisect_left
import time
import logging
import random
import colorsys
import math

def _normalize(pv: float) -> float:
    if pv < 0:
        return 0.
    elif pv > 255:
        return 255.
    else:
        return pv

def _scale_pixel(p):
    return tuple( int(int(_normalize(p[i])) * config.SCALE[i]/255)
            for i in range(len(p)) )

def current_interval_factory(analysis, name):
    if name.startswith('segment') or name.startswith('section'):
        # workaround for API inconsitency
        keys = [x['start'] for x in analysis[name][1:]]
        keys.insert(0, 0)
        key_to_x = {x['start']: x for x in analysis[name][1:]}
        key_to_x[0] = analysis[name][0]
    else:
        keys = [x['start'] for x in analysis[name]]
        key_to_x = {x['start']: x for x in analysis[name]}
    return lambda t: key_to_x[keys[bisect_left(keys, t) - 1]]

def section_scale_factory(analysis, name):
    items = [section[name] for section in analysis['sections']
             if name in section]
    min_ = min(items)
    max_ = max(items)
    return lambda x: (x - min_) / (max_ - min_)

class AnalysisHelper:
    def __init__(self, analysis, led_count=1):
        self.led_count = led_count
        # vary with time
        self.get_current_beat = current_interval_factory(analysis, 'beats')
        self.get_current_bar = current_interval_factory(analysis, 'bars')
        self.get_current_tatum = current_interval_factory(analysis, 'tatums')
        self.get_current_segment = current_interval_factory(analysis, 'segments')
        self.get_current_section = current_interval_factory(analysis, 'sections')

        # vary by section
        self.scale_section_loudness = section_scale_factory(analysis, 'loudness')
        self.scale_section_tempo = section_scale_factory(analysis, 'tempo')
        self.scale_section_key = section_scale_factory(analysis, 'key')

    def get_color_components(self, t):
        beat = self.get_current_beat(t)
        bar = self.get_current_bar(t)
        tatum = self.get_current_tatum(t)
        segment = self.get_current_segment(t)
        section = self.get_current_section(t)

        loudness = self.scale_section_loudness(section.get('loudness', -1))
        tempo = self.scale_section_tempo(section.get('tempo', -1))
        key = self.scale_section_key(section.get('key', -1))

        current_bar = (t - bar['start'] + bar['duration']) / bar['duration']
        current_beat = (t - beat['start'] + beat['duration']) / beat['duration']
        #beat_color = (t - beat['start'] + beat['duration']) / beat['duration']
        #timbre_colors = [p for p in segment['timbre']]
        #pitch_colors = [p for p in segment['pitches']]
        parts = {
                't': 0.2*tempo,
                #'p': 0.1*math.exp(segment['pitches'][0]) -0.1,
                #'bar': -0.2*math.log10(current_bar%1),
                #'beat': -0.1*math.log10(current_beat%1)
                'beat': -0.05*math.log(current_beat%1)
                }
        parts['sum'] = sum(parts.values())
        return parts

    def get_current_colors(self, t):
        parts = self.get_color_components(t)
        h = sum(parts.values())
        parts['result']=h

        rgb = colorsys.hsv_to_rgb(h, 1, 1)
        p = _scale_pixel([255*p for p in rgb])
        colors = [p for _ in range(self.led_count)]
        return  colors
