# оператор, который предоставляет функции работы с ОС
import os
# оператор, который предоставляет различные константы и функции для работы со строками
import string
# оператор, который предоставляет функции для работы со временем
import time
# оператор, который предоставляет возможность работы с файлами звуковых волн формата WAV
import wave

# класс для автоматической коррекции ошибок в словах
from autocorrect import Speller
# модуль для отправки сообщений пользователю
from django.contrib import messages
# класс для создания HTTP-ответов
from django.http import HttpResponse
# функция для рендеринга шаблонов
from django.shortcuts import render
# функция для транслитерации текста
from transliterate import translit


# импорт класса Wave из модуля audiowave
from main.echo.audiowave import Wave
# импорт функций из модуля coder
from main.echo.coder import BinaryMessage_encode, Key_encode, System_encode
# импорт классов из модуля decoder
from main.echo.decoder import BinaryMessage, Key, System
# импорт класса из модуля PhaseEncodingAudioStego
from main.phase.PhaseEncodingAudioStego import PhaseEncodingAudioStego

# создание переменной encoded_audio_path
encoded_audio_path = ''

# функция, для автоматического исправления ошибок в тексте на русском языке
def correct_grammar(text):
    spell = Speller('ru')
    return spell(text)

# функция для проверки входящего текста на латинские символы
def is_latin(text):
    if all(c in string.ascii_letters or c.isspace() for c in text):
        return True
    return False

# Страница вставки ЦВЗ
def index(request):
    # удаление содержимого папки media
    folder = 'media'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # удаление файла
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

    if request.method == 'POST':
        try:
            # старт секундомера времени вставки ЦВЗ
            time_start = time.time()
            # получение значения message из POST запроса
            text_message = request.POST.get('message', '')
            # алгоритм метода НЗБ
            if request.POST.get('button1'):
                # получение аудиофайла из запроса
                audio_file = request.FILES.get('audio')
                # определение веса аудиофайла
                audio_file_size = round(audio_file.size / 1024 / 1024, 5)
                # сохранение загруженного файла в папке media и чтение его содержимого в виде массива байтов
                uploaded_file_path = os.path.join('media/', audio_file.name)
                with open(uploaded_file_path, 'wb') as uploaded_file:
                    for chunk in audio_file.chunks():
                        uploaded_file.write(chunk)
                audio = wave.open(uploaded_file_path, mode="rb")
                frame_bytes = bytearray(list(audio.readframes(audio.getnframes())))
                # преобразование текстового сообщения в строку двоичных данных
                utf16_string = text_message.encode('utf-16')
                binary_string = ''.join(format(byte, '08b') for byte in utf16_string)
                # добавление двоичного представления длины сообщения в начало строки двоичных данных
                binary_string = format(len(binary_string), '016b') + binary_string
                # замена наименее значимых битов на биты из строки binary_string
                for i in range(len(binary_string)):
                    frame_bytes[i] = (frame_bytes[i] & 254) | int(binary_string[i])
                # сохранение получившегося байтового массива
                frame_modified = bytes(frame_bytes)
                # создание нового пути для сохранения аудиофайла с вставленным ЦВЗ с теми же параметрами
                # (число каналов, частота дискретизации, глубина бит и др), что и оригинал
                encoded_audio_path = os.path.join('media/', f'{audio_file.name.split(".")[0]}_lsb_encoded.wav')
                suggested_filename = f'{audio_file.name.split(".")[0]}_lsb_encoded.wav'
                with wave.open(encoded_audio_path, 'wb') as new_audio:
                    new_audio.setparams(audio.getparams())
                    new_audio.writeframes(frame_modified)
                # закрытие исходного и нового аудиофайла
                audio.close()
                # остановка секундомера времени вставки ЦВЗ
                time_end = round(time.time() - time_start, 5)
                # определение веса аудиофайла с вставленным ЦВЗ
                encoded_audio_file_size = round(os.path.getsize(encoded_audio_path) / 1024 / 1024, 5)
                # определение процента изменения веса аудиофайла
                percent = round((encoded_audio_file_size - audio_file_size) / audio_file_size * 100, 5)
                # сохранение encoded_audio_path в сессию
                request.session['encoded_path'] = encoded_audio_path
                # создание словаря для отображения его содержимого на веб-странице
                return render(request, 'code.html', {
                    'original_audio_path': uploaded_file_path,
                    'encoded_audio_path': encoded_audio_path,
                    'audio_file_size': audio_file_size,
                    'encoded_audio_file_size': encoded_audio_file_size,
                    'encoding_time': time_end,
                    'percent': percent,
                    'suggested_filename': suggested_filename,
                })
            # алгоритм метода Фазового кодирования
            elif request.POST.get('button2'):
                # получение аудиофайла
                audio_file = request.FILES['audio']
                # получение текстового сообщения
                message = request.POST.get('message')
                # проверка текста на принадлежность к латинскому алфавиту. Если сообщение
                # на русском языке, то программа транслитерирует его на латиницу
                if not is_latin(message):
                    message = translit(message, 'ru', reversed=True).lower()
                    print(f'Transliterated message: {message}')
                else:
                    print(f'Message is already in Latin: {message}')
                # обработка случая, когда транслитерация в латинский алфавит невозможна
                if not is_latin(message):
                    messages.error(request, 'Не удалось транслитерировать сообщение')
                    return render(request, 'code.html')
                # создание переменной пути к временному файлу
                temp_file_path = f'media/{audio_file.name}'
                # открытие временного файла в двоичном режиме и запись в него всех частей загруженного файла
                with open(temp_file_path, 'wb+') as dest:
                    for chunk in audio_file.chunks():
                        dest.write(chunk)
                # создание экземпляра класса PhaseEncodingAudioStego
                stego_obj = PhaseEncodingAudioStego()
                # кодирование аудиофайла с использованием сообщения message
                encoded_path = stego_obj.encodeAudio(temp_file_path, message)
                # cохранние получившегося файла в media
                encoded_filename = f'{audio_file.name.split(".")[0]}_phase_encoded.wav'
                with open(encoded_path, 'rb') as src:
                    with open(f'media/{encoded_filename}', 'wb+') as dest:
                        dest.write(src.read())
                uploaded_file_path = os.path.join('media/', audio_file.name)
                encoded_file_path = os.path.join('media/', encoded_filename)
                # остановка секундомера времени вставки ЦВЗ
                time_end = round(time.time() - time_start, 5)
                # определение веса исходного аудиофайла
                audio_file_size = round(audio_file.size / 1024 / 1024, 5)
                # определение веса получившегося аудиофайла
                encoded_audio_file_size = round(os.path.getsize(encoded_file_path) / 1024 / 1024, 5)
                # определение процента изменения размера аудиофайла
                percent = round((encoded_audio_file_size - audio_file_size) / audio_file_size * 100, 5)
                # сохранение encoded_audio_path в сессию
                request.session['encoded_path'] = encoded_file_path
                # создание словаря для отображения его содержимого на веб-странице
                return render(request, 'code.html', {
                    'original_audio_path': uploaded_file_path,
                    'encoded_audio_path': encoded_file_path,
                    'audio_file_size': audio_file_size,
                    'encoded_audio_file_size': encoded_audio_file_size,
                    'encoding_time': time_end,
                    'percent': percent,
                })
            # алгоритм метода Эхо-сигнала
            elif request.POST.get('button3'):
                # получение аудиофайла
                audio_file = request.FILES['audio']
                # получение текстового сообщения
                text = request.POST.get('message')
                # создание объекта класса Wave
                signal = Wave(audio_file)
                # создание объекта класса BinaryMessage
                message = BinaryMessage_encode(text)
                # создание объекта класса Key, который представляет ключ для кодирования и декодирования
                key = Key_encode()
                # создание объекта stegosystem класса System_encode, который представляет систему
                # стеганографии и предоставляет методы для создания стего-сигнала
                stegosystem = System_encode(signal, message, key)
                # создание стего-сигнала путём скрытия сообщения в исходном сигнале с использованием ключа
                stegosystem.create_stego()
                # сохранение стего-сигнала в аудиофайл с именем, полученным из исходного имени аудиофайла
                stegosystem.signal.create_stegoaudio(stegosystem.key, audio_file.name.split(".")[0])
                # значения перепенных сохраняются в переменные с тем же именем
                delta0, delta1, begin, end = key.save()
                # создание строки key, содержащей значения переменных
                key = f"{delta0} {delta1} {begin} {end}"
                # создание пути к временному файлу
                temp_file_path = f'media/{audio_file.name}'
                # открытие временного файла и запись туда чанков (кусков)
                with open(temp_file_path, 'wb+') as dest:
                    for chunk in audio_file.chunks():
                        dest.write(chunk)
                # сохранение загруженного файла в папке media
                uploaded_file_path = os.path.join('media/', audio_file.name)
                # остановка секундомера времени вставки ЦВЗ
                time_end = round(time.time() - time_start, 5)
                # определение веса исходного аудиофайла
                audio_file_size = round(audio_file.size / 1024 / 1024, 5)
                # определение веса получившегося аудиофайла
                encoded_audio_file_size = round(
                    os.path.getsize(f'media/{audio_file.name.split(".")[0]}_echo_encoded.wav') / 1024 / 1024, 5)
                encoded_file_path = f'media/{audio_file.name.split(".")[0]}_echo_encoded.wav'
                suggested_filename = f'{audio_file.name.split(".")[0]}_echo_encoded.wav'
                # процент изменения веса аудиофайла
                percent = round((encoded_audio_file_size - audio_file_size) / audio_file_size * 100, 5)
                # сохранение encoded_audio_path в сессию
                request.session['encoded_path'] = encoded_file_path
                # создание словаря для отображения его содержимого на веб-странице
                return render(request, 'code.html', {
                    'original_audio_path': uploaded_file_path,
                    'encoded_audio_path': encoded_file_path,
                    'audio_file_size': audio_file_size,
                    'encoded_audio_file_size': encoded_audio_file_size,
                    'encoding_time': time_end,
                    'percent': percent,
                    'key': key,
                    'suggested_filename': suggested_filename,
                })
        # обработка исключений при выполнении кода
        except Exception as e:
            print(f"Error: {e}")
            return HttpResponse("Error during encoding", status=500)
    # возвращение сгенерированной HTML страницы с использованем шаблона code.html
    return render(request, 'code.html')

# страница считывания ЦВЗ
def decode_audio(request):
    if request.method == 'POST':
        # старт секундомера времени считывания ЦВЗ
        time_start = time.time()
        try:
            # получение аудиофайла
            audio_file = request.FILES.get('audio')
            # алгоритм считывания методом НЗБ
            if request.POST.get('button3'):
                # открытие аудиофайла для чтения в бинарном режиме
                audio = wave.open(audio_file, mode='rb')
                # чтение всех байтов фреймов из аудиофайла и преобразование их в байтовый массив
                frame_bytes = bytearray(list(audio.readframes(audio.getnframes())))
                # извлечение первых 16 наименее значимых бит из 16 байтов фреймов для определения длины скрытого сообщения
                binary_string = ''.join([str(frame_bytes[i] & 1) for i in range(16)])
                # преобразование бинарной строки в целое число, которое указывает длину скрытого сообщения
                message_length = int(binary_string, 2)
                # извлечение наименее значимых бит из оставшихся байтов фреймов (начиная с 16 байта и до длины сообщения)
                binary_message = ''.join(
                    [str(frame_bytes[i] & 1) for i in range(16, 16 + message_length)])
                # преобразование бинарного сообщения в строку
                utf16_string = int(binary_message, 2).to_bytes((len(binary_message) + 7) // 8, 'big').decode('utf-16')
                # закрытие аудиофайла
                audio.close()
                # остановка секундомера времени считывания ЦВЗ
                time_end = round(time.time() - time_start, 5)
                # возвращение html страницы сгенерированной с помощью шаблона decode.html
                return render(request, 'decode.html', {'message': utf16_string, 'decoding_time': time_end})
            # алгоритм считывания ЦВЗ методом Фазового кодирования
            elif request.POST.get('button4'):
                try:
                    # сохранение загруженного аудиофайла путём записи каждого блока данных во временный файл
                    temp_file_path = f'media/{audio_file.name}'
                    with open(temp_file_path, 'wb+') as dest:
                        for chunk in audio_file.chunks():
                            dest.write(chunk)
                    # создание объекта PhaseEncodingAudioStego, который представляет методы для
                    # фазового кодировани и декодирования
                    stego_obj = PhaseEncodingAudioStego()
                    # вызов метода decodeAudio, который извлекает ЦВЗ из аудиофайла
                    secret_text = stego_obj.decodeAudio(temp_file_path)
                    # проверка наличия русского языка в ЦВЗ. Если русский язык имеется, то происходит транслитерация.
                    if request.POST.get('language') == 'russian':
                        secret_text = translit(secret_text, 'ru').lower()
                        print(f'Transliterated message: {secret_text}')
                        try:
                            # исправление грамматики
                            secret_text = correct_grammar(secret_text)
                        # ошибка при исправлении грамматики
                        except Exception as e:
                            print(f"Error during correcting grammar: {e}")
                            messages.error(request, 'Не удалось исправить грамматику')
                            return render(request, 'decode.html')
                    # остановка секундомера времени считывания ЦВЗ
                    time_end = round(time.time() - time_start, 5)
                    # возвращение html страницы, сгенерированной с помощью шаблона decode.html
                    return render(request, 'decode.html', {
                        'message': secret_text, 'decoding_time': time_end
                    })
                # ошибка при невозможности считывания ЦВЗ
                except:
                    messages.error(request, 'Невозможно декодировать аудиофайл')
                    return render(request, 'decode.html')
            # алгоритм считывания методом эхо-сигнала
            elif request.POST.get('button5'):
                # получение текста из поля key
                text = request.POST.get('key')
                # создание объектов signal, message и key с помощью соответсвтующих классов
                signal = Wave(audio_file)
                message = BinaryMessage()
                key = Key(text)
                # создание объекта stegosystem и передача туда объектов
                stegosystem = System(signal, message, key)
                # извлечение сообщения из сигнала с помощью метода extract_stegomessage
                stegosystem.extract_stegomessage()
                # получение раскодированного текста
                decoded_text = stegosystem.get_message()
                secret_text = decoded_text
                try:
                    # исправление грамматики
                    secret_text = correct_grammar(decoded_text)
                # ошибка при исправлении грамматики
                except Exception as e:
                    print(f"Error during correcting grammar: {e}")
                    messages.error(request, 'Не удалось исправить грамматику')
                    return render(request, 'decode.html')
                # остановка секундомера времени считывания ЦВЗ
                time_end = round(time.time() - time_start, 5)
                # возвращение html страницы, сгенерированной с помощью шаблона decode.html
                return render(request, 'decode.html', {
                    'message': secret_text, 'decoding_time': time_end
                })
        # ошибка при невозможности считывания ЦВЗ
        except Exception as e:
            print(f"Error during decoding: {e}")
            return HttpResponse("Error during decoding", status=500)
    # возвращение сгенерированной HTML страницы с использованем шаблона decode.html
    return render(request, 'decode.html')

# скачивание аудиофайла из веб-приложения
def download_encoded_audio(request):
    # получение пути к аудиофайлу из сессии
    encoded_path = request.session.get('encoded_path')
    # извлечение имени файла из пути и сохранение в переменной file_name
    file_name = encoded_path.split('/')[-1]
    # если путь существует, то открытие файла в режиме чтения бинарного файла
    if encoded_path:
        with open(encoded_path, 'rb') as src:
            # создание объекта для передачи ему содержимого файла в виде байтов
            response = HttpResponse(src.read(), content_type="audio/wav")
            # установка заголовка для указании имени файла при скачивании
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(file_name)
            # возвращение объекта с содержимым файла и указанными заголовками
            return response
    # если путь к закодированному аудио не существует, то появляется сообщение об ошибке
    return HttpResponse("Error during downloading", status=500)
