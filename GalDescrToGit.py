import os
import re
import configparser
import sys
import threading
from ftplib import FTP
from queue import Queue
from colorama import Fore
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from redminelib import Redmine
import datetime
from datetime import datetime as cur_dt

# Установка пакетов для Win11
# pip3 install python-redmine
# pip3 install colorama
# python -m pip install --upgrade pip


# Addition class - print message/Дополнительный класс красивой печати типовых сообщений
class PrintMsg:
    def __init__(self):
        self.IsPrintDebug: bool = False

    def print_service_message(self, value):
        print(f'{Fore.BLUE}{value}{Fore.WHITE}')

    def print_header(self, value):
        print(f'{Fore.YELLOW}{value}{Fore.WHITE}')

    def print_error(self, value):
        print(f'{Fore.RED}Error: {value}{Fore.WHITE}')

    def print_success(self, value):
        print(f'{Fore.GREEN}Success: {value}{Fore.WHITE}')

    def print_debug(self, value):
        if self.IsPrintDebug:
            print(f'{Fore.MAGENTA}{value}{Fore.WHITE}')


# Addition class - settings/Дополнительный класс хранения настроек из CFG
class AppSettings:
    def __init__(self):
        self.MailSMTPServer: str = ''
        self.MailPassword: str = ''
        self.MailSMTPPort: int = 0
        self.MailFrom: str = ''
        self.MailTo: str = ''
        self.MailAdditionText: str = ''
        self.IsSendMail: bool = False
        self.IsIncludeNewInMail: bool = False
        self.FTPHost: str = ''
        self.FTPDir: str = ''
        self.ReMineHost: str = 'http://192.168.1.1'
        self.ReMineApiKey: str = ''
        self.ReMineIssueId: str = ''
        self.RedMineOverloadMail: bool = False

    def __str__(self):
        return f'AppSettings: {self.__dict__} '


# Thread download FTP/Потоковое скачивание файлов с FTP
class DownloadFromFTP(threading.Thread):

    def __init__(self, queue):
        """Инициализация потока"""
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        """Запуск потока"""
        while True:
            # Получаем параметры из очереди
            params = self.queue.get()

            # Обработка
            self.fun_download_from_ftp(params)

            # Отправляем сигнал о том, что задача завершена
            self.queue.task_done()

    def fun_download_from_ftp(self, params):

        ftp_name = params.get("ftpname")
        file_datetime: datetime = params.get("filedatetme")

        local_name = params.get("localname")
        local_file_path = os.path.join(currentDownloadFolder, f'{local_name}_WIN1251').upper()

        # Считаем хеш - чтоб разделить потоки для журнализации
        cur_hash = str(hash(ftp_name))

        printmsg.print_header(f'FTP ({cur_hash}). Download :{ftp_name}')

        try:
            ftp = FTP(appsettings.FTPHost, timeout=400)
            printmsg.print_debug(f"Login to FTP: {appsettings.FTPHost}, try goto {appsettings.FTPDir}. {ftp.login()}")
            ftp.cwd(appsettings.FTPDir)
            ftp.retrbinary("RETR " + ftp_name, open(local_file_path, 'wb').write)
            ftp.quit()

            # Время файла
            dt_epoch = file_datetime.timestamp()
            os.utime(local_file_path, (dt_epoch, dt_epoch))
            printmsg.print_success(f'FTP ({cur_hash}). {ftp_name}>>>{local_name}')

        except Exception as inst:
            printmsg.print_error(f'FTP ({cur_hash}). {type(inst)}')  # the exception instance
            printmsg.print_error(f'FTP ({cur_hash}). {inst.args}')  # arguments stored in .args
            printmsg.print_error(f'FTP ({cur_hash}). {inst}')  # __str__ allows args to be printed directly,
        finally:
            ftp.close()  # Close FTP connection


# Thead encode file/Потоковое перекодирование файла
class EncodeLocalFile(threading.Thread):
    def __init__(self, queue):
        """Инициализация потока"""
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        """Запуск потока"""
        while True:
            # Получаем параметры из очереди
            params = self.queue.get()

            # Обработка
            self.fun_encode_local_file(params)

            # Отправляем сигнал о том, что задача завершена
            self.queue.task_done()

    def fun_encode_local_file(self, params):

        file_datetime = params.get("filedatetme")
        file_name = params.get("filename")
        path_from = params.get("pathfrom")
        path_to = params.get("pathto")

        # Считаем хеш - чтоб разделить потоки для журнализации
        cur_hash = str(hash(file_name))

        printmsg.print_header(f'ENCODE ({cur_hash}). File: {path_from}')
        try:
            encode_text = ''

            with open(path_from, 'r', encoding='windows-1251') as fr:
                for codeText in fr.readlines():
                    # Убираем стоки с номерами задач
                    # т.к. тогда всегда будут исправления из-за скользящей нумерации
                    if codeText[0] != '№':
                        encode_text += codeText[:-1] + '\n'  # \r\n

            with open(path_to, 'w', encoding='UTF-8') as fw:
                fw.write(encode_text)

            # Установка времени редактирования файла
            dt_epoch = file_datetime.timestamp()
            os.utime(path_to, (dt_epoch, dt_epoch))

            printmsg.print_success(f'ENCODE ({cur_hash}). {path_from}>>>{path_to}')
        except Exception as inst:
            printmsg.print_error(f'ENCODE ({cur_hash}). {type(inst)}')  # the exception instance
            printmsg.print_error(f'ENCODE ({cur_hash}). {inst.args}')  # arguments stored in .args
            printmsg.print_error(f'ENCODE ({cur_hash}). {inst}')  # __str__ allows args to be printed directly,


# Addition class - work with FTP/Дополнительный класс работа с FTP
class FTPReader:

    # Get maximum file date from FTP/Получение максимальной даты редактирования файла на FTP

    def get_max_date_from_ftp(self) -> datetime:

        printmsg.print_header('Start GetMaxDateFromFTP')
        result: datetime = datetime.datetime(1, 1, 1, 0, 0)

        try:
            ftp = FTP(appsettings.FTPHost)
            printmsg.print_debug(f"Login to FTP: {appsettings.FTPHost}, try goto {appsettings.FTPDir}. {ftp.login()}")

            max_date_time: datetime = datetime.datetime(1, 1, 1, 0, 0)  # максимальная дата файла int в формате YYYYMMDD

            files = ftp.mlsd(appsettings.FTPDir)  # Получаем файлы с датами с FTP
            for file in files:
                file_name = file[0]
                file_type = file[1]['type']
                if file_type == 'file':  # смотрим только файлы
                    time_stamp = file[1]['modify']  # дата модификации файла
                    cur_file_date = datetime.datetime.strptime(time_stamp[:14], '%Y%m%d%H%M%S')

                    if max_date_time < cur_file_date:
                        max_date_time = cur_file_date
                        printmsg.print_debug(f'FileName = {file_name},'
                                             f' FileType =  {file_type}, {cur_file_date}/{time_stamp}')

            result = max_date_time

            printmsg.print_success(f'result = {result}')
        except Exception as inst:
            printmsg.print_error(f'{type(inst)}')  # the exception instance
            printmsg.print_error(f'{inst.args}')  # arguments stored in .args
            printmsg.print_error(f'{inst}')  # __str__ allows args to be printed directly,

        return result

    # Get list file from FTP/Получить список файлов с FTP с параметрами

    def get_ftp_file_list(self):

        printmsg.print_header('Start GetFTPFileList')
        result = []

        try:
            ftp = FTP(appsettings.FTPHost)
            printmsg.print_debug(f"Login to FTP: {appsettings.FTPHost}, try goto {appsettings.FTPDir}. {ftp.login()}")

            files = ftp.mlsd(appsettings.FTPDir)  # Получаем файлы с датами с FTP
            for file in files:
                file_name = file[0]
                file_type = file[1]['type']
                if file_type == 'file' and file_name.find('.txt') != -1:  # смотрим только файлы
                    # Оставить только имя файла без версии ресурса
                    local_file = re.sub('_(\d)+\.', '.',
                                        file_name)  # регулярное выражение '_'+ 'несколько цифр' + '.'

                    # Время файла
                    time_stamp = file[1]['modify']
                    cur_file_date = int(time_stamp[:8])  # int в формате YYYYMMDD
                    dt = datetime.datetime.strptime(str(cur_file_date), '%Y%m%d')

                    # Полный путь к FTP, оригинальное имя файла, новое имя без версии, дата редактирования
                    _row = {"ftppath": f'{appsettings.FTPHost}/{appsettings.FTPDir}/{file_name}',
                            "ftpname": file_name,
                            "localname": local_file.upper(),
                            "filedatetme": dt}
                    result.append(_row)
                    printmsg.print_debug(f"*ftp: {_row}")
                    ftp.close()
            printmsg.print_success(f'Count file to download = {len(result)}')
        except Exception as inst:
            printmsg.print_error(f'{type(inst)}')  # the exception instance
            printmsg.print_error(f'{inst.args}')  # arguments stored in .args
            printmsg.print_error(f'{inst}')  # __str__ allows args to be printed directly,

        return result

    # Delete old file and Download new/Удаление старых файлов и загрузка новых с FTP

    def down_load_ftp(self):
        # Удалить все файлы *.txt + ".TXT_WIN1251 в каталоге назначения
        printmsg.print_header(f'Delete old file')
        count = 0
        try:
            for path, sub_dirs, files in os.walk(currentDownloadFolder):
                if path == currentDownloadFolder:
                    for file in files:
                        if file.find(".txt") or file.find(".TXT_WIN1251") != -1:
                            count = count + 1
                            printmsg.print_debug(f'*{path}{file}')
                            os.remove(os.path.join(path, file).lower())

            printmsg.print_success(f'Delete {count} old file')
        except:
            printmsg.print_error(f'Delete old file')

        printmsg.print_header(f'Starting create download list')
        ftp_list = ftp_reader.get_ftp_file_list()  # список файлов с FTP

        # Download FTP file
        printmsg.print_header(f'Starting download FTP file')
        try:
            queue_ftp = Queue()
            # Запускаем потом и очередь
            for i in range(10):
                t = DownloadFromFTP(queue_ftp)
                t.daemon = True
                t.start()

            # Даем очереди нужные нам ссылки для скачивания (FTPList[:1])
            for el in ftp_list:
                queue_ftp.put(el)

            # Ждем завершения работы очереди
            queue_ftp.join()

            printmsg.print_success(f'Download FTP {len(ftp_list)} files')
        except:
            printmsg.print_error(f'Download FTP')


# Encode file to UTF8/Перекодирование файлов в UTF8 т.к. GIT не поддерживает WIN1251
def encode_files():
    # Удалить все файлы *.txt в рабочем каталоге, где в имени файла нет _WIN1251
    # это старые перекодированные файлы
    printmsg.print_header(f'Delete old convert file')
    count = 0
    try:

        for path, sub_dirs, files in os.walk(currentDownloadFolder):
            if path == currentDownloadFolder:
                for file in files:
                    if file.find(".TXT_WIN1251") == -1:
                        count = count + 1
                        printmsg.print_debug(f'*{path}{file}')
                        os.remove(os.path.join(path, file).lower())

        printmsg.print_success(f'Delete {count} old file')
    except:
        printmsg.print_error(f'Delete old file')

    # Файлы для перекодировки
    printmsg.print_header(f'Starting get list encode file')
    dos_code_list = []

    for path, sub_dirs, files in os.walk(currentDownloadFolder):
        if path == currentDownloadFolder:
            for file in files:
                if file.find(".TXT_WIN1251") != -1:
                    # дата модификации файла
                    time_stamp = os.path.getmtime(os.path.join(path, file))
                    cur_file_date = datetime.datetime.fromtimestamp(time_stamp)  # int в формате YYYYMMDD

                    row = {"filename": file,
                           "pathfrom": f'{os.path.join(path, file)}',
                           "pathto": f'{os.path.join(path, file.replace("_WIN1251", ""))}',
                           "filedatetme": cur_file_date}
                    dos_code_list.append(row)
                    printmsg.print_debug(row)

    printmsg.print_success(f'Get EnCode {len(dos_code_list)} file`s')

    printmsg.print_header(f'Starting encode file')
    try:
        queue_encode_file = Queue()
        # Запускаем потом и очередь
        for i in range(10):
            t = EncodeLocalFile(queue_encode_file)
            t.daemon = True
            t.start()
        # Даем очереди нужные нам ссылки для скачивания
        for el in dos_code_list:
            queue_encode_file.put(el)

        # Ждем завершения работы очереди
        queue_encode_file.join()
        printmsg.print_success(f'Encode {len(dos_code_list)} files')
    except:
        printmsg.print_error(f'Encode file')


# Get date whit out time/Получить дату без времени
def get_date_from_datetime(value: datetime) -> datetime:
    result: datetime = datetime.datetime(int(value.year), int(value.month), int(value.day), 0, 0)
    return result


# Get name class.var to lower. Template: classname.valuename=
# Params f"{appsettings.MailSMTPServer=}" => MailSMTPServer
def get_class_value_name_low(variable):
    var_str = get_value_name_low(variable)
    var_str = var_str.split('.')[1]
    return var_str


# Get name class.var to lower. Template: valuename=
# Params f"{appsettings.MailSMTPServer=}" => appsettings.MailSMTPServer
def get_value_name_low(variable):
    var_str = variable.split('=')[0].lower()
    return var_str


# Read config file/Чтение конфигурационного файла
def read_config(filepath):
    if os.path.exists(filepath):
        printmsg.print_header(f'Start ReadConfig')

        config = configparser.ConfigParser()
        config.read(filepath, "utf8")
        config.sections()

        var_settings_name = get_class_value_name_low(f"{appsettings.MailPassword=}")
        appsettings.MailPassword = config.has_option("Settings", var_settings_name) and config.get("Settings",
                                                                                                   var_settings_name) or None

        var_settings_name = get_class_value_name_low(f"{appsettings.MailSMTPServer=}")
        appsettings.MailSMTPServer = config.has_option("Settings", var_settings_name) and config.get("Settings",
                                                                                                     var_settings_name) or None

        var_settings_name = get_class_value_name_low(f"{appsettings.MailSMTPPort=}")
        appsettings.MailSMTPPort = config.has_option("Settings", var_settings_name) and config.getint("Settings",
                                                                                                      var_settings_name) or 0

        var_settings_name = get_class_value_name_low(f"{appsettings.MailFrom=}")
        appsettings.MailFrom = config.has_option("Settings", var_settings_name) and config.get("Settings",
                                                                                               var_settings_name) or None

        var_settings_name = get_class_value_name_low(f"{appsettings.MailTo=}")
        appsettings.MailTo = config.has_option("Settings", var_settings_name) and config.get("Settings",
                                                                                             var_settings_name) or None

        var_settings_name = get_class_value_name_low(f"{appsettings.MailAdditionText=}")
        appsettings.MailAdditionText = config.has_option("Settings", var_settings_name) and config.get("Settings",
                                                                                                       var_settings_name) or None

        var_settings_name = get_class_value_name_low(f"{appsettings.FTPHost=}")
        appsettings.FTPHost = config.has_option("Settings", var_settings_name) and config.get("Settings",
                                                                                              var_settings_name) or None

        var_settings_name = get_class_value_name_low(f"{appsettings.FTPDir=}")
        appsettings.FTPDir = config.has_option("Settings", var_settings_name) and config.get("Settings",
                                                                                             var_settings_name) or None
        # Note that the accepted values for the option are "1", "yes", "true", and "on"
        var_settings_name = get_class_value_name_low(f"{appsettings.IsSendMail=}")
        appsettings.IsSendMail = config.has_option("Settings", var_settings_name) and config.getboolean("Settings",
                                                                                                        var_settings_name) or False

        var_settings_name = get_class_value_name_low(f"{appsettings.IsIncludeNewInMail=}")
        appsettings.IsIncludeNewInMail = config.has_option("Settings", var_settings_name) and config.getboolean(
            "Settings",
            var_settings_name) or False

        var_settings_name = get_class_value_name_low(f"{printmsg.IsPrintDebug=}")
        printmsg.IsPrintDebug = config.has_option("Settings", var_settings_name) and config.getboolean("Settings",
                                                                                                       var_settings_name) or False

        var_settings_name = get_class_value_name_low(f"{appsettings.ReMineHost=}")
        appsettings.ReMineHost = config.has_option("Settings", var_settings_name) and config.get("Settings",
                                                                                                 var_settings_name) or None

        var_settings_name = get_class_value_name_low(f"{appsettings.ReMineApiKey=}")
        appsettings.ReMineApiKey = config.has_option("Settings", var_settings_name) and config.get("Settings",
                                                                                                   var_settings_name) or None

        var_settings_name = get_class_value_name_low(f"{appsettings.ReMineIssueId=}")
        appsettings.ReMineIssueId = config.has_option("Settings", var_settings_name) and config.get("Settings",
                                                                                                    var_settings_name) or None

        var_settings_name = get_class_value_name_low(f"{appsettings.RedMineOverloadMail=}")
        appsettings.RedMineOverloadMail = config.has_option("Settings", var_settings_name) and config.getboolean(
            "Settings",
            var_settings_name) or False
        printmsg.print_success(f'Read config: {filepath}')
        return True
    else:
        printmsg.print_header(f'Start create config')
        config = configparser.ConfigParser()
        config.add_section("Settings")

        var_settings_name = get_class_value_name_low(f"{appsettings.MailPassword=}")
        config.set("Settings", var_settings_name, '****Replace mail hash password (f9-4hfgq2h[)***')

        var_settings_name = get_class_value_name_low(f"{appsettings.MailSMTPServer=}")
        config.set("Settings", var_settings_name, 'smtp.gmail.com')

        var_settings_name = get_class_value_name_low(f"{appsettings.MailSMTPPort=}")
        config.set("Settings", var_settings_name, '587')

        var_settings_name = get_class_value_name_low(f"{appsettings.MailFrom=}")
        config.set("Settings", var_settings_name, 'put@gmail.com')

        var_settings_name = get_class_value_name_low(f"{appsettings.MailTo=}")
        config.set("Settings", var_settings_name, 'get@gmail.com')

        var_settings_name = get_class_value_name_low(f"{appsettings.MailAdditionText=}")
        config.set("Settings", var_settings_name, 'You can read text from GIT')

        var_settings_name = get_class_value_name_low(f"{appsettings.FTPHost=}")
        config.set("Settings", var_settings_name, 'ftp.galaktika.ru')

        var_settings_name = get_class_value_name_low(f"{appsettings.FTPDir=}")
        config.set("Settings", var_settings_name, 'pub/support/galaktika/bug_fix/GAL910/DESCRIPTIONS')

        var_settings_name = get_class_value_name_low(f"{appsettings.IsSendMail=}")
        config.set("Settings", var_settings_name, 'false')

        var_settings_name = get_class_value_name_low(f"{appsettings.IsIncludeNewInMail=}")
        config.set("Settings", var_settings_name, 'false')

        var_settings_name = get_class_value_name_low(f"{printmsg.IsPrintDebug=}")
        config.set("Settings", var_settings_name, 'false')

        var_settings_name = get_class_value_name_low(f"{appsettings.ReMineHost=}")
        config.set("Settings", var_settings_name, 'http://192.168.1.1')

        var_settings_name = get_class_value_name_low(f"{appsettings.ReMineApiKey=}")
        config.set("Settings", var_settings_name, '')

        var_settings_name = get_class_value_name_low(f"{appsettings.ReMineIssueId=}")
        config.set("Settings", var_settings_name, '')

        var_settings_name = get_class_value_name_low(f"{appsettings.RedMineOverloadMail=}")
        config.set("Settings", var_settings_name, 'false')

        with open(filepath, "w") as config_file:
            config.write(config_file)

        printmsg.print_success(f'Create config: {filepath}')

        return False


# Get list last update file/Получение списка файлов из последнего обновления
def get_last_file_list(work_date: datetime):
    result = []
    no_time_date: datetime = get_date_from_datetime(work_date)
    printmsg.print_debug(f'Convert: {work_date}>>>{no_time_date}')

    for path, sub_dirs, files in os.walk(currentDownloadFolder):
        if path == currentDownloadFolder:
            for file in files:
                if file.find(".TXT") != -1:
                    # дата модификации файла
                    time_stamp = os.path.getmtime(os.path.join(path, file))
                    cur_file_date = datetime.datetime.fromtimestamp(time_stamp)  # int в формате YYYYMMDD

                    if no_time_date == cur_file_date:
                        row = {"filename": file,
                               "filepath": f'{os.path.join(path, file)}',
                               "filedatetme": cur_file_date}
                        result.append(row)
                        printmsg.print_debug(row)

    return result


# Read new Issue from file/Получение из файла текста новых правок
def get_new_text(last_update_file_list: []) -> str:
    printmsg.print_header('Start GetNewText')
    result = '\n<h2>File content (new issue)</h2>\n'
    try:
        index_f: int = 0
        for el in last_update_file_list:
            index_f = index_f + 1
            filename = el.get("filename")
            filepath = el.get("filepath")
            result += f'<h3>{index_f} File {filename}</h3>\n'

            start_i: bool = False  # Начало задачи
            issue_header: bool = False  # Начало текста задачи
            issue_text = ''  # Текст задачи
            is_new_issue: bool = False  # Признак новой задачи
            skip_file: bool = False  # Признак пропуска файла, новые задачи вначале - дальше файл можно пропустить
            index = 0
            index_i: int = 0
            with open(filepath, 'r', encoding='UTF-8') as fr:
                for line in fr.readlines():
                    index = index + 1
                    if skip_file:
                        printmsg.print_debug(f'Exit line: {index}')
                        break

                    # Начало задачи
                    if line.find('* ЗАДАЧА В JIRA:') != -1 and not start_i:
                        issue_header = True
                        start_i = True
                        is_new_issue = False
                        issue_text = ''

                    # Конец задачи
                    if line.find('* * *') != -1 and start_i:
                        start_i = False

                        if is_new_issue:
                            result += f'{issue_text}\n'

                    # признак новой задачи
                    if line.find('* ПЕРВОЕ РЕШЕНИЕ:') != -1 and start_i:
                        if line.find(': NEW') != -1 and start_i:
                            is_new_issue = True
                        else:
                            skip_file = True

                    if issue_header:
                        index_i = index_i + 1
                        issue_header = False
                        issue_text += f'<p><b>{index_f}.{index_i} {line[:-1]}</b></p>\n'
                    else:
                        cur_str = str(line[:-1])
                        if cur_str != '' and cur_str is not None and cur_str:
                            issue_text += f'{cur_str}<br>\n'

        printmsg.print_debug(f'{result}')
        printmsg.print_success(f'Get new text in path')
    except Exception as inst:
        printmsg.print_error(f'{type(inst)}')  # the exception instance
        printmsg.print_error(f'{inst.args}')  # arguments stored in .args
        printmsg.print_error(f'{inst}')  # __str__ allows args to be printed directly,

    return result


# Send email/Отправка e-mail
def sending_email(work_date: datetime, last_update_file_list: []):
    printmsg.print_header('Start SendingEmail')
    message = '<html><head></head><body>'
    message += f"<p>Check time: <b>{datetime.datetime.now().strftime('%d %b %Y, %H:%M')}<b></p>\n"
    message += f"<p>FTP UTC time: <b>{work_date.strftime('%d %b %Y, %H:%M')}</b></p>\n"
    message += f"<p>{appsettings.MailAdditionText}</p>\n\n"

    message += f"<h2>Updated files list:</h2>\n<ul>\n"
    for el in last_update_file_list:
        message += f'<li>{el.get("filename")}</li>\n'
    message += f"</ul>\n"

    if appsettings.IsIncludeNewInMail:
        message += get_new_text(last_update_file_list)

    message += '</body></html>'

    try:

        # Список получателей
        email_list = []

        if appsettings.RedMineOverloadMail:
            email_list = get_email_from_red_mine().split(',')
        else:
            email_list = appsettings.MailTo.split(',')

        for cur_email in email_list:
            printmsg.print_service_message(f'Send e-mail: {cur_email}')

            # Формирование текста сообщения e-mail
            e_mail_msg = MIMEMultipart()
            e_mail_msg["From"] = appsettings.MailFrom
            e_mail_msg["To"] = cur_email
            e_mail_msg["Subject"] = "Update ftp.galaktika.ru"
            e_mail_msg.attach(MIMEText(message, 'html'))

            printmsg.print_debug(f'{e_mail_msg.as_string()}')

            # Отправка сообщения
            server = smtplib.SMTP(appsettings.MailSMTPServer, appsettings.MailSMTPPort)
            server.starttls()
            server.login(appsettings.MailFrom, appsettings.MailPassword)

            text = e_mail_msg.as_string()
            server.sendmail(appsettings.MailFrom, cur_email, text)
            server.quit()
            printmsg.print_success(f'Sending email')

            try:
                now = cur_dt.now()

                #  Log e-mail
                email_log_folder = os.path.join(currentDirectory,"EMailLog")
                if not os.path.exists(email_log_folder):
                    os.makedirs(email_log_folder)

                logfile = os.path.join(email_log_folder, f'{cur_email.strip()}_{now.strftime("%Y.%m.%d %H-%M-%S")}.txt')
                with open(logfile, 'a', encoding='utf-8') as f:
                    f.write(f"{cur_email}\n\n{message}\n")
            except Exception as inst:
                printmsg.print_error(f'{type(inst)}')  # the exception instance
                printmsg.print_error(f'{inst.args}')  # arguments stored in .args
                printmsg.print_error(f'{inst}')  # __str__ allows args to be printed directly,

    except Exception as inst:
        printmsg.print_error(f'{type(inst)}')  # the exception instance
        printmsg.print_error(f'{inst.args}')  # arguments stored in .args
        printmsg.print_error(f'{inst}')  # __str__ allows args to be printed directly,


# Get local max file date/Получение максимальной даты редактирования файла в локальном каталоге
def get_max_date_from_local():
    printmsg.print_header('Start GetMaxDateFromLocal')
    result: datetime = datetime.datetime(1, 1, 1, 0, 0)
    try:
        for path, sub_dirs, files in os.walk(currentDownloadFolder):
            if path == currentDownloadFolder:
                for file in files:
                    if file.find(".TXT") != -1:
                        # дата модификации файла
                        time_stamp = os.path.getmtime(os.path.join(path, file))
                        cur_file_date = datetime.datetime.fromtimestamp(time_stamp)  # int в формате YYYYMMDD
                        if result < cur_file_date:
                            result = cur_file_date

        printmsg.print_success(f'result: {result}')
    except Exception as inst:
        printmsg.print_error(f'{type(inst)}')  # the exception instance
        printmsg.print_error(f'{inst.args}')  # arguments stored in .args
        printmsg.print_error(f'{inst}')  # __str__ allows args to be printed directly,

    return result


# Check email/проверка email по шаблону
def check_email(email) -> bool:
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    # pass the regular expression
    # and the string into the fullmatch() method
    if (re.fullmatch(regex, email)):
        return True
    return False


# Get watchers from Redmine.Issue to get e-mail/Получение наблюдателей из задачи RedMine,
# у наблюдателей получаем адреса почты
def get_email_from_red_mine() -> str:
    printmsg.print_header('Start GetEmailFromRedMine')
    result = str(appsettings.MailTo)

    try:
        redmine = Redmine(appsettings.ReMineHost, key=appsettings.ReMineApiKey)
        issue = redmine.issue.get(appsettings.ReMineIssueId, include=['watchers'])
        printmsg.print_debug(f'Количество наблюдателей RedMine = {len(issue.watchers)}')

        emails: str = ''
        if len(issue.watchers) > 0:
            for user in issue.watchers:
                usr = redmine.user.get(user.id)
                printmsg.print_debug(f'{user} = {usr.mail}')
                if check_email(str(usr.mail).strip()):
                    if len(emails) == 0:
                        emails = f'{str(usr.mail).strip()}'
                    else:
                        emails = f'{emails}, {str(usr.mail).strip()}'

        result = emails
    except Exception as inst:
        printmsg.print_error(f'{type(inst)}')  # the exception instance
        printmsg.print_error(f'{inst.args}')  # arguments stored in .args
        printmsg.print_error(f'{inst}')  # __str__ allows args to be printed directly,

    return result


# Check folder/сли есть *.TXT_WIN1251 - то надо удалить все файлы т.е. предыдущий запуск окончился ошибкой
def check_folder_to_error_end():
    printmsg.print_header(f'Start CheckFolder')
    is_error: bool = False
    try:
        for path, sub_dirs, files in os.walk(currentDownloadFolder):
            if path == currentDownloadFolder:
                for file in files:
                    if file.find(".TXT_WIN1251") != -1:
                        is_error = True

    except:
        printmsg.print_error(f'Delete old file')

    printmsg.print_success(f'{is_error=}')
    count: int = 0
    if is_error:
        try:
            for path, sub_dirs, files in os.walk(currentDownloadFolder):
                if path == currentDownloadFolder:
                    for file in files:
                        if file.find(".txt") or file.find(".TXT_WIN1251") != -1:
                            count = count + 1
                            printmsg.print_debug(f'*{path}{file}')
                            os.remove(os.path.join(path, file).lower())

            printmsg.print_success(f'Delete {count} old file')
        except:
            printmsg.print_error(f'Delete old file')


def main():
    printmsg.print_header('Start work')

    is_have_new_file = False  # проверка необходимости работы - только если есть новые файлы на FTP (по умолчанию должна быть False)
    is_get_max_local_date = True  # получить дату редактирования с локально
    is_get_max_ftp_date = True  # получить дату редактирования с FTP
    is_download_ftp = True  # скачивать файлы с FTP
    is_encode_file = True  # перекодировать файлы
    is_delete_download_file = True  # удалять не конвертированные файлы
    is_get_last_file_list = True  # получить список последних обновленных файлов
    is_sending_email = True  # отправка email

    # Если есть *.TXT_WIN1251 - то надо удалить все файлы т.е. предыдущий запуск окончился ошибкой
    check_folder_to_error_end()

    # максимальная дата файла в DownLoad
    local_max_date: datetime = datetime.datetime(1, 1, 1, 0, 0)
    if is_get_max_local_date:
        local_max_date = get_max_date_from_local()

    # максимальная дата файла на FTP
    ftp_max_date: datetime = datetime.datetime(1, 1, 1, 0, 0)
    if is_get_max_ftp_date:
        ftp_max_date = ftp_reader.get_max_date_from_ftp()

    # Проверка необходимости скачивания обновлений
    if get_date_from_datetime(local_max_date) < get_date_from_datetime(ftp_max_date):
        is_have_new_file = True
    else:
        printmsg.print_service_message('Нет обновлений')

    if is_have_new_file:
        # Перекачать файлы с FTP
        if is_download_ftp:
            ftp_reader.down_load_ftp()

        # Перекодировать в UTF8
        if is_encode_file:
            encode_files()

        # Удалить не перекодированные файлы
        if is_delete_download_file:
            printmsg.print_header(f'Starting delete DOS file')
            count = 0
            try:
                for path, sub_dirs, files in os.walk(currentDownloadFolder):
                    if path == currentDownloadFolder:
                        for file in files:
                            if file.find(".TXT_WIN1251") != -1:
                                count = count + 1
                                printmsg.print_debug(f'*{path}{file}')
                                os.remove(os.path.join(path, file).lower())

                printmsg.print_success(f'Delete {count} DOS file')
            except:
                printmsg.print_error(f'Delete DOS file')

        # Последние обновленные файлы
        last_update_file_list = []
        if is_get_last_file_list:
            last_update_file_list = get_last_file_list(ftp_max_date)
            printmsg.print_header(f'Find {len(last_update_file_list)} new file in path')
            for el in last_update_file_list:
                printmsg.print_debug(f'{el.get("filepath")}')

        # Отправка e-mail
        if is_sending_email:
            if appsettings.IsSendMail and len(last_update_file_list) > 0:
                sending_email(ftp_max_date, last_update_file_list)

    printmsg.print_success('End work')


if __name__ == '__main__':
    printmsg = PrintMsg()
    printmsg.IsPrintDebug = True

    ftp_reader = FTPReader()  # Работа с FTP
    appsettings = AppSettings()  # Настройки

    printmsg.print_service_message(f'Last update: Cherepanov Maxim masygreen@gmail.com (c), 01.2023')
    printmsg.print_service_message(f'Download Galaktika description')
    currentDirectory = os.getcwd()
    configFilePath = os.path.join(currentDirectory, 'config.cfg')

    # Создаем рабочий каталог
    currentDownloadFolder = os.path.join(currentDirectory, 'Download')
    if not os.path.exists(currentDownloadFolder):
        os.makedirs(currentDownloadFolder)

    if read_config(configFilePath):
        main()
        printmsg.print_service_message(f'Close')
        sys.exit(0)
    else:
        printmsg.print_error(f'Pleas edit default Config value: {configFilePath}')
        printmsg.print_service_message(f'Process skip...')
