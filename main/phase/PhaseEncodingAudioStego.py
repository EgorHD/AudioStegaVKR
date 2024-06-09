import os # модуль для работы с системой
import numpy as np # модуль для работы с массивами и числовыми операциями
from scipy.io import wavfile # функция для работы с WAV файлами

class PhaseEncodingAudioStego:
    # метод фазового кодирования
    def encodeAudio(self, audioLocation, stringToEncode) -> str:
        # конвертация аудиофайла в массив байтов
        self.convertToByteArray(audioLocation)
        # подготовка строки для кодирования
        stringToEncode = stringToEncode.ljust(100, '~')
        # вычисление длины текста в битах и длины блока
        textLength = 8 * len(stringToEncode)
        blockLength = int(2 * 2 ** np.ceil(np.log2(2 * textLength)))
        # вычисление числа блоков необходимых для хранения данных и изменяет размер аудиоданных так, чтобы их длина была кратна длине блока
        # если данные одномерные - преобразует их в двумерный массив
        blockNumber = int(np.ceil(self.audioData.shape[0] / blockLength))
        if len(self.audioData.shape) == 1:
            self.audioData.resize(blockNumber * blockLength, refcheck=False)
            self.audioData = self.audioData[np.newaxis]
        else:
            self.audioData.resize((blockNumber * blockLength, self.audioData.shape[1]), refcheck=False)
            self.audioData = self.audioData.T
        # разделение данных на блоки и применение к ним преобразования Фурье
        blocks = self.audioData[0].reshape((blockNumber, blockLength))
        blocks = np.fft.fft(blocks)
        # извлечение амплитуд и фаз
        magnitudes = np.abs(blocks)
        phases = np.angle(blocks)
        # вычисление разности фаз и преобразования текста в двоичный формат
        phaseDiffs = np.diff(phases, axis=0)
        textInBinary = np.ravel([[int(y) for y in format(ord(x), "08b")] for x in stringToEncode])
        # преобразование двоичных данных в фазовые значения
        textInPi = textInBinary.copy()
        textInPi[textInPi == 0] = -1
        textInPi = textInPi * -np.pi / 2
        # вставка фазовых данных в аудиоблоки
        blockMid = blockLength // 2
        phases[0, blockMid - textLength: blockMid] = textInPi
        phases[0, blockMid + 1: blockMid + 1 + textLength] = -textInPi[::-1]
        # восстановление фаз для всех блоков и выполнение обратного преобразования Фурье
        for i in range(1, len(phases)):
            phases[i] = phases[i - 1] + phaseDiffs[i - 1]
        blocks = (magnitudes * np.exp(1j * phases))
        blocks = np.fft.ifft(blocks).real
        # сохранение изменённых данных обратно в аудиоданные и сохранение файла
        self.audioData[0] = blocks.ravel().astype(np.int16)
        return self.saveToLocation(self.audioData.T, audioLocation)

    # метод фазового декодирования
    def decodeAudio(self, audioLocation) -> str:
        # конвертация аудиофайла в массив байтов
        self.convertToByteArray(audioLocation)
        # настройка параметров декодирования (длина текста и длина блоков для декодирвания)
        textLength = 800
        blockLength = 2 * int(2 ** np.ceil(np.log2(2 * textLength)))
        blockMid = blockLength // 2
        # извлечение фаз из первых блоков аудиоданных
        if len(self.audioData.shape) == 1:
            secret = self.audioData[:blockLength]
        else:
            secret = self.audioData[:blockLength, 0]
        secretPhases = np.angle(np.fft.fft(secret))[blockMid - textLength:blockMid]
        # преобразование фаз в двоичный текст
        secretInBinary = (secretPhases < 0).astype(np.int8)
        secretInIntCode = secretInBinary.reshape((-1, 8)).dot(1 << np.arange(8 - 1, -1, -1))
        # преобразование двоичного текста в строку символов и удаление символов заполнения
        return "".join(np.char.mod("%c", secretInIntCode)).replace("~", "")

    # метод чтение аудиофайла и сохранения его данных в атрибуте
    def convertToByteArray(self, audio):
        try:
            self.rate, self.audioData = wavfile.read(audio)
        except:
            pass
        self.audioData = self.audioData.copy()

    # метод сохранения изменённых аудиоданных в файл и возвращения пути к нему
    def saveToLocation(self, audioArray, location) -> str:
        dir = os.path.dirname(location)
        wavfile.write(dir + "/output-pc.wav", self.rate, audioArray)
        return dir + "/output-pc.wav"
