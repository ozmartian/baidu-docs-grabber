#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import signal
import sys
from enum import Enum

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from munch import Munch

signal.signal(signal.SIGINT, signal.SIG_DFL)
signal.signal(signal.SIGTERM, signal.SIG_DFL)


class BaiduDoc(QWidget):
    def __init__(self):
        super(BaiduDoc, self).__init__()
        self.workspace, self.filename = None, None
        self.outdir = QDir(QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
        self.procs = Munch(download=None, render=None, convert=None)
        self.work_folders = []
        self.setWindowTitle('Baidu Doc Grabber')
        self.setWindowIcon(QIcon(self.get_path('icon.png')))
        input_links = QTextEdit(self)
        input_links.setFontFamily('Microsoft YaHei')
        input_links.setPlaceholderText('copy & paste one or more Baidu Docs page links here')
        input_links.setWordWrapMode(QTextOption.NoWrap)
        input_links.setTextInteractionFlags(Qt.TextEditorInteraction)
        input_links.ensureCursorVisible()
        buttons = QDialogButtonBox(QDialogButtonBox.SaveAll | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(lambda: self.download_swfs(input_links.toPlainText().split('\n')))
        buttons.rejected.connect(qApp.quit)
        self.download_swfs()
        layout = QVBoxLayout()
        layout.addWidget(input_links)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self.setMinimumSize(600, 500)

    @pyqtSlot(list)
    def download_swfs(self, urls: list):
        savepath, _ = QFileDialog.getExistingDirectory(self, "Select a folder for the PDFs...",
                                                       self.outdir.absolutePath())
        if savepath:
            self.outdir = QDir(savepath)
            for url in urls:
                index = urls.index(url)
                swf_link = QUrl.fromUserInput(url)
                if swf_link.isValid():
                    self.work_folders.append(self.get_path('{0:03}'.format(index)))
                    os.makedirs(self.work_folders[index], exist_ok=True)
                    cmd = '{0} {1}'.format(Tools.DOWNLOAD.value, url)
                    self.procs.download = BaiduDoc.init_proc(cmd, True, self.check_downloads, self.work_folders[index])

    @pyqtSlot(int, QProcess.ExitStatus)
    def check_downloads(self, code: int, status: QProcess.ExitStatus):
        if code == 0 and status == QProcess.NormalExit:
            path = QDir(self.sender().workingDirectory())
            swfs = path.entryList('*.swf')
            if len(swfs) > 0:
                self.publish_pdf(path)

    def publish_pdf(self, path: QDir):
        for swf in path.entryList('*.swf'):
            cmd = '{0} -r 240 {2} -o {3]'.format(Tools.RENDER.value, swf, swf.replace('.swf', '.png'))
            self.procs.render = BaiduDoc.init_proc(cmd, True, self.convert, path)

    @pyqtSlot(int, QProcess.ExitStatus)
    def convert(self, code: int, status: QProcess.ExitStatus):
        if code == 0 and status == QProcess.NormalExit:
            path = QDir(self.sender().workingDirectory())
            swfs = path.entryList('*.swf')
            pngs = path.entryList('*.png')
            if len(swfs) == len(pngs):
                cmd = '{0} -adjoin {1} {2}'.format(Tools.CONVERT.value,
                                                   '{}/*.png'.format(path.absolutePath()),
                                                   '{0}/{1}.pdf'.format(self.outdir.absolutePath(), path.dirName()))
                self.procs.convert = BaiduDoc.init_proc(cmd, True, self.complete, path)

    @pyqtSlot(int, QProcess.ExitStatus)
    def complete(self, code: int, status: QProcess.ExitStatus):
        if code == 0 and status == QProcess.NormalExit:
            btn = QMessageBox.information(self,
                                          'Processing complete',
                                          'Your documents are finally ready!<br><br>Click the OPEN  button below to '
                                          'open the folder to view documents or click CLOSE to exit the application.',
                                          QMessageBox.Open | QMessageBox.Close, QMessageBox.Open)
            if btn == QMessageBox.Open:
                QDesktopServices.openUrl(QUrl.fromLocalFile(self.outdir.absolutePath()))
            qApp.quit()

    def handle_error(self, title: str, msg: str):
        QMessageBox.critical(self, title, msg, QMessageBox.Ok)

    @staticmethod
    def get_path(path: str = None):
        if getattr(sys, 'frozen', False) and getattr(sys, '_MEIPASS', False):
            # noinspection PyProtectedMember, PyUnresolvedReferences
            prepath = sys._MEIPASS
        else:
            prepath = os.path.dirname(os.path.realpath(sys.argv[0]))
        if path is not None:
            return os.path.join(prepath, path)
        else:
            return prepath

    @staticmethod
    def init_proc(cmd: str, autostart: bool, finish: pyqtSlot, workpath: QDir):
        p = QProcess()
        p.setProcessEnvironment(QProcessEnvironment.systemEnvironment())
        p.setProcessChannelMode(QProcess.MergedChannels)
        p.setWorkingDirectory(workpath.absolutePath())
        if cmd is not None:
            p.setProgram(cmd)
        if finish is not None:
            p.finished.connect(finish)
        if cmd is not None and autostart:
            p.start()
        return p

    @pyqtSlot()
    def cleanup(self):
        pass


class Tools(Enum):
    DOWNLOAD = BaiduDoc.get_path('bin/dl-baidu-swf{}'.format('.exe' if sys.platform == 'win32' else ''))
    RENDER = BaiduDoc.get_path('bin/swfrender{}'.format('.exe' if sys.platform == 'win32' else ''))
    CONVERT = BaiduDoc.get_path('bin/convert{}'.format('.exe' if sys.platform == 'win32' else ''))


def main():
    app = QApplication(sys.argv)
    baidu = BaiduDoc()
    baidu.show()
    app.setApplicationName('BaiduGrabber')
    app.setApplicationVersion('1.0')
    app.aboutToQuit.connect(baidu.cleanup)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()