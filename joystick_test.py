#!/usr/bin/env python3
"""Identify joystick axes and buttons without activating motors."""
import argparse
import time
from arm.joystick import Joystick

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--device', default='/dev/input/js0')
    args = p.parse_args(); js = Joystick(args.device)
    try:
        old = None
        while True:
            js.update()
            state = (tuple(sorted((k, round(v, 2)) for k,v in js.axes.items())), tuple(sorted(k for k,v in js.buttons.items() if v)))
            if state != old:
                print('Axes:', dict(state[0]), 'Pressed buttons:', state[1], flush=True); old = state
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        js.close()
