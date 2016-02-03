#!/usr/bin/env python
# -*- encoding: utf-8 -*-

__author__ = 'mac'

import os
import re
import subprocess
import collections


class MOV_Metadata(object):
    def __init__(self):
        super(MOV_Metadata, self).__init__()
        self.header = collections.OrderedDict()

    def __timecodetoframe(self, timecode, fps):
        # print('==== __timecodetoframe  ====')
        ffps = float(fps)
        hh = int(timecode[0:2])
        mm = int(timecode[3:5])
        ss = int(timecode[6:8])
        ff = 0
        if timecode[8:9] == '.':
            ff = int(float(timecode[9:11]) / 100.0 * ffps)
        else:
            ff = int(timecode[9:11])
        # print(ffps, hh, mm, ss, ff)
        framecount = int((hh * 3600 * ffps) + int(mm * 60 * ffps) + int(ss * ffps) + ff)
        # print(framecount)
        return framecount

    def __frametotimecode(self, frame, fps):
        # print('==== __frametotimecode  ====')
        ffps = float(fps)
        fframe = int(frame)
        hh = fframe // int(3600 * ffps)
        fframe = fframe - int(hh * 3600 * ffps)
        mm = fframe // int(60 * ffps)
        fframe = fframe - int(mm * 60 * ffps)
        ss = fframe // ffps
        ff = fframe - ss * ffps
        tcstring = '%02d:%02d:%02d:%02d' % (hh, mm, ss, ff)
        # print(tcstring)
        return tcstring

    def __timecodeadd(self, tc1, tc2, fps):
        # print('==== __timecodeadd  ====')
        frame1 = self.__timecodetoframe(tc1, fps)
        frame2 = self.__timecodetoframe(tc2, fps)
        # print(frame1, frame2)
        frame2 = frame1 + frame2
        return self.__frametotimecode(frame2, fps)

    def metadata(self, path):
        if not os.path.exists('/opt/local/bin/ffmpeg'):
            print('please install ffmpeg')
            return None

        cmd = '/opt/local/bin/ffmpeg -i ' + path.replace(' ', r'\ ')
        message = subprocess.Popen(cmd, stderr=subprocess.PIPE, shell=True).communicate()[1]

        if len(message) > 0:
            self.header['FULL_PATH'] = path
            for index, line in enumerate(message.split(os.linesep)):
                # print(index, line)
                if 'Duration' in line:
                    # print(line.split(',')[0].split(':')[-1].lstrip().rstrip())
                    self.header['duration'] = line.split(',')[0].split(': ')[-1].lstrip().rstrip()
                if 'creation_time' in line:
                    # print(line.split(' : ')[-1].lstrip().rstrip())
                    self.header['creation_date'] = line.split(' : ')[-1].lstrip().rstrip().split(' ')[0]
                    self.header['creation_time'] = line.split(' : ')[-1].lstrip().rstrip().split(' ')[1]
                if 'encoder' in line:
                    # print(line.split(':')[-1].lstrip().rstrip())
                    self.header['encoder'] = line.split(' : ')[-1].lstrip().rstrip()
                if 'Stream' in line and 'Video' in line and 'fps' in line:
                    # print(line.split(',')[4].lstrip().rstrip().split(' ')[0])
                    self.header['fps'] = line.split('fps')[0].lstrip().rstrip().split(',')[-1].lstrip().rstrip()
                    self.header['width'] = line.split(',')[2].lstrip().rstrip().split(' ')[0].split('x')[0]
                    self.header['height'] = line.split(',')[2].lstrip().rstrip().split(' ')[0].split('x')[1]
                if 'reel_name' in line:
                    # print(line.split(':')[-1].lstrip().rstrip())
                    self.header['REEL'] = line.split(' : ')[-1].lstrip().rstrip()
                if 'timecode' in line:
                    # print(line.split(' : ')[-1].lstrip().rstrip())
                    self.header['MASTER_TC'] = line.split(' : ')[-1].lstrip().rstrip()
                    if self.header.has_key('duration') and self.header.has_key('fps'):
                        self.header['END_TC'] = self.__timecodeadd(self.header['MASTER_TC'], self.header['duration'],
                                                                   self.header['fps'])

            return self.header
        else:
            return None

    def csvString(self, sep=','):
        csvstring = ''
        csvstring = sep.join(self.header.keys())
        csvstring += os.linesep
        csvstring += sep.join(map(str, self.header.values()))
        csvstring += os.linesep

        if len(csvstring) > 0:
            return csvstring
        else:
            return None


if __name__ == '__main__':
    testclass = MOV_Metadata()
    mylist = testclass.metadata('/Volumes/work/TEST_Footage/\~Footage/MOV/jzs_v1.mov')
    print(mylist)
    print(testclass.csvString())