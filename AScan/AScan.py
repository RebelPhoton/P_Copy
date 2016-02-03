#!/usr/bin/env python
# -*- encoding: utf-8 -*-
__author__ = 'andyguo'

from collections import *
import os
import re
import logging
from Arri_Metadata import *
from EXR_Metadata import *
from R3D_Metadata import *
from MOV_Metadata import *

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')


class AScan(object):
    def __init__(self):
        super(AScan, self).__init__()
        self.digitRegex = re.compile(r'.*(?:\D|^)(\d{3,})')
        self.sequencelist = []
        self.allmetadata = False

    def _extractNumbers(self, filename, pattern='#'):
        if filename.lower().endswith(('.mov', '.mp4', '.mxf')):
            return {'filename': filename,
                    'index': -999}

        m = self.digitRegex.match(filename)
        if m:
            repalcedtext = pattern * len(m.group(m.lastindex))
            return {'filename': os.path.normpath(repalcedtext.join(filename.rsplit(m.group(m.lastindex), 1))),
                    'index': int(m.group(m.lastindex))}
        else:
            return {'filename': os.path.normpath(filename),
                    'index': -999}

    def _filterFiles(self, filename):
        if self.typeFilter:
            return not filename.startswith('.') and filename.lower().endswith(self.typeFilter)
        else:
            return not filename.startswith('.')

    def _findMissing(self, indices):
        if sum(indices) * 2 == (indices[0] + indices[-1]) * len(indices):
            return []
        else:
            tempset = set(indices)
            return [missing for missing in range(indices[0], indices[-1] + 1) if missing not in tempset]

    def _getMetadata(self, path, framerange, allframe=False):
        if allframe:
            pass
        else:
            firstpath = self.restoreFilename(path, framerange[0])
            lastpath = self.restoreFilename(path, framerange[-1])
            _tempdict = {}

            # process exr clips
            if lastpath.lower().endswith('.exr'):
                metadata = EXR_Metadata()
                mymetadata = metadata.metadata(firstpath)
                _tempdict['Reel'] = ''
                if mymetadata.has_key('timeCode'):
                    _tempdict['startTimeCode'] = mymetadata['timeCode']
                else:
                    _tempdict['startTimeCode'] = '-1:-1:-1:-1'
                mymetadata = metadata.metadata(lastpath)
                if mymetadata.has_key('timeCode'):
                    _tempdict['endTimeCode'] = mymetadata['timeCode']
                else:
                    _tempdict['endTimeCode'] = '-1:-1:-1:-1'
                return _tempdict

            # process ari clips
            if lastpath.lower().endswith('.ari'):
                metadata = Arri_Metadata()
                mymetadata = metadata.metadata(firstpath)
                _tempdict['Reel'] = mymetadata['Reel']
                _tempdict['startTimeCode'] = mymetadata['Master_TC']
                mymetadata = metadata.metadata(lastpath)
                _tempdict['endTimeCode'] = mymetadata['Master_TC']
                return _tempdict

            # process R3D clips
            if lastpath.lower().endswith('.r3d'):
                metadata = R3D_Metadata()
                mymetadata = metadata.metadata(firstpath)
                _tempdict['Reel'] = mymetadata['AltReelID']
                _tempdict['startTimeCode'] = mymetadata['Abs TC']
                _tempdict['endTimeCode'] = mymetadata['End Abs TC']
                return _tempdict

            # process mov clips
            if lastpath.lower().endswith(('.mov', '.mp4')):
                metadata = MOV_Metadata()
                mymetadata = metadata.metadata(firstpath)
                if mymetadata.has_key('REEL'):
                    _tempdict['Reel'] = mymetadata['REEL']
                else:
                    _tempdict['Reel'] = ''
                if mymetadata.has_key('MASTER_TC'):
                    _tempdict['startTimeCode'] = mymetadata['MASTER_TC']
                else:
                    _tempdict['startTimeCode'] = '-1:-1:-1:-1'
                if mymetadata.has_key('END_TC'):
                    _tempdict['endTimeCode'] = mymetadata['END_TC']
                else:
                    _tempdict['endTimeCode'] = '-1:-1:-1:-1'
                return _tempdict

        return None

    def _scanRecursion(self, folderpath, checkMissing, stereo, typeFilter, metadata):
        for root, subfolder, files in os.walk(folderpath):
            self.typeFilter = typeFilter
            filterfiles = filter(self._filterFiles, files)

            if len(filterfiles) == 0:
                continue

            filterfiles.sort()
            filterfiles = map(self._extractNumbers, filterfiles)
            # logging.debug(filterfiles)

            clips = defaultdict(list)
            for index, item in enumerate(filterfiles):
                clips[item['filename']].append(item['index'])
            logging.debug(clips)

            for clip, indices in clips.items():
                self.sequencelist.append({'filename': os.path.normpath(os.path.join(root, clip)),
                                          'frames': indices,
                                          'missing': self._findMissing(indices)})
                if metadata:
                    metadict = self._getMetadata(os.path.join(root, clip), indices, allframe=self.allmetadata)
                    if metadict:
                        self.sequencelist[-1]['Reel'] = metadict['Reel']
                        self.sequencelist[-1]['startTimeCode'] = metadict['startTimeCode']
                        self.sequencelist[-1]['endTimeCode'] = metadict['endTimeCode']

        logging.info(self.sequencelist)

    def _scanNoRecursion(self, folderpath, checkMissing, stereo, typeFilter, metadata):
        files = [x for x in os.listdir(folderpath) if os.path.isfile(os.path.join(folderpath, x))]
        logging.debug(files)

        self.typeFilter = typeFilter
        filterfiles = filter(self._filterFiles, files)

        if len(filterfiles) == 0:
            return

        filterfiles.sort()
        filterfiles = map(self._extractNumbers, filterfiles)
        # logging.debug(filterfiles)

        clips = defaultdict(list)
        for index, item in enumerate(filterfiles):
            clips[item['filename']].append(item['index'])
        logging.debug(clips)

        for clip, indices in clips.items():
            self.sequencelist.append({'filename': os.path.normpath(os.path.join(folderpath, clip)),
                                      'frames': indices,
                                      'missing': self._findMissing(indices)})
            if metadata:
                metadict = self._getMetadata(os.path.join(folderpath, clip), indices)
                if metadict:
                    self.sequencelist[-1]['Reel'] = metadict['Reel']
                    self.sequencelist[-1]['startTimeCode'] = metadict['startTimeCode']
                    self.sequencelist[-1]['endTimeCode'] = metadict['endTimeCode']

        logging.info(self.sequencelist)

    # method for scanning contents of the folder
    def scanFolder(self, folderpath, recursion=True, checkMissing=True, stereo=False, typeFilter=None, metadata=False):

        self.typeFilter = typeFilter
        self.sequencelist = []
        myfolder = folderpath
        isfile = False
        # check if folderpath availavle?
        if not os.path.exists(myfolder):
            logging.error('the folder path is not exist or not a folder')
            return None

        if os.path.isfile(myfolder):
            myfolder = os.path.dirname(myfolder)
            isfile = True

        # scan folder with recursion mode
        if recursion == True:
            self._scanRecursion(myfolder, checkMissing, stereo, typeFilter, metadata)
        else:
            self._scanNoRecursion(myfolder, checkMissing, stereo, typeFilter, metadata)

        if isfile:
            filepattern = self._extractNumbers(folderpath)['filename']
            for index, item in enumerate(self.sequencelist):
                if filepattern == item['filename']:
                    return self.sequencelist[index]

        return self.sequencelist

    # give the total frame number in sequencelist
    def total(self):
        return sum([len(x['frames']) for x in self.sequencelist])

    # change a file path to a pattern path
    def patternFilename(self, filename, pattern='#'):
        patternname = self._extractNumbers(filename, pattern)
        return (patternname['filename'], patternname['index'])

    # change the pattern path to a real file name
    def restoreFilename(self, filename, index, pattern='#'):
        rr = re.compile(r'.*?({0}+)'.format(pattern))
        match = rr.match(filename)

        if match:
            indexstring = '%0{0}d'.format(len(match.group(match.lastindex))) % index
            return indexstring.join(filename.rsplit(match.group(match.lastindex), 1))
        else:
            return filename

    # rename old clip to new names
    def renameFileName(self, oldfilename, oldrange, newfilename, newstartindex, pattern='#'):
        newindex = newstartindex
        for index in oldrange:
            oldtemp = self.restoreFilename(oldfilename, index, pattern)
            newtemp = self.restoreFilename(newfilename, newindex, pattern)
            newindex += 1
            logging.info(oldtemp)
            logging.info(newtemp)

            try:
                os.rename(oldtemp, newtemp)
            except:
                logging.error(('error rename in ', oldtemp, newtemp))

    # print result for human reading
    def humanFormat(self, mode='all'):
        humanstring = ''
        if len(self.sequencelist) == 0:
            return '==== Empty List ====\n'

        for index, item in enumerate(self.sequencelist):
            humanstring += '%05d\t' % (index + 1)
            humanstring += item['filename']
            humanstring += '\t'
            if item.has_key('Reel'):
                humanstring += '%s\t' % item['Reel']
            if item.has_key('startTimeCode'):
                humanstring += '[%s - %s]\t' % (item['startTimeCode'], item['endTimeCode'])
            humanstring += '[%d]>[%d - %d]\t' % (len(item['frames']), item['frames'][0], item['frames'][-1])
            humanstring += '[%d]>%s\n' % (len(item['missing']), item['missing'])
        return humanstring

    def csvString(self, sep=','):
        csvstring = sep.join(
            ['index', 'filename', 'frames', 'duration', 'Reel', 'startTimeCode', 'endTimeCode', 'missing'])
        for index, item in enumerate(self.sequencelist):
            csvstring += os.linesep
            reel = ''
            starttc = ''
            endtc = ''
            if item.has_key('Reel'):
                reel = item['Reel']
                starttc = item['startTimeCode']
                endtc = item['endTimeCode']

            csvstring += ','.join(['%04d' % index,
                                   item['filename'], str(item['frames']).replace(',', ' '),
                                   str(len(item['frames'])), reel, starttc, endtc,
                                   str(item['missing']).replace(',', ' ')])

        if len(csvstring) > 0:
            return csvstring
        else:
            return None


if __name__ == '__main__':
    testclass = AScan()
    testclass.allmetadata = True
    # mylist = testclass.scanFolder('/Volumes/work/TEST_Footage/IOTOVFX_WORKFLOW/To_VFX/20150915', typeFilter=('.exr', '.dpx'), recursion=True, metadata=True)
    # mylist = testclass.scanFolder(r'/Volumes/work/TEST_Footage/~Footage/A003C028_140924_R6QB', recursion=False, metadata=False)
    mylist = testclass.scanFolder(
        r'/Volumes/work/TEST_Footage/~Footage/A003C028_140924_R6QB/A003C028_140924_R6QB.0403757.ari', recursion=False,
        metadata=False)
    # mylist = testclass.scanFolder('/Users/mac/Desktop/', recursion=False)
    # print mylist
    # testclass.renameFileName(mylist[0]['filename'], mylist[0]['frames'],
    #                          '/Volumes/work/TEST_Footage/IOTOVFX_WORKFLOW/To_VFX/20150915/TST0010/1_B027C024_150201_R6QX/2048x1152/TST_####.exr', 1001)
    print(mylist)
    # print(testclass.restoreFilename('/Users/andyguo/Desktop/#####.zip', 102))
    # print(testclass.patternFilename('/Users/andyguo/Desktop/1234567.zip', pattern='#'))
