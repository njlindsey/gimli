#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Import/Export for SIP data."""

import codecs
from datetime import  datetime

import numpy as np
import re

import pygimli as pg

def load(fileName, verbose=False, **kwargs):
    """Shortcut to load SIP spectral data.

    Import Data and try to assume the file format.

    Parameters
    ----------
    fileName: str

    Returns
    -------
    freqs, amp, phi : np.array
        Frequencies, amplitudes and phases phi in neg. radiant

    """
    firstLine = None
    with codecs.open(fileName, 'r', encoding='iso-8859-15',
                     errors='replace') as fi:
        firstLine = fi.readline()
        
    f, amp, phi = None, None, None

    fnLow = fileName.lower()

    if 'SIP Fuchs III' in firstLine:
        if verbose:
            pg.info("Reading SIP Fuchs III file")
        f, amp, phi, header = readFuchs3File(fileName, 
                                             verbose=verbose, **kwargs)
        phi *= -np.pi/180.
        # print(header) # not used?
    elif 'SIP-Quad' in firstLine:
        if verbose:
            pg.info("Reading SIP Quad file")
        f, amp, phi, header = readFuchs3File(fileName, 
                                             verbose=verbose, **kwargs)
        phi *= -np.pi/180.
    elif 'SIP-Fuchs' in firstLine:
        if verbose:
            pg.info("Reading SIP Fuchs file")
        f, amp, phi, drhoa, dphi = readRadicSIPFuchs(fileName, 
                                                     verbose=verbose, **kwargs)
        phi *= -np.pi/180.
    elif fnLow.endswith('.txt') or fnLow.endswith('.csv'):
        f, amp, phi = readTXTSpectrum(filename)
        amp *= 1.0 # scale it with k if available
    else:
        raise Exception("Don't know how to read data.")

    return f, amp, phi


def fstring(fri):
    """Format frequency to human-readable (mHz or kHz)."""
    if fri > 1e3:
        fstr = '{:d} kHz'.format(int(np.round(fri/1e3)))
    elif fri < 1.:
        fstr = '{:d} mHz'.format(int(np.round(fri*1e3)))
    elif fri < 10.:
        fstr = '{:3.1f} Hz'.format(fri)
    elif fri < 100.:
        fstr = '{:4.1f} Hz'.format(fri)
    else:
        fstr = '{:d} Hz'.format(int(np.round(fri)))
    return fstr


def readTXTSpectrum(filename):
    """Read spectrum from ZEL device output (txt) data file."""
    fid = open(filename)
    lines = fid.readlines()
    fid.close()
    f, amp, phi = [], [], []
    for line in lines[1:]:
        snums = line.replace(';', ' ').split()
        if len(snums) > 3:
            f.append(float(snums[0]))
            amp.append(float(snums[1]))
            phi.append(-float(snums[3]))
        else:
            break

    return np.asarray(f), np.asarray(amp), np.asarray(phi)


def readFuchs3File(resfile, k=1.0, verbose=False):
    """Read Fuchs III (SIP spectrum) data file.

    Parameters
    ----------
    k : float
        Overwrite internal geometric factor from device.

    """
    activeBlock = ''
    header = {}
    LINE = []
    dataAct = False
    with codecs.open(resfile, 'r', encoding='iso-8859-15', errors='replace') as f:
        for line in f:
            line = line.replace('\r\n', '\n') # correct for carriage return
            if dataAct:
                LINE.append(line)
                if len(line) < 2:
                    f, amp, phi, kIn = [], [], [], []
                    for li in LINE:
                        sline = li.split()
                        if len(sline) > 12:
                            fi = float(sline[11])
                            if np.isfinite(fi):
                                f.append(fi)
                                amp.append(float(sline[12]))
                                phi.append(float(sline[13]))
                                kIn.append(float(sline[9]))

                    if k != 1.0 and verbose is True:
                        pg.info("Geometric value changed to:", k)

                    return np.array(f), np.array(amp)/np.array(kIn) * k, \
                           np.array(phi), header
            elif len(line):
                if line.rfind('Current') >= 0:
                    if dataAct:
                        break
                    else:
                        dataAct = True

                if line[0] == '[':
                    token = line[1:line.rfind(']')].replace(' ', '_')
                    if token[:3] == 'End':
                        header[activeBlock] = np.array(header[activeBlock])
                        activeBlock = ''
                    elif token[:5] == 'Begin':
                        activeBlock = token[6:]
                        header[activeBlock] = []
                    else:
                        value = line[line.rfind(']') + 1:]
                        try:  # direct line information
                            if '.' in value:
                                num = float(value)
                            else:
                                num = int(value)
                            header[token] = num
                        except BaseException as e:
                            # maybe beginning or end of a block
                            #print(e)
                            pass

                else:
                    if activeBlock:
                        nums = np.array(line.split(), dtype=float)
                        header[activeBlock].append(nums)


def readRadicSIPFuchs(filename, readSecond=False, delLast=True):
    """Read SIP-Fuchs Software rev.: 070903

    Read Radic instrument res file containing a single spectrum.

    Please note the apparent resistivity value might be scaled with the
    real geometric factor. Default is 1.0.

    Parameters
    ----------
    filename : string

    readSecond: bool [False]
        Read the first data block[default] or read the second that
        consists in the file.

    delLast : bool [True]
        ??

    Returns
    -------
    fr : array [float]
        Measured frequencies

    rhoa : array [float]
        Measured apparent resistivties

    phi : array [float]
        Measured phases

    drhoa : array [float]
        Measured apparent resistivties error

    phi : array [float]
        Measured phase error
    """
    with codecs.open(resfile, 'r', encoding='iso-8859-15', errors='replace') as f:
    #f = open(filename, 'r')
        line = f.readline()
        fr = []
        rhoa = []
        phi = []
        drhoa = []
        dphi = []
        while True:
            line = f.readline()
            if line.rfind('Freq') > -1:
                break

        if readSecond:
            while True:
                if f.readline().rfind('Freq') > -1:
                    break

        while True:
            line = f.readline()
            b = line.split('\t')
            if len(b) < 5:
                break

            fr.append(float(b[0]))
            rhoa.append(float(b[1]))
            phi.append(-float(b[2]) * np.pi / 180.)
            drhoa.append(float(b[3]))
            dphi.append(float(b[4]) * np.pi / 180.)

        f.close()

    if delLast:
        fr.pop(0)
        rhoa.pop(0)
        phi.pop(0)
        drhoa.pop(0)
        dphi.pop(0)

    return np.array(fr), np.array(rhoa), np.array(phi), np.array(drhoa), np.array(dphi)


def toTime(t, d):
    """ convert time format into timestamp
    11:08:02, 21/02/2019
    """
    tim = [int(_t) for _t in t.split(':')]
    day = [int(_t) for _t in d.split('/')]
    dt = datetime(day[2], day[1], day[0], 
                  hour=tim[0], minute=tim[1], second=tim[2])
   
    return dt.timestamp()
    

def readSIP256file(resfile, verbose=False):
    """Read SIP256 file (RES format) - mostly used for 2d SIP by pybert.sip.

    Read SIP256 file (RES format) - mostly used for 2d SIP by pybert.sip.

    Parameters
    ----------
    filename: str
        *.RES file (SIP256 raw output file)
    verbose: bool
        do some output [False]

    Returns
    -------
        header - dictionary of measuring setup
        DATA - data AB-list of MN-list of matrices with f, amp, phi, dAmp, dPhi
        AB - list of current injection
        RU - list of remote units

    Examples
    --------
        header, DATA, AB, RU = readSIP256file('myfile.res', True)
    """
    activeBlock = ''
    header = {}
    LINE = []
    dataAct = False

    with codecs.open(resfile, 'r', encoding='iso-8859-15', 
                                   errors='replace') as fi:
        content = fi.readlines()

    for line in content:
        if dataAct:
            LINE.append(line)
        elif len(line):
            if line[0] == '[':
                token = line[1:line.rfind(']')].replace(' ', '_')
                # handle early 256D software bug
                if 'FrequencyParameterBegin' in token:
                    token = token.replace('FrequencyParameterBegin',
                                            'Begin_FrequencyParameter')
                if 'FrequencyParameterEnd' in token:
                    token = token.replace('FrequencyParameterEnd',
                                            'End_FrequencyParameter')

                if token.replace(' ', '_') == 'Messdaten_SIP256':
                    dataAct = True
                elif 'Messdaten' in token:
                    # res format changed into SIP256D .. so we are a
                    # little bit more flexible with this.
                    dataAct = True
                elif token[:3] == 'End':
                    header[activeBlock] = np.array(header[activeBlock])
                    activeBlock = ''
                elif token[:5] == 'Begin':
                    activeBlock = token[6:]
                    header[activeBlock] = []
                else:
                    value = line[line.rfind(']') + 1:]
                    try:  # direct line information
                        if '.' in value:
                            num = float(value)
                        else:
                            try:
                                num = int(value)
                            except:
                                num = 0
                                pass
                        header[token] = num
                    except BaseException as e:
                        # maybe beginning or end of a block
                        print(e)
            else:
                if activeBlock:
                    nums = np.array(line.split(), dtype=float)
                    header[activeBlock].append(nums)

    DATA, dReading, dFreq, AB, RU, ru = [], [], [], [], [], []
    tMeas = []
    for line in LINE:
        line = line.replace(' nc ', ' 0 ') # no calibration should 0
        line = line.replace(' c ', ' 1 ') # calibration should 1
        sline = line.split()
        sline = line.rstrip('\r\n').split()
        if line.find('Reading') == 0:
            rdno = int(sline[1])
            if rdno > 0:
                AB.append((int(sline[4]), int(sline[6])))
            if ru:
                RU.append(ru)
                ru = []
            if rdno > 1 and dReading:
                dReading.append(np.array(dFreq))
                DATA.append(dReading)
                pg.verbose('Reading {0}:{1} RUs'.format(rdno-1, len(dReading)))
                dReading, dFreq = [], []
        elif line.find('Remote Unit') == 0:
            ru.append(int(sline[2]))
            if dFreq:
                dReading.append(np.array(dFreq))
                dFreq = []
        elif line.find('Freq') >= 0:
            pass
        elif len(sline) > 1 and rdno > 0:  # some data present
            if re.search('[0-9]-', line):  # missing whitespace before -
                sline = re.sub('[0-9]-', '5 -', line).split()

            for c in range(6): # this is expensive .. do we really need this?
                if len(sline[c]) > 15:  # too long line / missing space
                    if c == 0:
                        part1 = sline[c][:-15]
                        part2 = sline[c][-15:]   # [10:]
                    else:
                        part1 = sline[c][:-10]
                        part2 = sline[c][-10:]   # [11:]
                    sline = sline[:c] + [part1] + [part2] + sline[c + 1:] 
                
                if sline[c].find('c') >= 0:
                    sline[c] = '1.0'
            #Frequency /Hz       RA/Ohmm    PA/�      ERA/%     EPA/�     Cal?     IA/mA     K.-F./m    Gains  Time/h:m:s    Date/d.m.y
            #20000.00000000        0.4609  -6.72598   0.02234   0.01280    1      20.067        1.00      0     11:08:02     21/02/2019
            dFreq.append(np.array(sline[:8]+ [toTime(sline[9], sline[10])], dtype=float))
            
    dReading.append(np.array(dFreq))
    DATA.append(dReading)
    pg.verbose('Reading {0}:{1} RUs'.format(rdno, len(dReading)))
    return header, DATA, AB, RU


if __name__ == "__main__":
    pass
