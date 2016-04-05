#!/usr/bin/env python
# -*- encoding: utf-8 -*-

__author__ = 'andyguo'

import multiprocessing as mp
import time
import xxhash
import AScan.AScan as ascan
import os
import sys

BLOCKSIZE = 1024 ** 2


class exitcode(object):
    pass


class myclass(object):
    def __init__(self):
        super(myclass, self).__init__()
        self._queue = mp.Queue()
        self.whitecolor = '\033[0;37;40m'
        self.redcolor = '\033[1;31;40m'
        self.greencolor = '\033[1;32;40m'
        self.yellowcolor = '\033[1;33;40m'
        self.resetcolor = '\033[0m'
        self.failfiles = []
        self.logstring = ''

    def _digestAndWrite(self, myqueue, topath):
        digest = xxhash.xxh64()
        try:
            os.makedirs(os.path.dirname(topath))
        except:
            pass
        finally:
            with open(topath, 'w') as f:
                while True:
                    item = myqueue.get()

                    if isinstance(item, exitcode):
                        myqueue.put(digest.hexdigest())
                        sys.stdout.write(self.greencolor + '[COPY PASS]'.rjust(16))
                        sys.stdout.flush()
                        break

                    digest.update(item)
                    f.write(item)

    def _digestAndRead(self, filepath):
        readdigest = xxhash.xxh64()
        with open(filepath, 'r') as f:
            for item in iter((lambda: f.read(BLOCKSIZE)), ''):
                readdigest.update(item)

        return readdigest.hexdigest()

    def _copy(self, frompath, topath, checksum=True, overwrite=False):
        sys.stdout.write(self.whitecolor + frompath)
        sys.stdout.flush()
        self.logstring += frompath
        self.logstring += ','

        if os.path.exists(topath) and not overwrite:
            print(self.yellowcolor + '[COPY SKIP]'.rjust(16))
            self.failfiles.append(frompath)
            self.logstring += '------------\n'
        else:
            digestprocessing = mp.Process(target=self._digestAndWrite, args=(self._queue, topath))
            digestprocessing.start()

            with open(frompath, 'r') as f:
                for item in iter((lambda: f.read(BLOCKSIZE)), ''):
                    self._queue.put(item)

            self._queue.put(exitcode())
            digestprocessing.join()
            result = self._queue.get()
            self.logstring += result
            digestprocessing.terminate()

            if checksum:
                destdigest = self._digestAndRead(topath)
                if destdigest == result:
                    print self.greencolor + '[CHECK PASS]'.rjust(16)
                else:
                    self.failfiles.append(topath)
                    print self.redcolor + '[CHECK FAIL]'.rjust(16)
            else:
                print self.yellowcolor + '[CHECK SKIP]'.rjust(25)

            self.logstring += '\n'

    def copyfiles(self, frompath, topath, checksum=True, overwrite=False, csv=False):
        begintime = time.time()
        self.failfiles = []
        self.logstring = ''
        localcopy = self._copy
        # scanner = ascan.AScan()
        # copyfiles = scanner.scanFolder(frompath)

        for root, sub, files in os.walk(frompath):
            for singlefile in sorted([os.path.join(root, myfile) for myfile in files]):
                tofile = os.path.normpath(
                    os.path.join(topath, os.path.split(frompath)[-1]) + singlefile.replace(frompath, ''))
                # print(tofile)
                localcopy(singlefile, tofile, checksum, overwrite)

        print self.resetcolor + '\n==============================\ncopy time: %s' % (time.time() - begintime)
        print self.redcolor + 'error files: %s\n%s' % (len(self.failfiles), '\n'.join(self.failfiles))
        print self.resetcolor

        if csv:
            with open(os.path.join(topath, 'xxhash.csv'), 'w') as f:
                f.write(self.logstring)
                print self.resetcolor + 'log file: %s' % (os.path.join(topath, 'xxhash.csv'))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('''readme:
        copy files with xxhash check and write csv log file with it.
    usage:
        P_Copy.py [-c] [-o] [-w] [source folder] [target folder]
    param:
        -c\tcheck file (using xxhash)
        -o\toverwrite exist file
        -w\twrite xxhash log file
        [source folder]\tfolder needs to be copied (recursive scan)
        [target folder]\tcopied location''')
        sys.exit(0)

    sourcefolder = sys.argv[-2]
    destfolder = sys.argv[-1]

    checkflag = False
    if '-c' in sys.argv:
        checkflag = True

    overwriteflag = False
    if '-o' in sys.argv:
        overwriteflag = True

    csvflag = False
    if '-w' in sys.argv:
        csvflag = True

    testclass = myclass()
    testclass.copyfiles(sourcefolder, destfolder, checksum=checkflag, overwrite=overwriteflag, csv=csvflag)
