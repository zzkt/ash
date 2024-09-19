#!/usr/bin/env python

# File name: k2-misc.py
# Description: MIDI->OSC bridge for Allen & Heath XONE:K2 controller
# Author: nik gaffney <nik@fo.am>
# Created: 2024-09-10
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import mido
import mido.backends.rtmidi
from oscpy.client import OSCClient


def parse_arguments():
    parser = argparse.ArgumentParser(
        prog='k2osc',
        description='MIDI->OSC bridge for Allen & Heath XONE:K2 controller')
    parser.add_argument("--host", metavar='OSC-host', required=False,
                        help='hostname or address of OSC destination',
                        dest='osc_host', default='127.0.0.1')
    parser.add_argument("--port", metavar='OSC-port', required=False,
                        help='port for OSC messages',
                        dest='osc_port', default=5111)
    parser.add_argument("--midi", metavar='MIDI-port',
                        required=False,  help='port name of MIDI device',
                        dest='midi_port', default='XONE:K2')
    parser.add_argument("-v", metavar='verbose',
                        required=False, dest='verbose')
    parser.add_argument("-q", metavar='quiet',
                        required=False, dest='quiet')
    args = parser.parse_args()
    return args


# XONE:K2 controller mapping

# valid types of controllers
#    rp - rotary pots from 0-127
#    re - rotary encoders (inc/dec)
#    fader - linear faders 0-127
#    button - pressed/released (MIDI notes)
CONTROLLERS = ["rp", "re", "fader", "button"]

# controller types and corresponding MIDI control_id
rotary_encoder_channels = [0, 1, 2, 3, 20, 21]
rotary_potentiometer_channels = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
fader_channels = [16, 17, 18, 19]


# map MIDI control_id to controller number
def normalise_control_id(id):
    id_map = [1, 2, 3, 4, 1,
              2, 3, 4, 5, 6,
              7, 8, 9, 10, 11,
              12, 1, 2, 3, 4,
              5, 6, 0, 0, 0,]
    return id_map[id]


# map MIDI note to button number (NOTE: no latching layers or LEDs yet)
def normalise_button_id(id):
    id_map = {
        # upper block
        48: 1, 49: 2, 50: 3, 51: 4,
        44: 5, 45: 6, 46: 7, 47: 8,
        40: 9, 41: 10, 42: 11, 43: 12,
        # lower block
        36: "A", 37: "B", 38: "C", 39: "D",
        32: "E", 33: "F", 34: "G", 35: "H",
        28: "I", 29: "J", 30: "K", 31: "L",
        24: "M", 25: "N", 26: "O", 27: "P",
        # square buttons
        12: "LAYER", 15: "EXIT"}
    return id_map[id]


# predicates for mapped controllers
def is_rp(id):
    return id in rotary_potentiometer_channels


def is_re(id):
    return id in rotary_encoder_channels


def is_fader(id):
    return id in fader_channels


def is_button(note):
    return True


# MIDI in OSC out
def parse_midi_message(msg):
    msg_type = msg.type
    print(f"\nrecv message of type '{msg_type}': {msg}")
    if msg_type == 'control_change':
        control_id, value = msg.control, msg.value
        id = normalise_control_id(control_id)
        if is_rp(control_id):
            mutaliate("rp", id, value)
        elif is_re(control_id):
            mutaliate("re", id, "inc" if (value == 1) else "dec")
        elif is_fader(control_id):
            mutaliate("fader", id, value)
    if msg_type in ['note_on', 'note_off']:
        note = msg.note
        if is_button(note):
            id = normalise_button_id(note)
            mutaliate("button", id,
                      "pressed" if (msg_type == 'note_on') else "released")
        elif is_re(note):
            print("increase resolution of encoder when pressed...")
    # print(f"note: {note}")
    print(f"unrecognised: {msg}")


# OSC interslonk
#  see also -> https://github.com/kivy/oscpy

def osc_setup(address="127.0.0.1", port=5111):
    osc = OSCClient(address, port)
    print(f"OSC client active. Sending to {address} on port {port}")
    return osc


# send some OSC messages etc+
def mutaliate(control, control_id, value=""):
    global osc
    # print(f"mutaliate: {control}, {control_id}, {arg}, {value}")
    if control in CONTROLLERS:
        path = f"/xone/k2/{control}/{control_id}"
        print(f"osc: {path} {value}")
        osc.send_message(path, value)
    return True


def looper():
    loop = 0
    while True:
        loop += 1
    return True


# setup MIDI ports
def midi_setup(label):
    mido.open_input(label, callback=parse_midi_message)
    port = mido.open_output(label)
    return port


def main():
    global osc, midi
    args = parse_arguments()
    osc = osc_setup(args.osc_host, args.osc_port)
    midi = midi_setup(args.midi_port)
    # event loop
    looper()


if __name__ == '__main__':
    main()
