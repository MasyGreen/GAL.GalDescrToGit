import os
import re
import configparser
import datetime
import sys
import threading
from ftplib import FTP
from queue import Queue
from colorama import Fore
import hashlib


# Addition class - print message
class PrintMsg:
    def __init__(self):
        self.IsPrintDebug: bool = False

    def PrintServiceMessage(self, value):
        print(f'{Fore.BLUE}{value}{Fore.WHITE}')

    def PrintHeader(self, value):
        print(f'{Fore.YELLOW}{value}{Fore.WHITE}')

    def PrintErrror(self, value):
        print(f'{Fore.RED}Error: {value}{Fore.WHITE}')

    def PrintSuccess(self, value):
        print(f'{Fore.GREEN}Success: {value}{Fore.WHITE}')

    def PrintDebug(self, value):
        if self.IsPrintDebug:
            print(f'{Fore.MAGENTA}{value}{Fore.WHITE}')


# Addition class - settings
class AppSettings:
    def __init__(self):
        self.MailSMTPServer: str = ''
        self.MailPassword: str = ''
        self.MailSMTPPort: int = 0
        self.MailAdr: str = ''
        self.IsSendMail: bool = False
        self.FTPHost: str = ''
        self.FTPDir: str = ''

    def __str__(self):
        return f'AppSettings: {self.__dict__} '


# Thead download FTP
class DownloadFromFTP(threading.Thread):
    """Потоковый загрузчик файлов"""

    def __init__(self, queue):
        """Инициализация потока"""
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        """Запуск потока"""
        while True:
            # Получаем url из очереди
            params = self.queue.get()

            # Скачиваем файл
            self.FunDownloadFromFTP(params)

            # Отправляем сигнал о том, что задача завершена
            self.queue.task_done()

    def FunDownloadFromFTP(self, params):

        ftpname = params.get("ftpname")
        filedatetme: datetime = params.get("filedatetme")

        localname = params.get("localname")
        localfilepath = os.path.join(currentDownloadFolder, f'{localname}_WIN1251').upper();

        # Считаем хеш - чтоб разделить потоки для журнализации
        curHash = str(hash(ftpname))

        printmsg.PrintHeader(f'FTP ({curHash}). Download :{ftpname}')

        try:
            ftp = FTP(appsettings.FTPHost, timeout=400)
            print(f"Login to FTP: {appsettings.FTPHost}, try goto {appsettings.FTPDir}. {ftp.login()}")
            ftp.cwd(appsettings.FTPDir)
            ftp.retrbinary("RETR " + ftpname, open(localfilepath, 'wb').write)
            ftp.quit()

            # Установка времени редактирования файла
            dt_epoch = filedatetme.timestamp()
            os.utime(localfilepath, (dt_epoch, dt_epoch))

            # Устанавливаем время редактирования
            printmsg.PrintSuccess(f'FTP ({curHash}). {ftpname}>>>{localname}')
        except Exception as inst:
            printmsg.PrintErrror(f'FTP ({curHash}). {type(inst)}')  # the exception instance
            printmsg.PrintErrror(f'FTP ({curHash}). {inst.args}')  # arguments stored in .args
            printmsg.PrintErrror(f'FTP ({curHash}). {inst}')  # __str__ allows args to be printed directly,
        finally:
            ftp.close()  # Close FTP connection


# Thead encode file
class DecodeLocalFile(threading.Thread):
    """Потоковый загрузчик файлов"""

    def __init__(self, queue):
        """Инициализация потока"""
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        """Запуск потока"""
        while True:
            # Получаем url из очереди
            params = self.queue.get()

            # Скачиваем файл
            self.FunDecodeLocalFile(params)

            # Отправляем сигнал о том, что задача завершена
            self.queue.task_done()

    def FunDecodeLocalFile(self, params):
        _codec_page = 'windows-1251'

        filedatetme = params.get("filedatetme")
        filename = params.get("filename")
        pathfrom = params.get("pathfrom")
        pathto = params.get("pathto")

        # Считаем хеш - чтоб разделить потоки для журнализации
        curHash = str(hash(filename))

        printmsg.PrintHeader(f'DECODE ({curHash}). File: {pathfrom}')
        try:
            decode_test = ''

            with open(pathfrom, 'r', encoding='windows-1251') as fr:
                for code_text in fr.readlines():
                    if code_text[0] != '№':
                        decode_test += code_text[:-1] + '\n'  # \r\n

            with open(pathto, 'w', encoding='UTF-8') as fw:
                fw.write(decode_test)

            # Установка времени редактирования файла
            dt_epoch = filedatetme.timestamp()
            os.utime(pathto, (dt_epoch, dt_epoch))

            printmsg.PrintSuccess(f'DECODE ({curHash}). {pathfrom}>>>{pathto}')
        except Exception as inst:
            printmsg.PrintErrror(f'DECODE ({curHash}). {type(inst)}')  # the exception instance
            printmsg.PrintErrror(f'DECODE ({curHash}). {inst.args}')  # arguments stored in .args
            printmsg.PrintErrror(f'DECODE ({curHash}). {inst}')  # __str__ allows args to be printed directly,


# Addition class - work with FTP
class FTPReader:

    # Get maximum file date from FTP
    def GetMaxDateFromFTP(self) -> datetime:
        printmsg.PrintHeader('Start GetMaxDateFromFTP')
        result: datetime = datetime.datetime.now()

        try:
            ftp = FTP(appsettings.FTPHost)
            print(f"Login to FTP: {appsettings.FTPHost}, try goto {appsettings.FTPDir}. {ftp.login()}")

            maxDateTime = 0  # максимальная дата файла int в формате YYYYMMDD

            files = ftp.mlsd(appsettings.FTPDir)  # Получаем файлы с датами с FTP
            for file in files:
                fileName = file[0]
                fileType = file[1]['type']
                if fileType == 'file':  # смотрим только файлы
                    timeStamp = file[1]['modify']  # дата модификации файла
                    curFileDate = int(timeStamp[:8])  # int в формате YYYYMMDD
                    if maxDateTime < curFileDate:
                        maxDateTime = curFileDate
                        printmsg.PrintDebug(f'FileName = {fileName}, FileType =  {fileType}, {curFileDate}')

            result = datetime.datetime.strptime(str(maxDateTime), '%Y%m%d')

            printmsg.PrintSuccess(f'result = {result}')
        except Exception as inst:
            printmsg.PrintErrror(f'{type(inst)}')  # the exception instance
            printmsg.PrintErrror(f'{inst.args}')  # arguments stored in .args
            printmsg.PrintErrror(f'{inst}')  # __str__ allows args to be printed directly,

        return result

    # Get list file from FTP
    def GetFTPFileList(self):
        printmsg.PrintHeader('Start GetFTPFileList')
        result = []

        try:
            ftp = FTP(appsettings.FTPHost)
            print(f"Login to FTP: {appsettings.FTPHost}, try goto {appsettings.FTPDir}. {ftp.login()}")

            files = ftp.mlsd(appsettings.FTPDir)  # Получаем файлы с датами с FTP
            for file in files:
                fileName = file[0]
                fileType = file[1]['type']
                if fileType == 'file' and fileName.find('.txt') != -1:  # смотрим только файлы
                    # Оставить только имя файла без версии ресурса
                    local_file = re.sub('_(\d)+\.', '.',
                                        fileName)  # регулярное выражение '_'+ 'несколько цифр' + '.'

                    # дата модификации файла
                    timeStamp = file[1]['modify']
                    curFileDate = int(timeStamp[:8])  # int в формате YYYYMMDD
                    dt = datetime.datetime.strptime(str(curFileDate), '%Y%m%d')

                    # Полный путь к FTP, оригинальное имя файла, новое имя без версии, дата редактирования
                    _row = {"ftppath": f'{appsettings.FTPHost}/{appsettings.FTPDir}/{fileName}',
                            "ftpname": fileName,
                            "localname": local_file.upper(),
                            "filedatetme": dt}
                    result.append(_row)
                    printmsg.PrintDebug(f"*ftp: {_row}")
                    ftp.close()
            printmsg.PrintSuccess(f'Count file to download = {len(result)}')
        except Exception as inst:
            printmsg.PrintErrror(f'{type(inst)}')  # the exception instance
            printmsg.PrintErrror(f'{inst.args}')  # arguments stored in .args
            printmsg.PrintErrror(f'{inst}')  # __str__ allows args to be printed directly,

        return result

    def DownLoadFTP(self):
        # Удалить все файлы *.txt + ".TXT_WIN1251 в каталоге назначения
        printmsg.PrintHeader(f'Delete old file')
        count = 0
        try:
            for path, subdirs, files in os.walk(currentDownloadFolder):
                for file in files:
                    if file.find(".txt") or file.find(".TXT_WIN1251") != -1:
                        count = count + 1
                        printmsg.PrintDebug(f'*{path}{file}')
                        os.remove(os.path.join(path, file).lower())
            printmsg.PrintSuccess(f'Delete {count} old file')
        except:
            printmsg.PrintErrror(f'Delete old file')

        printmsg.PrintHeader(f'Starting create download list')
        FTPList = ftpreader.GetFTPFileList()  # список файлов с FTP

        # with open(f'{currentDirectory}\JRN_{date.today()}.txt', 'w') as f:
        #     for item in FTPList:
        #         f.write("%s\n" % item)

        # Download FTP file
        printmsg.PrintHeader(f'Starting download FTP file')
        try:
            queueFTP = Queue()
            # Запускаем потом и очередь
            for i in range(10):
                t = DownloadFromFTP(queueFTP)
                t.daemon = True
                t.start()

            # Даем очереди нужные нам ссылки для скачивания (FTPList[:1])
            for el in FTPList[:2]:
                queueFTP.put(el)

            # Ждем завершения работы очереди
            queueFTP.join()

            printmsg.PrintSuccess(f'Download FTP {len(FTPList)} files')
        except:
            printmsg.PrintErrror(f'Download FTP')


def DecodeFile():
    # Удалить все файлы *.txt в каталоге назначения где в имени файла нет _WIN1251
    printmsg.PrintHeader(f'Delete old convert file')
    count = 0
    try:
        for path, subdirs, files in os.walk(currentDownloadFolder):
            for file in files:
                if file.find(".TXT_WIN1251") == -1:
                    count = count + 1
                    printmsg.PrintDebug(f'*{path}{file}')
                    os.remove(os.path.join(path, file).lower())
        printmsg.PrintSuccess(f'Delete {count} old file')
    except:
        printmsg.PrintErrror(f'Delete old file')

    # Файлы для перкодировки
    printmsg.PrintHeader(f'Starting get list encode file')
    DOSCodeList = []
    for path, subdirs, files in os.walk(currentDownloadFolder):
        for file in files:
            if file.find(".TXT_WIN1251") != -1:
                # дата модификации файла
                timeStamp = os.path.getmtime(os.path.join(path, file))
                curFileDate = datetime.datetime.fromtimestamp(timeStamp)  # int в формате YYYYMMDD

                row = {"filename": file,
                       "pathfrom": f'{os.path.join(path, file)}',
                       "pathto": f'{os.path.join(path, file.replace("_WIN1251", ""))}',
                       "filedatetme": curFileDate}
                DOSCodeList.append(row)
                printmsg.PrintDebug(row)

    printmsg.PrintSuccess(f'Get DeCode {len(DOSCodeList)} file`s')

    printmsg.PrintHeader(f'Starting encode file')
    try:
        queueDecodefile = Queue()
        # Запускаем потом и очередь
        for i in range(10):
            t = DecodeLocalFile(queueDecodefile)
            t.daemon = True
            t.start()
        # Даем очереди нужные нам ссылки для скачивания
        for el in DOSCodeList:
            queueDecodefile.put(el)

        # Ждем завершения работы очереди
        queueDecodefile.join()
        printmsg.PrintSuccess(f'Encode {len(DOSCodeList)} files')
    except:
        printmsg.PrintErrror(f'Encode file')


# Get name class.var to lower. Template: classname.valuename=
# Params f"{appsettings.MailSMTPServer=}" => MailSMTPServer
def GetClassValueNameLow(variable):
    varstr = GetValueNameLow(variable)
    varstr = varstr.split('.')[1]
    return varstr


# Get name class.var to lower. Template: valuename=
# Params f"{appsettings.MailSMTPServer=}" => appsettings.MailSMTPServer
def GetValueNameLow(variable):
    varstr = variable.split('=')[0].lower()
    return varstr


# Read config file
def ReadConfig(filepath):
    if os.path.exists(filepath):
        printmsg.PrintHeader(f'Start ReadConfig')

        config = configparser.ConfigParser()
        config.read(filepath, "utf8")
        config.sections()

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailPassword=}")
        appsettings.MailPassword = config.has_option("Settings", varsettingsname) and config.get("Settings",
                                                                                                 varsettingsname) or None

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailSMTPServer=}")
        appsettings.MailSMTPServer = config.has_option("Settings", varsettingsname) and config.get("Settings",
                                                                                                   varsettingsname) or None

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailSMTPPort=}")
        appsettings.MailSMTPPort = config.has_option("Settings", varsettingsname) and config.getint("Settings",
                                                                                                    varsettingsname) or 0

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailAdr=}")
        appsettings.MailAdr = config.has_option("Settings", varsettingsname) and config.get("Settings",
                                                                                            varsettingsname) or None

        varsettingsname = GetClassValueNameLow(f"{appsettings.FTPHost=}")
        appsettings.FTPHost = config.has_option("Settings", varsettingsname) and config.get("Settings",
                                                                                            varsettingsname) or None

        varsettingsname = GetClassValueNameLow(f"{appsettings.FTPDir=}")
        appsettings.FTPDir = config.has_option("Settings", varsettingsname) and config.get("Settings",
                                                                                           varsettingsname) or None
        # Note that the accepted values for the option are "1", "yes", "true", and "on"
        varsettingsname = GetClassValueNameLow(f"{appsettings.IsSendMail=}")
        appsettings.IsSendMail = config.has_option("Settings", varsettingsname) and config.getboolean("Settings",
                                                                                                      varsettingsname) or False

        varsettingsname = GetClassValueNameLow(f"{printmsg.IsPrintDebug=}")
        printmsg.IsPrintDebug = config.has_option("Settings", varsettingsname) and config.getboolean("Settings",
                                                                                                     varsettingsname) or False

        printmsg.PrintSuccess(f'Read config: {filepath}')
        return True
    else:
        printmsg.PrintHeader(f'Start create config')
        config = configparser.ConfigParser()
        config.add_section("Settings")

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailPassword=}")
        config.set("Settings", varsettingsname, '****Replace mail hash password (f9-4hfgq2h[)***')

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailSMTPServer=}")
        config.set("Settings", varsettingsname, 'smtp.gmail.com')

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailSMTPPort=}")
        config.set("Settings", varsettingsname, '587')

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailAdr=}")
        config.set("Settings", varsettingsname, 'test@gmail.com')

        varsettingsname = GetClassValueNameLow(f"{appsettings.FTPHost=}")
        config.set("Settings", varsettingsname, 'ftp.galaktika.ru')

        varsettingsname = GetClassValueNameLow(f"{appsettings.FTPDir=}")
        config.set("Settings", varsettingsname, 'pub/support/galaktika/bug_fix/GAL910/DESCRIPTIONS')

        varsettingsname = GetClassValueNameLow(f"{appsettings.IsSendMail=}")
        config.set("Settings", varsettingsname, 'false')

        varsettingsname = GetClassValueNameLow(f"{printmsg.IsPrintDebug=}")
        config.set("Settings", varsettingsname, 'false')

        with open(filepath, "w") as config_file:
            config.write(config_file)

        printmsg.PrintSuccess(f'Create config: {filepath}')

        return False


def GetLastFileList(workDate: datetime):
    result = []
    printmsg.PrintDebug(f'{workDate=}; {workDate.year}')
    noTimeDate: datetime = datetime.datetime(int(workDate.year), int(workDate.month), int(workDate.day), 0, 0)
    printmsg.PrintDebug(f'Convert: {workDate}>>>{noTimeDate}')

    for path, subdirs, files in os.walk(currentDownloadFolder):
        for file in files:
            if file.find(".TXT") != -1:
                # дата модификации файла
                timeStamp = os.path.getmtime(os.path.join(path, file))
                curFileDate = datetime.datetime.fromtimestamp(timeStamp)  # int в формате YYYYMMDD

                if workDate == curFileDate:
                    row = {"filename": file,
                           "filepath": f'{os.path.join(path, file)}',
                           "filedatetme": curFileDate}
                    result.append(row)
                    printmsg.PrintDebug(row)

    return result


def main():
    printmsg.PrintHeader('Start work')

    IsGetMaxDate = True  # получить дату редактирования с FTP
    IsDowloadFTP = False  # скачивать файлы с FTP
    IsDecodeFile = False  # перекодировать файлы
    IsDeleteDownloadFile = False  # удалять не конвертированные файлы
    IsGetLastFileList = True  # получить список последних обновленных файлов

    # максимальная дата файла на FTP
    ftpMaxDate: datetime = datetime.datetime.now()
    if IsGetMaxDate:
        ftpMaxDate = ftpreader.GetMaxDateFromFTP()
        printmsg.PrintDebug(f'{ftpMaxDate}')

    # Перекачать файлы с FTP
    if IsDowloadFTP:
        ftpreader.DownLoadFTP()

    # Перекодировать в UTF8
    if IsDecodeFile:
        DecodeFile()

    # Удалить не перекодированные файлы
    if IsDeleteDownloadFile:
        printmsg.PrintHeader(f'Starting delete DOS file')
        count = 0
        try:
            for path, subdirs, files in os.walk(currentDownloadFolder):
                for file in files:
                    if file.find(".TXT_WIN1251") != -1:
                        count = count + 1
                        printmsg.PrintDebug(f'*{path}{file}')
                        os.remove(os.path.join(path, file).lower())
            printmsg.PrintSuccess(f'Delete {count} DOS file')
        except:
            printmsg.PrintErrror(f'Delete DOS file')

    # Последние обновленные файлы
    lastUpdateFileList = []
    if IsGetLastFileList:
        lastUpdateFileList = GetLastFileList(ftpMaxDate)
        printmsg.PrintHeader(f'Find {len(lastUpdateFileList)} new file in path')
        for el in lastUpdateFileList:
            printmsg.PrintDebug(f'{el.get("filepath")}')

    printmsg.PrintSuccess('End work')


if __name__ == '__main__':
    printmsg = PrintMsg()
    printmsg.IsPrintDebug = True

    ftpreader = FTPReader()  # Работа с FTP
    appsettings = AppSettings()  # Настройки

    printmsg.PrintServiceMessage(f'Last update: Cherepanov Maxim masygreen@gmail.com (c), 01.2023')
    printmsg.PrintServiceMessage(f'Download Galaktika descrtiption')
    currentDirectory = os.getcwd()
    configFilePath = os.path.join(currentDirectory, 'config.cfg')

    # Создаем рабочий каталог
    currentDownloadFolder = os.path.join(currentDirectory, 'Download')
    if not os.path.exists(currentDownloadFolder):
        os.makedirs(currentDownloadFolder)

    if ReadConfig(configFilePath):
        main()
        printmsg.PrintServiceMessage(f'Close')
        sys.exit(0)
    else:
        printmsg.PrintErrror(f'Pleas edit default Config value: {configFilePath}')
        printmsg.PrintServiceMessage(f'Process skip...')
