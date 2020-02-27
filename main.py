# -*- coding: UTF-8 -*-
# @date: 2019/5/5 9:32 
# @name: head_standard
# @author：hy_wanghuan@163.com
import sys
import os
import struct
import platform

STANDARD_PATTERN = 'head44'
CHECK_PATTERN = 'check'
SR1628_PATTERN = 'sr1628'
SR8216_PATTERN = 'sr8216'
LINK_PATTERM = 'link'
SOX_PATTERM = 'sox'


def dir_walk(src_path, det_path=None):
    """
    common methods : yield single (src_voice_path,det_voice_path)
    :param src_path: src_path
    :param det_path: det_path can None
    :return: yield (src_voice_path,det_voice_path)
    """
    if os.path.isdir(src_path):
        if det_path and not os.path.isdir(det_path):
            os.makedirs(det_path)
        for name in os.listdir(src_path):
            _src_path = os.path.join(src_path, name)
            _det_path = det_path and os.path.join(det_path, name)
            for src_file, det_file in dir_walk(_src_path, _det_path):
                yield src_file, det_file
    if os.path.isfile(src_path):
        yield src_path, det_path


def generate_voice(det_voice_path, data, data_len, bitdepth=16, samplerate=16000, channel=1):
    """
    common methods : Through the args and data generation new voice
    :param det_voice_path: det_voice_path
    :param data: data
    :param data_len: data_len
    :param bitdepth: bitdepth
    :param samplerate: samplerate
    :param channel: channel
    :return: None
    """
    ChunkID = b'RIFF'  # 4bytes
    ChunkSize = 36 + data_len  # 4bytes
    Format = b'WAVE'  # 4bytes
    Subchunk1ID = b'fmt '  # 4bytes
    Subchunk1Size = 16  # 4bytes PCM is 16
    AudioFormat = 1  # 2bytes 1 is PCM
    NumChannels = channel  # 2bytes
    SampleRate = samplerate  # 4bytes
    ByteRate = int(samplerate * channel * bitdepth / 8)  # 4bytes
    BlockAlign = int(channel * bitdepth / 8)  # 2bytes
    BitsPerSample = bitdepth  # 2bytes.bitdepth
    Subchunk2ID = b'data'  # 4bytes
    Subchunk2Size = data_len  # 4bytes = NumSamples * NumChannels * BitsPerSample/8
    with open(det_voice_path, 'wb') as det_file:
        det_file.seek(0, 0)
        det_file.write(struct.pack('4s', ChunkID))
        det_file.write(struct.pack('i', ChunkSize))
        det_file.write(struct.pack('4s', Format))
        det_file.write(struct.pack('4s', Subchunk1ID))
        det_file.write(struct.pack('i', Subchunk1Size))
        det_file.write(struct.pack('h', AudioFormat))
        det_file.write(struct.pack('h', NumChannels))
        det_file.write(struct.pack('i', SampleRate))
        det_file.write(struct.pack('i', ByteRate))
        det_file.write(struct.pack('h', BlockAlign))
        det_file.write(struct.pack('h', BitsPerSample))
        det_file.write(struct.pack('4s', Subchunk2ID))
        det_file.write(struct.pack('i', Subchunk2Size))
        det_file.write(data)


def head44_speech_headers(src_voice_path, det_voice_path, *args):
    """
    handle single voice
    :param src_voice_path: single voice path
    :param det_voice_path: Don't need to user input,get from det_path
    :param args: bitdepth and samplerate
    :return: None
    """
    bitdepth, samplerate = args
    with open(src_voice_path, 'rb') as f:
        f.seek(0, 0)
        # without voice head , add 44 head
        if not f.read(4) == struct.pack('4s', b'RIFF'):
            f.seek(0, 0)
            data = f.read()
            data_len = len(data)
            generate_voice(det_voice_path, data, data_len, bitdepth=bitdepth, samplerate=samplerate)
        else:
            f.seek(22, 0)
            channel = struct.unpack('h', f.read(2))[0]
            f.seek(24, 0)
            samplerate = struct.unpack('i', f.read(4))[0]
            f.seek(34, 0)
            bitdepth = struct.unpack('h', f.read(2))[0]
            head_len = 0
            for i in (36, 38, 50, 52, 70, 82, 106, 218):  # Here you can change, to adapt to more voice
                f.seek(i)
                if f.read(4) == struct.pack('4s', b'data'):
                    head_len = i + 8
                    break
            if 0 != head_len:
                f.seek(head_len)
                data = f.read()
                data_len = len(data)
                generate_voice(det_voice_path, data, data_len, bitdepth, samplerate, channel)
            else:
                print(src_voice_path + '\tdata sign not found')


def check_speech_headers(src_voice_path, bitdepth, samplerate):
    """
    judge voice header is standard 44 head?
    :param src_voice_path:src voice path
    :param bitdepth:bit depth,default 16
    :param samplerate:SampleRate,default 16k
    :return:True or False
    """
    with open(src_voice_path, 'rb') as file:
        # 1.The fixed format is "RIFF" and the voice head is 44 bits.
        file.seek(0, 0)
        if not file.read(4) == struct.pack('4s', b'RIFF'):
            print(src_voice_path + '\tThe fixed format is not RIFF')
            return False
        file.seek(36, 0)
        if not file.read(4) == struct.pack('4s', b'data'):
            print(src_voice_path + '\tThe voice head len is not 44')
            return False
        # 2.The sampling rate is 16k
        file.seek(24, 0)
        if not file.read(4) == struct.pack('i', samplerate):
            print('{voice_path}\tThis voice samplerate is not {samplerate}'.
                  format(voice_path=src_voice_path, samplerate=samplerate))
            return False
        # 3.16bit
        file.seek(34, 0)
        if not file.read(2) == struct.pack('h', bitdepth):
            print('{voice_path}\tThis voice byterate is not {bitdepth}'.
                  format(voice_path=src_voice_path, bitdepth=bitdepth))
            return False
        # Singles Road 1
        file.seek(22, 0)
        if not file.read(2) == struct.pack('h', 1):
            print('{voice_path}\tThis voice channel is not {channel}'.
                  format(voice_path=src_voice_path, channel=1))
            return False
        return True


def sr8216_speech_data(src_voice_path, det_voice_path, samplerate=16000):
    """
    8k -> 16k, core code
    :param src_voice_path: src_voice_path
    :param det_voice_path: det_voice_path
    :param samplerate: det voice SampleRate
    :return: None
    """
    with open(src_voice_path, 'rb') as f:
        f.seek(44, 0)
        data = f.read()
        data_len = len(data) * 2
        data = b''
        f.seek(44, 0)
        tmp = f.read(2)
        for i in range(int(data_len / 4) - 1):
            d1 = tmp
            d3 = f.read(2)
            d1_int, = struct.unpack('h', d1)
            d3_int, = struct.unpack('h', d3)
            d2_int = int((d1_int / 2 + d3_int / 2))
            data += d1
            data += struct.pack('h', d2_int)
            tmp = d3
        data += tmp
        data += tmp
        generate_voice(det_voice_path, data, data_len, bitdepth=16, samplerate=samplerate, channel=1)


def sr1628_speech_data(src_voice_path, det_voice_path, samplerate=8000):
    """
    16k->8k，, core code
    :param src_voice_path: src_voice_path
    :param det_voice_path: det_voice_path
    :param samplerate: det voice samplerate is 8000
    :return:None
    """
    with open(src_voice_path, 'rb') as f:
        f.seek(44, 0)
        data = f.read()
        data_len = int(len(data) / 2)
        data = b''
        f.seek(44, 0)
        for i in range(int(data_len / 2)):  # skip 2
            data += f.read(2)
            f.read(2)
        generate_voice(det_voice_path, data, data_len, bitdepth=16, samplerate=samplerate, channel=1)


# Need python3 environment
# def _sr1628_speech_data_fun1(src_voice_path, det_voice_path, samplerate=8000):
#    import numpy
#    with open(src_voice_path,'rb') as f:
#        f.seek(24,0)
#        src_samplerate = struct.unpack('i', f.read(4))[0]
#        f.seek(44,0)
#        #default is 2
#        compression_ratio = int(src_samplerate/samplerate)
#        compression_ratio = 2
#        half_data = numpy.frombuffer(f.read(), dtype=numpy.uint8).reshape([-1, 2])[::compression_ratio].reshape([-1]).tobytes()
#        generate_voice(det_voice_path, half_data, len(half_data), bitdepth=16, samplerate=samplerate, channel=1)

# Need python3 environment
# def _sr1628_speech_data_fun2(src_voice_path, det_voice_path,samplerate=8000):
#    from scipy.io import wavfile
#    musicData = wavfile.read(src_voice_path)[1]
#    wavfile.write(det_voice_path, 8000, musicData[::2])

def head44(src_path, det_path, *args):
    for src_voice_path, det_voice_path in dir_walk(src_path, det_path):
        head44_speech_headers(src_voice_path, det_voice_path, *args)


def check(src_path, bitdepth, samplerate):
    for src_voice_path, _ in dir_walk(src_path):
        check_speech_headers(src_voice_path, bitdepth, samplerate)


def get_speech_data(src_voice_path):
    with open(src_voice_path, 'rb') as f:
        f.seek(44, 0)
        return f.read()


def sr8216(src_path, det_path):
    for src_voice_path, det_voice_path in dir_walk(src_path, det_path):
        if check_speech_headers(src_voice_path, 16, 8000):
            sr8216_speech_data(src_voice_path, det_voice_path)


def sr1628(src_path, det_path):
    for src_voice_path, det_voice_path in dir_walk(src_path, det_path):
        if check_speech_headers(src_voice_path, 16,16000):
            sr1628_speech_data(src_voice_path, det_voice_path)


def link(src_path, det_voice_path):
    data = b''
    for src_voice_path, _ in dir_walk(src_path):
        data += get_speech_data(src_voice_path)
        data += struct.pack('iiiii', 0, 0, 0, 0, 0)
    data_len = len(data)
    generate_voice(det_voice_path, data, data_len)

def sox(src_path, det_path,bitdepth,samplerate):
    for src_voice_path, det_voice_path in dir_walk(src_path, det_path):
        linux_command = 'sox  {0} -r {1} -c 1 -b {2} {3}'.\
            format(src_voice_path,samplerate,bitdepth,det_voice_path)
        os.popen(linux_command)

def phone_or_web():
    """
    Receive parameters from user input
    :return: bitdepth,samplerate
    """
    bitdepth = 16
    samplerate = 16000
    # Need python2 environment
    if '2' == platform.python_version().split('.')[0]:
        if '8' == raw_input(
                '\nThe target voice default value is 16 bit depth, '
                'press 8 change, press ENTER to use default value:\n'):
            bitdepth = 8
        print('The target voice bitdepth will be {bitdepth} bit\n'.format(bitdepth=bitdepth))
        if '8000' == raw_input(
                'The target voice default value is 16000HZ SimpleRate, '
                'press 8000 change, press ENTER to use default value:\n'):
            samplerate = 8000
        print('The target voice samplerate will be {samplerate}HZ\n'.format(samplerate=samplerate))
    # Need python3 environment
    else:
        if '8' == input(
                '\nThe target voice default value is 16 bit depth, '
                'press 8 change, press ENTER to use default value:\n'):
            bitdepth = 8
        print('The target voice bitdepth will be {bitdepth} bit\n'.format(bitdepth=bitdepth))
        if '8000' == input(
                'The target voice default value is 16000HZ SimpleRate, '
                'press 8000 change, press ENTER to use default value:\n'):
            samplerate = 8000
        print('The target voice samplerate will be {samplerate}HZ\n'.format(samplerate=samplerate))
    print('-' * 20)
    return bitdepth, samplerate


def prompt_input_param():
    """
    Prompt the user to input
    :return: None
    """
    print('Usage: python script.py  {0}  src_path'.format(CHECK_PATTERN))
    print('or')
    print('Usage: python script.py  {0}  src_path  det_path'.format(STANDARD_PATTERN))
    print('or')
    print('Usage: python script.py  {0}  src_path det_path'.format(SR1628_PATTERN))
    print('or')
    print('Usage: python script.py  {0}  src_path det_path'.format(SR8216_PATTERN))
    print('or')
    print('Usage: python script.py  {0}  src_path [det_voice_path]'.format(LINK_PATTERM))
    print('or')
    print('Usage: python script.py  {0}  src_path det_path'.format(SOX_PATTERM))
    exit(2)

def check_python_version():
    """
    check python3 env version,Considering the compatibility, not used
    :return:None
    """
    if '3' != platform.python_version().split('.')[0]:
        print('Please Use Python 3.x Version')
        exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(len(sys.argv))
        prompt_input_param()
    param = (sys.argv[1]).lower()
    if param == STANDARD_PATTERN:
        src_path = sys.argv[2]
        det_path = sys.argv[3]
        print('**To ensure that all the file are PCM wav audio encoding**')
        print('-' * 20)
        bitdepth, samplerate = phone_or_web()
        head44(src_path, det_path, bitdepth, samplerate)
    elif param == CHECK_PATTERN:
        src_path = sys.argv[2]
        print('**To ensure that all the file are PCM wav audio encoding**')
        print('-' * 20)
        bitdepth, samplerate = phone_or_web()
        check(src_path, bitdepth, samplerate)
    elif param == SR1628_PATTERN:
        src_path = sys.argv[2]
        det_path = sys.argv[3]
        print('**To ensure that all the file are PCM wav audio encoding**')
        print('**To ensure that all the wav voice is 44 head**')
        print('**To ensure that all the wav voice is 1 channel**')
        print('**To ensure that all the wav voice is 16bit bitdepth**')
        print('**To ensure that all the wav voice is 16000 samplerate**')
        print('-' * 20)
        sr1628(src_path, det_path)
    elif param == SR8216_PATTERN:
        src_path = sys.argv[2]
        det_path = sys.argv[3]
        print('**To ensure that all the file are PCM wav audio encoding**')
        print('**To ensure that all the wav voice is 44 head**')
        print('**To ensure that all the wav voice is 1 channel**')
        print('**To ensure that all the wav voice is 16bit bitdepth**')
        print('**To ensure that all the wav voice is 8000 samplerate**')
        print('**To ensure that all the wav voice is 1 channel**')
        print('-' * 20)
        sr8216(src_path, det_path)
    elif param == LINK_PATTERM:
        src_path = sys.argv[2]
        voice_name = 'linked_voice.wav'
        if len(sys.argv) == 4:
            voice_name = sys.argv[3]
        det_voice_path = os.path.join(os.path.dirname(__file__), voice_name)
        print('**To ensure that all the file are PCM wav audio encoding**')
        print('**To ensure that all the wav voice is 44 head**')
        print('**To ensure that all the wav voice is 1 channel**')
        print('**To ensure that all the wav voice is 16bit bitdepth**')
        print('**To ensure that all the wav voice is 16000 samplerate**')
        print('-' * 20)
        link(src_path, det_voice_path)
    elif param == SOX_PATTERM:
        src_path = sys.argv[2]
        det_path = sys.argv[3]
        print('**To ensure that all the file are PCM wav audio encoding**')
        print('**To ensure that sys is linux**')
        print('**To ensure that sys has sox command**')
        print('**To ensure that all the wav voice is 44 head**')
        print('**To ensure that all the wav voice bitdepth >= your input**')
        print('**To ensure that all the wav voice samplerate >= your input**')
        print('-' * 20)
        bitdepth, samplerate = phone_or_web()
        sox(src_path, det_path,bitdepth, samplerate)
    else:
        prompt_input_param()