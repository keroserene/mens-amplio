#!/usr/bin/env python

import threading
import random
import time
import sys

from flame.sequences import RunSequence, SequentialBursts, SyncedBursts


class ParamThread(threading.Thread):
    """
    Base class for daemon threads that operate on an EffectParameters object
    """
    def __init__(self, params):
        threading.Thread.__init__(self)
        self.daemon = True
        self.params = params


class FlamesThread(ParamThread):
    def __init__(self, params, flame_board,
                 flame_sequences):
        super(FlamesThread,self).__init__(params)
        self.flame_board = flame_board
        self.flame_sequences = flame_sequences
        self.prev_datapoint = None
        self.threshold_attention = 0.0
        self.threshold_meditation = 0.8999
        self.consecutive_crossings_for_fire = 3
        self.consecutive_threshold_crossings = 0
        self.min_time_between_fires = 10 # adjust later
        self.last_fire_time = None

    def run(self):
        while True:
            eeg = self.params.eeg
            if not eeg or eeg == self.prev_datapoint:
                time.sleep(0.5)
                continue
            self.prev_datapoint = eeg
            if (eeg.attention >= self.threshold_attention
                    and eeg.meditation >= self.threshold_meditation):
                self.consecutive_threshold_crossings += 1
                if self.consecutive_threshold_crossings > self.consecutive_crossings_for_fire:
                    if not self.last_fire_time or time.time() - self.last_fire_time > self.min_time_between_fires:
                        print ('*$%!#%*!%#!*%!*%*!#*%!*%*#*%!*#**@!*%\n'
                            '~~~~~~~~~~~ POOOOOOOOOF ~~~~~~~~~~~~~\n'
                            '*$%!#%*!%#!*%!*%*!#*%!*%*#*%!*#**@!*%')
                        RunSequence(self.flame_sequences.selection(), self.flame_board)
                        self.flame_sequences.advance()
                        self.last_fire_time = time.time()
                    self.consecutive_threshold_crossings = 0
            else:
                self.consecutive_threshold_crossings = 0


class HeadsetThread(ParamThread):
    """
    Polls the Mindwave headset. Each time a new point is received, creates an 
    EEGInfo object and stores it in params.
    """ 
    
    class EEGInfo:
        """
        Extracts/stores all the headset info that the effects might actually care about.
        Attention and meditation values are scaled to floats in the range [0,1].
        """
        def __init__(self, point):
            def scale(n):
                return float(n)/100
            self.attention = scale(point.attention)
            self.meditation = scale(point.meditation)
            self.on = point.headsetOnHead()
            self.poor_signal = point.poor_signal

        def __str__(self):
            return "Attn: {0}, Med: {1}, PoorSignal: {2}".format(
                self.attention, self.meditation, self.poor_signal) 

    def __init__(self, params, headset):
        super(HeadsetThread,self).__init__(params)
        self.headset = headset

    def run(self):
        while True: 
            point = self.headset.readDatapoint()
            self.params.eeg = HeadsetThread.EEGInfo(point)
            print self.params.eeg    


class LayerSwapperThread(ParamThread):
    """
    Monitors the headset parameter data and changes the active layers in the renderer
    when the headset is taken on or off, or when headset data values cross a certain 
    threshold [not implemented yet]
    
    Assumes that renderer contains 'on', 'off', and 'transition' playlists.
    """
    
    idleSwitchTime = 10 #how often to swap routines when headset is off - raise this later
    
    def __init__(self, params, renderer):
        ParamThread.__init__(self, params)
        self.renderer = renderer
        self.headsetOn = False
        
        renderer.activePlaylist = 'off'
        
    def run(self):
        lastActive = time.time()
        while True:
            if self.params.eeg and self.params.eeg.on:
                if not self.headsetOn:
                    sys.stderr.write("on!\n")
                    self.headsetOn = True
                    self.renderer.swapPlaylists('on', 'transition')
            else:
                if self.headsetOn:
                    sys.stderr.write("off!\n")
                    self.headsetOn = False
                    self.renderer.swapPlaylists('off')
                    lastActive = time.time()
                if time.time() - lastActive > self.idleSwitchTime:
                    self.renderer.advanceCurrentPlaylist()
                    lastActive = time.time()
                    print "playlist advanced"
            time.sleep(0.05)

