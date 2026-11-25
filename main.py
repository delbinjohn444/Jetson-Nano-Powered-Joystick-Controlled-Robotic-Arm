#!/usr/bin/env python3
"""Jetson Nano powered joystick controlled robotic arm."""
import argparse
import time
import sys
import signal
from arm.controller import load_config, Controller
from arm.joystick import Joystick
from arm.output import DryRun, PCA9685


def interrupt(signum, frame):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config.example.json')
    parser.add_argument('--device', help='Override joystick device')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--hardware', action='store_true', help='Explicitly enable PCA9685 output')
    group.add_argument('--demo', action='store_true', help='Synthetic input; no joystick or hardware')
    args = parser.parse_args()
    js = output = None
    try:
        cfg = load_config(args.config)
        if args.hardware and not cfg['hardware_calibrated']:
            raise ValueError('Hardware locked: complete calibration and set hardware_calibrated true')
        output = PCA9685(cfg) if args.hardware else DryRun()
        ctl = Controller(cfg, output)
        print('Jetson Nano Powered Joystick Controlled Robotic Arm')
        print('[MODE]', 'PCA9685 HARDWARE' if args.hardware else 'DRY RUN (no motor outputs)')
        if args.demo:
            settings = cfg['joystick']; dm = settings['deadman_button']; stop = settings['stop_button']
            axes = {j['axis']: 0.0 for j in cfg['joints'].values()}
            buttons = {dm: False, stop: False}
            ctl.step(axes, buttons, set(), set(), 0.04)
            buttons[dm] = True; ctl.step(axes, buttons, {dm}, set(), 0.04)
            axes[next(iter(axes))] = 1.0
            for _ in range(25): ctl.step(axes, buttons, set(), set(), 0.04)
            print('[DEMO]', ctl.status, ctl.angles)
            buttons[dm] = False; ctl.step(axes, buttons, set(), {dm}, 0.04)
            print('[DEMO]', ctl.status)
            return 0
        js = Joystick(args.device or cfg['joystick']['device'])
        print('[INFO] Joystick opened. Release enable button, center mapped axes, then press enable.')
        last = time.monotonic(); last_print = 0.0; period = 1/cfg['loop_hz']
        while True:
            now = time.monotonic(); js.update()
            ctl.step(js.axes, js.buttons, js.pressed, js.released, now-last)
            last = now
            if now-last_print >= 0.5 or ctl.stopped:
                print('[STATUS]', ctl.status, '|', ' '.join('{}={:.1f}'.format(k,v) for k,v in ctl.angles.items()), flush=True)
                last_print = now
            if ctl.stopped:
                break
            time.sleep(max(0, period-(time.monotonic()-now)))
        return 0
    except KeyboardInterrupt:
        print('\n[STOP] User interrupted; no further position commands.')
        return 0
    except (OSError, ValueError, KeyError, TypeError, ImportError, RuntimeError) as exc:
        print('[ERROR]', exc, file=sys.stderr)
        return 1
    finally:
        if js: js.close()
        if output: output.close()
        if args.hardware and output:
            print('[CAUTION] Last PWM may persist. Support arm and use physical cutoff if needed.')

if __name__ == '__main__':
    signal.signal(signal.SIGTERM, interrupt)
    sys.exit(main())
