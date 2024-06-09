import numpy # модуль для работы с массивами
import math # модуль для работы с математическими функциями

# конструктор класса с инициализацией списка битов и длины битов
class BinaryMessage:
    def __init__(self):
        self.bits = []
        self.bitslen = 0

    # установление длины битов на основе текущего кол-ва битов в списке
    def set_bitslen(self):
        self.bitslen = len(self.bits)

    # перевод битового представления в текст
    def save_text(self):
        bin_ord = ''
        self.set_bitslen()
        # цикл по длине битов
        for i in range(self.bitslen):
            bin_ord += str(self.bits[i])
        byte_array = bytearray()
        for i in range(0, len(bin_ord), 8):
            byte = bin_ord[i:i + 8]
            byte_array.append(int(byte, 2))
        # Декодируем байты в текст с использованием кодировки cp1251
        text = byte_array.decode('cp1251')
        return text

# конструктор класса Key ринимает ключ в виде строки или списка
class Key:
    def __init__(self, input_key):
        if isinstance(input_key, str):
            input_list = input_key.split(' ')
        elif isinstance(input_key, list):
            input_list = input_key
        else:
            raise ValueError("Input data should be a string or a list.")
        # установка значений delta, begin и end на основе элементов списка
        self.delta = [int(input_list[0]), int(input_list[1])]
        self.begin, self.end = int(input_list[2]), int(input_list[3])

# конструктор класса System принимает сигнал, сообщение и ключ. Устанавливает кол-во семплов на секцию
class System:
    def __init__(self, signal, message, key):
        self.signal = signal
        self.message = message
        self.key = key
        self.hidden_bits_per_second = 16
        self.samples_per_section = self.signal.frame_rate // self.hidden_bits_per_second
        self.diff = self.signal.frame_rate % self.hidden_bits_per_second
    # возвращение комплексного числа x, который вычисляется как квадратный корень суммы квадратов его действительной и мнимой частей
    def get_mod(self, x):
        return math.sqrt(x.real ** 2 + x.imag ** 2)

    # принятие секции аудиосигнала
    def decode_section(self, section):
        extended_section = [] #
        extension = 4
        # для каждого элемента секции цикл добавляет в extended_section значения от s до s - 3
        for s in section:
            for d in range(extension):
                extended_section.append(s - d)
        # применяется преобразование Фурье
        dft = numpy.fft.fft(extended_section)
        # создаётся пустой список sqr_lg и для каждого элемента в dft вычисляется логарифм и возводится в квадрат
        sqr_lg = []
        for elem in dft:
            sqr_lg.append((numpy.log(elem)) ** 2)
        # применяется быстроее преобразование фурье
        ift = numpy.fft.ifft(sqr_lg)
        # индексы устанавливаются на основе значений из delta, умноженных на extension
        i0, i1 = extension*self.key.delta[0], extension*self.key.delta[1]
        imax0, imax1 = i0, i1

        # в цикле от -2 до 2 если модуль значения в ift по индексу i0+d больше нуля, то imax0 обновляется на i0+d
        # аналогично для индексов i1 и imax1
        for d in range(-2, 2):
            if self.get_mod(ift[i0 + d]) > self.get_mod(ift[imax0]):
                imax0 = i0 + d
            if self.get_mod(ift[i1 + d]) > self.get_mod(ift[imax1]):
                imax1 = i1 + d
        # если модуль значения в ift по индексу imax0 больше модуля значения по индексу imax1, возвращается строка 0, иначе 1
        if self.get_mod(ift[imax0]) > self.get_mod(ift[imax1]):
            return "0"
        else:
            return "1"
    # инициализация счётчика значением начала ключа и счётчика секций нулём
    def extract_stegomessage(self):
        counter = self.key.begin
        section_counter = 0
        # пока счётчик меньше значения конца ключа
        while counter < self.key.end:
            # извлекается секция аудиосигнала из первого каналаот текущего счётчика до счётчика + кол-во семплов на секцию
            section = self.signal.channels[0][counter:counter + self.samples_per_section]
            # декодируется секция с помощью метода decode_section, результат добавляется в биты сообщения
            self.message.bits.append(self.decode_section(section))
            counter += self.samples_per_section
            # счётчик секций увеличивается на 1
            section_counter += 1
            # сли счётчик секций достигает количества скрытых битов в секунду, то счётчик увеличивается на остаток и счётчик секций сбрасывается на 0
            if section_counter == self.hidden_bits_per_second:
                counter += self.diff
                section_counter = 0
        # сохраняется текст сообщения
        self.message.save_text()
    # сообщение возвращается
    def get_message(self):
        return self.message.save_text()

