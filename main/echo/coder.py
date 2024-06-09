import math # модуль для математических операций
import numpy # модуль для работы с массивами
import random # модуль для генерации случайных чисел

# класс для преобразования текстового сообщения в последовательность битов
class BinaryMessage_encode:
    def __init__(self, input_txt):
        self.bits = []  # список для хранения закодированных битов
        self.input = input_txt  # входной текст

        for ch in self.input:
            symb_ord = ord(
                ch.encode('cp1251'))  # преобразование символа в его числовое представление в кодировке cp1251
            print(symb_ord)
            bin_ord = bin(symb_ord)[2:].zfill(
                8)  # числовое значение преобразуется в двоичный вид и дополняется нулями до 8 бит
            print(bin_ord)

            # добавляем двоичное представление символа в список битов без разделения
            for bit in bin_ord:
                self.bits.append(int(bit))

        self.average = numpy.mean(self.bits)  # среднее значение битов
        self.bitslen = len(self.bits)  # длина списка битов

# создание класса Key_encode для созданию ключа и инициализация списка delta и переменных begin и end
class Key_encode:
    def __init__(self):
        self.delta = []
        self.begin, self.end = 0, 0

    # метод для установки значения delta
    def set_delta(self, delta):
        self.delta = delta

    # метод для установки начальной точки begin в сэмплах
    def set_begin(self, begin):
        self.begin = begin

    # метод для установки конечной точки end в сэмплах
    def set_end(self, end):
        self.end = end

    # метод для сохранения ключа (возвращает значения delta, begin и end в виде строк)
    def save(self):
        return str(self.delta[0]), str(self.delta[1]), str(self.begin), str(self.end)


# создание класса System_encode и инициализация параметров системы
class System_encode:
    def __init__(self, signal, message, key):
        self.signal = signal # аудиосигнал
        self.message = message # сообщение для кодирования
        self.key = key # ключ для кодирования

        # инициализация параметров эха
        self.echo_volume = 0.3
        self.hidden_bits_per_second = 16
        self.volume_max = 0.9
        self.volume_min = 0.7
        self.delta_max = 30
        self.delta_min = 40

        # установка значения громкости эха и дельты в зависимости от среднего значения битов сообщения
        if self.message.average <= 0.5:
            self.volume0, self.volume1 = self.volume_max, self.volume_min
            self.key.set_delta([self.delta_max, self.delta_min])
        else:
            self.volume0, self.volume1 = self.volume_min, self.volume_max
            self.key.set_delta([self.delta_min, self.delta_max])

        # вычисление количества сэмплов на секцию и остаток семплов на секцию
        self.samples_per_section = self.signal.frame_rate // self.hidden_bits_per_second
        self.diff = self.signal.frame_rate % self.hidden_bits_per_second
        # установка начальной и конечной точки в ключе
        self.samples_per_message = self.count_samples()
        self.key.set_begin(self.get_begin())
        self.key.set_end(self.key.begin + self.samples_per_message)
        # инициализация пустого списка для стеганографических каналов
        self.stegochannels = []

    # вычисление количества сэмплов, необходимых для встраивания сообщения
    def count_samples(self):
        div_part = self.message.bitslen // self.hidden_bits_per_second * self.signal.frame_rate
        mod_part = self.message.bitslen % self.hidden_bits_per_second * self.samples_per_section
        return div_part + mod_part

    # вычисление начальной точки для встраивания сообщения
    def get_begin(self):
        rest = self.signal.frames_num % self.signal.frame_rate # остаток от деления общего кол-ва фреймов на частоту дискретизации
        acceptable_begin = self.signal.frames_num - self.samples_per_message - rest # максимальная допустимая начальная точка для встраивания сообщения
        max_second = acceptable_begin // self.signal.frame_rate # максимальное кол-во секунд для допустимой начальной точки
        rand_second = random.randint(math.floor(max_second * 0.05), max_second) # случайная секунда от max_second
        return rand_second * self.signal.frame_rate # возвращение начальной точки в сэмплах

    # функция для вычисления коэфициента сглаживания для текущего бита
    def smoothing_signal(self, i, position):
        x = self.message.bits[i] # текущий бит сообщения
        # константы для определения границ сглаживания
        a = 0.0005
        b = 0.9995
        if x == 0: # если x равен 0, то возвращается 0.0
            return 0.0
        k = position / self.samples_per_section # позиция внутри секции
        # если k находится внутри границ или соседние биты совпадают с текущим битом, возвращается 1.0
        # если k меньше или равно a, возвращается отношение k/a
        # если k больше или равно b, возвращается отношение (1.0 - k) / (1.0 - b)
        if (a < k < b) or (a > k and i != 0 and int(self.message.bits[i - 1]) == x) \
                or (k > b and i + 1 != self.message.bitslen and int(self.message.bits[i + 1]) == x):
            return 1.0
        if a >= k:
            return k / a
        if k >= b:
            return (1.0 - k) / (1.0 - b)

    # функция get_echo вычисляет значение эха для текущего сэмпла
    def get_echo(self, channel, k, n, counter):
        # значение нулевого эха
        echo0 = self.volume0 * self.echo_volume * (channel[k - self.key.delta[0]] if k >= self.key.delta[0] else 0) * \
                (1 - self.smoothing_signal(counter, k - n))
        # значение единичного эха
        echo1 = self.volume1 * self.echo_volume * (channel[k - self.key.delta[1]] if k >= self.key.delta[1] else 0) * \
                self.smoothing_signal(counter, k - n)
        return echo0 + echo1 # возвращение суммы нулевого и единичного эха

    # функция для встраивания сообщения в аудиосигал
    def embed_stegomessage(self, channel):
        # инициализируются счётчики секций и секунд
        second_counter = self.key.begin // self.signal.frame_rate
        section_counter = 0
        # вычисление начального уровня громкости
        volume = 1.0 - self.echo_volume * self.volume_max
        # инициализация пустого списка для стеганографического канала
        stegochannel = []

        # для каждого бита сообщения вычислется начальная точка секции и обновление счётчиков секций при необходимости
        for counter in range(self.message.bitslen):
            n = second_counter * self.signal.frame_rate + section_counter * self.samples_per_section
            for k in range(n, n + self.samples_per_section):
                stegochannel.append(math.floor(volume * channel[k] + self.get_echo(channel, k, n, counter)))
            section_counter += 1

            if section_counter == self.hidden_bits_per_second:
                for j in range(k, k + self.diff):
                    stegochannel.append(math.floor(volume * channel[j] + self.get_echo(channel, j, n, counter)))
                section_counter = 0
                second_counter += 1

        return stegochannel

    # создание стеганографического сигнала
    def create_stego(self):
        # встраивание сообщения в первый аудиоканал и добавление его в список стегоканалов
        self.stegochannels.append(self.embed_stegomessage(self.signal.channels[0]))
        # если аудиосигнал стерео, второй канал добавляется без изменений и каналы объединяются
        if self.signal.channels_num == 2:
            self.stegochannels.append((self.signal.channels[1])[self.key.begin:self.key.end])
            self.signal.stego = self.signal.unite_channels(self.stegochannels)
        else:
            self.signal.stego = self.stegochannels[0]
        # сохраняется ключ
        self.key.save()
