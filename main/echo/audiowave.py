# импорт модулей для работы с системой
import os
import shutil
# импорт модуля для работы с массивами
import numpy
# импорт модуля для работы с WAV файлами
import wave
# импорт модуля для математических операций
import math

# создание класса Wave, содержащись словарь для сопоставления количества байтов на семпл с соответствующим типом данных
class Wave:
    types = {
        1: numpy.int8,
        2: numpy.int16,
        4: numpy.int32
    }

    # конструктор класса для чтения WAV файла
    def __init__(self, input_wav):
        self.wavein = wave.open(input_wav, 'r')
        self.channels_num = self.wavein.getnchannels() # кол-во каналов (моно/стерео)
        self.bytes_per_sample = self.wavein.getsampwidth()  # кол-во байтов на сэмпл
        self.frame_rate = self.wavein.getframerate()  # частота дискретизации
        self.frames_num = self.wavein.getnframes() # общее кол-во фреймов
        # чтение всех фреймов из файла и преобразование их в массив
        self.content = numpy.fromstring(self.wavein.readframes(self.frames_num),
                                        dtype=self.types[self.bytes_per_sample])
        self.wavein.close()

        # разделение данных на отдельные каналы, для каждого создаётся отдельный массив
        self.channels = []
        for n in range(self.channels_num):
            self.channels.append(self.content[n::self.channels_num])

        # создание списка stego установка значения switching
        self.stego = []
        self.switching = 3 * self.frame_rate

        # переменные для управления амплитудой сигнала
        self.decreasing_from = 0
        self.increasing_to = 0

    # метод для установки начальной точки уменьшения амплитуды сигнала
    def set_decreasing_from(self, key):
        self.decreasing_from = max(0, key.begin - self.switching) * self.channels_num

    # метод для установки конечной точки увеличения амплитуды сигнала
    def set_increasing_to(self, key):
        self.increasing_to = min(self.frames_num, key.end + self.switching) * self.channels_num

    # метод для преобразования амплитуд в байты
    def set_amplitude(self, inst_amp):
        content = []
        for a in inst_amp:
            amp_in_bytes = int(a).to_bytes(self.bytes_per_sample, byteorder='little', signed=True)
            for part in amp_in_bytes:
                content.append(part)
        return bytearray(content)

    # метод объединения каналов в один массив
    def unite_channels(self, channels):
        content = []
        for i in range(len(channels[0])):
            for j in range(2):
                content.append(channels[j][i])
        return content

    # метод для уменьшения амплитуды сигнала. Если канал стерео и текущий индекс нечётный, возвращает 1.0, иначе возвращает амплитуду на основе индекса
    def dec_signal(self, i, begin):
        if self.channels_num == 2 and i % 2 == 1:
            return 1.0
        return 1.0 - 0.2 * i / (begin - self.decreasing_from)

    # метод для увеличения амплитуды сигнала. Если канал стерео и текущий индекс нечётный, возвращает 1.0, иначе возвращает амплитуду на основе индекса
    def inc_signal(self, i, end):
        if self.channels_num == 2 and i % 2 == 1:
            return 1.0
        return 0.8 + 0.2 * i / (self.increasing_to - end)

    # метод для создания WAV файла стеганографического аудио
    def create_stegoaudio(self, key, audio_name):
        output_wav = f'{audio_name}_echo_encoded.wav'

        wave_out = wave.open(output_wav, 'w')
        wave_out.setparams(self.wavein.getparams())

        # устанавливаются начальные и конечные точки уменьшения и увеличения амплитуды сигнала
        self.set_decreasing_from(key)
        self.set_increasing_to(key)

        # запись начальных фреймов до точки уменьшения амплитуды
        wave_out.writeframesraw(self.content[:self.decreasing_from])
        # уменьшение амплитуды сигнала и запись фреймов с уменьшеной амплитудой
        dec = [math.floor(self.dec_signal(i, key.begin * self.channels_num) * amp) for i, amp
               in enumerate(self.content[self.decreasing_from:key.begin * self.channels_num])]
        wave_out.writeframesraw(self.set_amplitude(dec))

        # запись стеганографических данных
        wave_out.writeframesraw(self.set_amplitude(self.stego))

        # увеличение амплитуды сигнала и запись фреймов с увеличенной амплитудой
        inc = [math.floor(self.inc_signal(i, key.end * self.channels_num) * amp) for i, amp
               in enumerate(self.content[key.end * self.channels_num:self.increasing_to])]
        wave_out.writeframesraw(self.set_amplitude(inc))        # increasing
        wave_out.writeframesraw(self.content[self.increasing_to:])      # end

        # закрытие выходного WAV файла и перемещение его в папку media
        wave_out.close()
        destination_folder = 'media'
        shutil.move(output_wav, os.path.join(destination_folder, output_wav))

