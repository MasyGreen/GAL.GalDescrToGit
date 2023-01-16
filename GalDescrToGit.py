import os
import re
import configparser
import datetime
import sys
import threading
from ftplib import FTP
from queue import Queue
from colorama import Fore
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from redminelib import Redmine


# Addition class - print message/Дополнительный класс красивой печати типовых сообщений
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


# Thead download FTP/Потоковое скачивание файлов с FTP
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
            printmsg.PrintDebug(f"Login to FTP: {appsettings.FTPHost}, try goto {appsettings.FTPDir}. {ftp.login()}")
            ftp.cwd(appsettings.FTPDir)
            ftp.retrbinary("RETR " + ftpname, open(localfilepath, 'wb').write)
            ftp.quit()

            # Время файла
            dt_epoch = filedatetme.timestamp()
            os.utime(localfilepath, (dt_epoch, dt_epoch))
            printmsg.PrintSuccess(f'FTP ({curHash}). {ftpname}>>>{localname}')

        except Exception as inst:
            printmsg.PrintErrror(f'FTP ({curHash}). {type(inst)}')  # the exception instance
            printmsg.PrintErrror(f'FTP ({curHash}). {inst.args}')  # arguments stored in .args
            printmsg.PrintErrror(f'FTP ({curHash}). {inst}')  # __str__ allows args to be printed directly,
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
            self.FunEncodeLocalFile(params)

            # Отправляем сигнал о том, что задача завершена
            self.queue.task_done()

    def FunEncodeLocalFile(self, params):

        filedatetme = params.get("filedatetme")
        filename = params.get("filename")
        pathfrom = params.get("pathfrom")
        pathto = params.get("pathto")

        # Считаем хеш - чтоб разделить потоки для журнализации
        curHash = str(hash(filename))

        printmsg.PrintHeader(f'ENCODE ({curHash}). File: {pathfrom}')
        try:
            encodeText = ''

            with open(pathfrom, 'r', encoding='windows-1251') as fr:
                for codeText in fr.readlines():
                    # Убираем стоки с номерами задач
                    # т.к. тогда всегда будут исправления из-за скользящей нумерации
                    if codeText[0] != '№':
                        encodeText += codeText[:-1] + '\n'  # \r\n

            with open(pathto, 'w', encoding='UTF-8') as fw:
                fw.write(encodeText)

            # Установка времени редактирования файла
            dt_epoch = filedatetme.timestamp()
            os.utime(pathto, (dt_epoch, dt_epoch))

            printmsg.PrintSuccess(f'ENCODE ({curHash}). {pathfrom}>>>{pathto}')
        except Exception as inst:
            printmsg.PrintErrror(f'ENCODE ({curHash}). {type(inst)}')  # the exception instance
            printmsg.PrintErrror(f'ENCODE ({curHash}). {inst.args}')  # arguments stored in .args
            printmsg.PrintErrror(f'ENCODE ({curHash}). {inst}')  # __str__ allows args to be printed directly,


# Addition class - work with FTP/Дополнительный класс работа с FTP
class FTPReader:

    # Get maximum file date from FTP/Получение максимальной даты редактирования файла на FTP
    def GetMaxDateFromFTP(self) -> datetime:

        printmsg.PrintHeader('Start GetMaxDateFromFTP')
        result: datetime = datetime.datetime(1, 1, 1, 0, 0)

        try:
            ftp = FTP(appsettings.FTPHost)
            printmsg.PrintDebug(f"Login to FTP: {appsettings.FTPHost}, try goto {appsettings.FTPDir}. {ftp.login()}")

            maxDateTime: datetime = datetime.datetime(1, 1, 1, 0, 0)  # максимальная дата файла int в формате YYYYMMDD

            files = ftp.mlsd(appsettings.FTPDir)  # Получаем файлы с датами с FTP
            for file in files:
                fileName = file[0]
                fileType = file[1]['type']
                if fileType == 'file':  # смотрим только файлы
                    timeStamp = file[1]['modify']  # дата модификации файла
                    curFileDate = datetime.datetime.strptime(timeStamp[:14], '%Y%m%d%H%M%S')

                    if maxDateTime < curFileDate:
                        maxDateTime = curFileDate
                        printmsg.PrintDebug(f'FileName = {fileName}, FileType =  {fileType}, {curFileDate}/{timeStamp}')

            result = maxDateTime

            printmsg.PrintSuccess(f'result = {result}')
        except Exception as inst:
            printmsg.PrintErrror(f'{type(inst)}')  # the exception instance
            printmsg.PrintErrror(f'{inst.args}')  # arguments stored in .args
            printmsg.PrintErrror(f'{inst}')  # __str__ allows args to be printed directly,

        return result

    # Get list file from FTP/Получить список файлов с FTP с параметрами
    def GetFTPFileList(self):

        printmsg.PrintHeader('Start GetFTPFileList')
        result = []

        try:
            ftp = FTP(appsettings.FTPHost)
            printmsg.PrintDebug(f"Login to FTP: {appsettings.FTPHost}, try goto {appsettings.FTPDir}. {ftp.login()}")

            files = ftp.mlsd(appsettings.FTPDir)  # Получаем файлы с датами с FTP
            for file in files:
                fileName = file[0]
                fileType = file[1]['type']
                if fileType == 'file' and fileName.find('.txt') != -1:  # смотрим только файлы
                    # Оставить только имя файла без версии ресурса
                    local_file = re.sub('_(\d)+\.', '.',
                                        fileName)  # регулярное выражение '_'+ 'несколько цифр' + '.'

                    # Время файла
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

    # Delete old file and Download new/Удаление старых файлов и загрузка новых с FTP
    def DownLoadFTP(self):
        # Удалить все файлы *.txt + ".TXT_WIN1251 в каталоге назначения
        printmsg.PrintHeader(f'Delete old file')
        count = 0
        try:
            for path, subdirs, files in os.walk(currentDownloadFolder):
                if path == currentDownloadFolder:
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
            for el in FTPList:
                queueFTP.put(el)

            # Ждем завершения работы очереди
            queueFTP.join()

            printmsg.PrintSuccess(f'Download FTP {len(FTPList)} files')
        except:
            printmsg.PrintErrror(f'Download FTP')


# Encode file to UTF8/Перекодирование файлов в UTF8 т.к. GIT не поддерживает WIN1251
def EncodeFiles():
    # Удалить все файлы *.txt в рабочем каталоге, где в имени файла нет _WIN1251
    # это старые перекодированные файлы
    printmsg.PrintHeader(f'Delete old convert file')
    count = 0
    try:

        for path, subdirs, files in os.walk(currentDownloadFolder):
            if path == currentDownloadFolder:
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
        if path == currentDownloadFolder:
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

    printmsg.PrintSuccess(f'Get EnCode {len(DOSCodeList)} file`s')

    printmsg.PrintHeader(f'Starting encode file')
    try:
        queueEncodefile = Queue()
        # Запускаем потом и очередь
        for i in range(10):
            t = EncodeLocalFile(queueEncodefile)
            t.daemon = True
            t.start()
        # Даем очереди нужные нам ссылки для скачивания
        for el in DOSCodeList:
            queueEncodefile.put(el)

        # Ждем завершения работы очереди
        queueEncodefile.join()
        printmsg.PrintSuccess(f'Encode {len(DOSCodeList)} files')
    except:
        printmsg.PrintErrror(f'Encode file')


# Get date whit out time/Получить дату без времени
def GetDateFromDatetime(value: datetime) -> datetime:
    result: datetime = datetime.datetime(int(value.year), int(value.month), int(value.day), 0, 0)
    return result


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


# Read config file/Чтение конфигурационного файла
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

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailFrom=}")
        appsettings.MailFrom = config.has_option("Settings", varsettingsname) and config.get("Settings",
                                                                                             varsettingsname) or None

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailTo=}")
        appsettings.MailTo = config.has_option("Settings", varsettingsname) and config.get("Settings",
                                                                                           varsettingsname) or None

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailAdditionText=}")
        appsettings.MailAdditionText = config.has_option("Settings", varsettingsname) and config.get("Settings",
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

        varsettingsname = GetClassValueNameLow(f"{appsettings.IsIncludeNewInMail=}")
        appsettings.IsIncludeNewInMail = config.has_option("Settings", varsettingsname) and config.getboolean(
            "Settings",
            varsettingsname) or False

        varsettingsname = GetClassValueNameLow(f"{printmsg.IsPrintDebug=}")
        printmsg.IsPrintDebug = config.has_option("Settings", varsettingsname) and config.getboolean("Settings",
                                                                                                     varsettingsname) or False

        varsettingsname = GetClassValueNameLow(f"{appsettings.ReMineHost=}")
        appsettings.ReMineHost = config.has_option("Settings", varsettingsname) and config.get("Settings",
                                                                                               varsettingsname) or None

        varsettingsname = GetClassValueNameLow(f"{appsettings.ReMineApiKey=}")
        appsettings.ReMineApiKey = config.has_option("Settings", varsettingsname) and config.get("Settings",
                                                                                                 varsettingsname) or None

        varsettingsname = GetClassValueNameLow(f"{appsettings.ReMineIssueId=}")
        appsettings.ReMineIssueId = config.has_option("Settings", varsettingsname) and config.get("Settings",
                                                                                                  varsettingsname) or None

        varsettingsname = GetClassValueNameLow(f"{appsettings.RedMineOverloadMail=}")
        appsettings.RedMineOverloadMail = config.has_option("Settings", varsettingsname) and config.getboolean(
            "Settings",
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

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailFrom=}")
        config.set("Settings", varsettingsname, 'put@gmail.com')

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailTo=}")
        config.set("Settings", varsettingsname, 'get@gmail.com')

        varsettingsname = GetClassValueNameLow(f"{appsettings.MailAdditionText=}")
        config.set("Settings", varsettingsname, 'You can read text from GIT')

        varsettingsname = GetClassValueNameLow(f"{appsettings.FTPHost=}")
        config.set("Settings", varsettingsname, 'ftp.galaktika.ru')

        varsettingsname = GetClassValueNameLow(f"{appsettings.FTPDir=}")
        config.set("Settings", varsettingsname, 'pub/support/galaktika/bug_fix/GAL910/DESCRIPTIONS')

        varsettingsname = GetClassValueNameLow(f"{appsettings.IsSendMail=}")
        config.set("Settings", varsettingsname, 'false')

        varsettingsname = GetClassValueNameLow(f"{appsettings.IsIncludeNewInMail=}")
        config.set("Settings", varsettingsname, 'false')

        varsettingsname = GetClassValueNameLow(f"{printmsg.IsPrintDebug=}")
        config.set("Settings", varsettingsname, 'false')

        varsettingsname = GetClassValueNameLow(f"{appsettings.ReMineHost=}")
        config.set("Settings", varsettingsname, 'http://192.168.1.1')

        varsettingsname = GetClassValueNameLow(f"{appsettings.ReMineApiKey=}")
        config.set("Settings", varsettingsname, '')

        varsettingsname = GetClassValueNameLow(f"{appsettings.ReMineIssueId=}")
        config.set("Settings", varsettingsname, '')

        varsettingsname = GetClassValueNameLow(f"{appsettings.RedMineOverloadMail=}")
        config.set("Settings", varsettingsname, 'false')

        with open(filepath, "w") as config_file:
            config.write(config_file)

        printmsg.PrintSuccess(f'Create config: {filepath}')

        return False


# Get list last update file/Получение списка файлов из последнего обновления
def GetLastFileList(workDate: datetime):
    result = []
    noTimeDate: datetime = GetDateFromDatetime(workDate)
    printmsg.PrintDebug(f'Convert: {workDate}>>>{noTimeDate}')

    for path, subdirs, files in os.walk(currentDownloadFolder):
        if path == currentDownloadFolder:
            for file in files:
                if file.find(".TXT") != -1:
                    # дата модификации файла
                    timeStamp = os.path.getmtime(os.path.join(path, file))
                    curFileDate = datetime.datetime.fromtimestamp(timeStamp)  # int в формате YYYYMMDD

                    if noTimeDate == curFileDate:
                        row = {"filename": file,
                               "filepath": f'{os.path.join(path, file)}',
                               "filedatetme": curFileDate}
                        result.append(row)
                        printmsg.PrintDebug(row)

    return result


# Read new Issue from file/Получение из файла текста новых правок
def GetNewText(lastUpdateFileList: []) -> str:
    printmsg.PrintHeader('Start GetNewText')
    result = '\n<h2>File content (new issue)</h2>\n'
    try:
        indexF: int = 0
        for el in lastUpdateFileList:
            indexF = indexF + 1
            filename = el.get("filename")
            filepath = el.get("filepath")
            result += f'<h3>{indexF} File {filename}</h3>\n'

            startI: bool = False  # Начало задачи
            issueHeader: bool = False  # Начало текста задачи
            issueText = ''  # Текст задачи
            isNewIssue: bool = False  # Признак новой задачи
            skeepFile: bool = False  # Признак пропуска файла, новые задачи вначале - дальше файл можно пропустить
            index = 0
            indexI: int = 0
            with open(filepath, 'r', encoding='UTF-8') as fr:
                for line in fr.readlines():
                    index = index + 1
                    if skeepFile:
                        printmsg.PrintDebug(f'Exit line: {index}')
                        break

                    # Начало задачи
                    if line.find('* ЗАДАЧА В JIRA:') != -1 and not startI:
                        issueHeader = True
                        startI = True
                        isNewIssue = False
                        issueText = ''

                    # Конец задачи
                    if line.find('* * *') != -1 and startI:
                        startI = False

                        if isNewIssue:
                            result += f'{issueText}\n'

                    # признак новой задачи
                    if line.find('* ПЕРВОЕ РЕШЕНИЕ:') != -1 and startI:
                        if line.find(': NEW') != -1 and startI:
                            isNewIssue = True
                        else:
                            skeepFile = True

                    if issueHeader:
                        indexI = indexI + 1
                        issueHeader = False
                        issueText += f'<p><b>{indexF}.{indexI} {line[:-1]}</b></p>\n'
                    else:
                        curStr = str(line[:-1])
                        if curStr != '' and curStr != None and curStr:
                            issueText += f'{curStr}<br>\n'

        printmsg.PrintDebug(f'{result}')
        printmsg.PrintSuccess(f'Get new text in path')
    except Exception as inst:
        printmsg.PrintErrror(f'{type(inst)}')  # the exception instance
        printmsg.PrintErrror(f'{inst.args}')  # arguments stored in .args
        printmsg.PrintErrror(f'{inst}')  # __str__ allows args to be printed directly,

    return result


# Send email/Отправка e-mail
def SendingEmail(workDate: datetime, lastUpdateFileList: []):
    printmsg.PrintHeader('Start SendingEmail')
    message = '<html><head></head><body>'
    message += f"<p>Check time: <b>{datetime.datetime.now().strftime('%d %b %Y, %H:%M')}<b></p>\n"
    message += f"<p>FTP UTC time: <b>{workDate.strftime('%d %b %Y, %H:%M')}</b></p>\n"
    message += f"<p>{appsettings.MailAdditionText}</p>\n\n"

    message += f"<h2>Updated files list:</h2>\n<ul>\n"
    for el in lastUpdateFileList:
        message += f'<li>{el.get("filename")}</li>\n'
    message += f"</ul>\n"

    if appsettings.IsIncludeNewInMail:
        message += GetNewText(lastUpdateFileList)

    message += '</body></html>'

    try:

        # Список получателей
        emailist = []

        if appsettings.RedMineOverloadMail:
            emailist = GetEmailFromRedMine().split(',')
        else:
            emailist = appsettings.MailTo.split(',')


        for curEmail in emailist:
            printmsg.PrintServiceMessage(f'Send e-mail: {curEmail}')

            # Формирование текста сообщения e-mail
            e_mail_msg = MIMEMultipart()
            e_mail_msg["From"] = appsettings.MailFrom
            e_mail_msg["To"] = curEmail
            e_mail_msg["Subject"] = "Update ftp.galaktika.ru"
            e_mail_msg.attach(MIMEText(message, 'html'))

            printmsg.PrintDebug(f'{e_mail_msg.as_string()}')

            # Отправка сообщения
            server = smtplib.SMTP(appsettings.MailSMTPServer, appsettings.MailSMTPPort)
            server.starttls()
            server.login(appsettings.MailFrom, appsettings.MailPassword)

            text = e_mail_msg.as_string()
            server.sendmail(appsettings.MailFrom, curEmail, text)
            server.quit()
            printmsg.PrintSuccess(f'Sending email')

    except Exception as inst:
        printmsg.PrintErrror(f'{type(inst)}')  # the exception instance
        printmsg.PrintErrror(f'{inst.args}')  # arguments stored in .args
        printmsg.PrintErrror(f'{inst}')  # __str__ allows args to be printed directly,


# Get local max file date/Получение максимальной даты редактирования файла в локальном каталоге
def GetMaxDateFromLocal():
    printmsg.PrintHeader('Start GetMaxDateFromLocal')
    result: datetime = datetime.datetime(1, 1, 1, 0, 0)
    try:
        for path, subdirs, files in os.walk(currentDownloadFolder):
            if path == currentDownloadFolder:
                for file in files:
                    if file.find(".TXT") != -1:
                        # дата модификации файла
                        timeStamp = os.path.getmtime(os.path.join(path, file))
                        curFileDate = datetime.datetime.fromtimestamp(timeStamp)  # int в формате YYYYMMDD
                        if result < curFileDate:
                            result = curFileDate

        printmsg.PrintSuccess(f'result: {result}')
    except Exception as inst:
        printmsg.PrintErrror(f'{type(inst)}')  # the exception instance
        printmsg.PrintErrror(f'{inst.args}')  # arguments stored in .args
        printmsg.PrintErrror(f'{inst}')  # __str__ allows args to be printed directly,

    return result


# Check email/проверка email по шаблону
def СheckEmail(email) -> bool:
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    # pass the regular expression
    # and the string into the fullmatch() method
    if (re.fullmatch(regex, email)):
        return True
    return False


# Get watchers from Redmine.Issue to get e-mail/Получение наблюдателей из задачи RedMine, у наблюдателей получаем адреса почты
def GetEmailFromRedMine() -> str:
    printmsg.PrintHeader('Start GetEmailFromRedMine')
    result = str(appsettings.MailTo)

    try:
        redmine = Redmine(appsettings.ReMineHost, key=appsettings.ReMineApiKey)
        issue = redmine.issue.get(appsettings.ReMineIssueId, include=['watchers'])
        printmsg.PrintDebug(f'Количество наблюдателей RedMine = {len(issue.watchers)}')

        emails: str = ''
        if len(issue.watchers) > 0:
            for user in issue.watchers:
                usr = redmine.user.get(user.id)
                printmsg.PrintDebug(f'{user} = {usr.mail}')
                if СheckEmail(str(usr.mail).strip()):
                    if len(emails) == 0:
                        emails = f'{str(usr.mail).strip()}'
                    else:
                        emails = f'{emails}, {str(usr.mail).strip()}'

        result = emails
    except Exception as inst:
        printmsg.PrintErrror(f'{type(inst)}')  # the exception instance
        printmsg.PrintErrror(f'{inst.args}')  # arguments stored in .args
        printmsg.PrintErrror(f'{inst}')  # __str__ allows args to be printed directly,

    return result


def main():
    printmsg.PrintHeader('Start work')

    IsHaveNewFile = False  # проверка необходимости работы - только если есть новые файлы на FTP (по умолчанию должна быть False)
    IsGetMaxLocalDate = True  # получить дату редактирования с локально
    IsGetMaxFTPDate = True  # получить дату редактирования с FTP
    IsDowloadFTP = True  # скачивать файлы с FTP
    IsEncodeFile = True  # перекодировать файлы
    IsDeleteDownloadFile = True  # удалять не конвертированные файлы
    IsGetLastFileList = True  # получить список последних обновленных файлов
    IsSendingEmail = True  # отправка email

    # максимальная дата файла в DownLoad
    localMaxDate: datetime = datetime.datetime(1, 1, 1, 0, 0)
    if IsGetMaxLocalDate:
        localMaxDate = GetMaxDateFromLocal()

    # максимальная дата файла на FTP
    ftpMaxDate: datetime = datetime.datetime(1, 1, 1, 0, 0)
    if IsGetMaxFTPDate:
        ftpMaxDate = ftpreader.GetMaxDateFromFTP()

    # Проверка необходимости скачивания обновлений
    if GetDateFromDatetime(localMaxDate) < GetDateFromDatetime(ftpMaxDate):
        IsHaveNewFile = True
    else:
        printmsg.PrintServiceMessage('Нет обновлений')

    if IsHaveNewFile:
        # Перекачать файлы с FTP
        if IsDowloadFTP:
            ftpreader.DownLoadFTP()

        # Перекодировать в UTF8
        if IsEncodeFile:
            EncodeFiles()

        # Удалить не перекодированные файлы
        if IsDeleteDownloadFile:
            printmsg.PrintHeader(f'Starting delete DOS file')
            count = 0
            try:
                for path, subdirs, files in os.walk(currentDownloadFolder):
                    if path == currentDownloadFolder:
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

        # Отправка e-mail
        if IsSendingEmail:
            if appsettings.IsSendMail and len(lastUpdateFileList) > 0:
                SendingEmail(ftpMaxDate, lastUpdateFileList)

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
