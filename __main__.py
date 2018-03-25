#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import signal
import sip
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
        self.urlcount, self.swfcount, self.completecount = 0, [], 0
        self.overlay, self.progress, self.progresslabel = None, None, None
        # self.outdir = QDir(QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
        self.buttonwidget = QWidget(self)
        self.buttonwidget.setVisible(False)
        self.openbutton, self.continuebutton = QPushButton('Open Folder', self), QPushButton('Continue', self)
        self.outdir = QDir('/home/ozmartian/Temp/_docs')
        self.procs = Munch(download=[], render=[], convert=[])
        self.work_folders = []
        self.setWindowTitle('Baidu Docs Grabber')
        self.setWindowIcon(QIcon(self.get_path('images/icon.png')))
        self.input_links = QTextEdit(self)
        self.input_links.setStyleSheet('''QTextEdit {
            background: #FFF url(images/watermark.png) no-repeat center center;
            font-family: "Microsoft YaHei", sans-serif;
            font-size: 10pt;
        }''')
        self.input_links.setAcceptRichText(False)
        self.input_links.setPlaceholderText('copy & paste one or more Baidu Docs page links here')
        self.input_links.setWordWrapMode(QTextOption.NoWrap)
        self.input_links.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.input_links.ensureCursorVisible()
        self.input_links.setAutoFormatting(QTextEdit.AutoNone)
        self.input_buttons = QDialogButtonBox(QDialogButtonBox.SaveAll | QDialogButtonBox.Reset, self)
        self.input_buttons.clicked.connect(self.handle_actions)
        logolabel = QLabel('<img src="images/logo.png" />')
        bottomlayout = QHBoxLayout()
        bottomlayout.setContentsMargins(0, 0, 0, 0)
        bottomlayout.addWidget(logolabel)
        bottomlayout.addStretch(1)
        bottomlayout.addWidget(self.input_buttons)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 8)
        layout.addWidget(self.input_links)
        layout.addLayout(bottomlayout)
        self.setLayout(layout)
        self.setMinimumSize(600, 400)
        # FOR TESTING
        self.input_links.setText('''https://wenku.baidu.com/view/7d31c296dd88d0d233d46ad8.html?sxts=1521450475781
https://wenku.baidu.com/view/44a0c50aba1aa8114431d979.html?from=search
https://wenku.baidu.com/view/5c4aa3716c85ec3a87c2c5f2.html?from=search''')

    @pyqtSlot(QAbstractButton)
    def handle_actions(self, button: QAbstractButton):
        if self.input_buttons.buttonRole(button) == QDialogButtonBox.AcceptRole:
            self.format_links()
        elif self.input_buttons.buttonRole(button) == QDialogButtonBox.ResetRole:
            self.input_links.clear()

    @pyqtSlot()
    def format_links(self):
        links = self.input_links.toPlainText().split('\n')
        links = [x for x in links if x.strip()]
        if len(links):
            self.download_swfs(links)

    def download_swfs(self, urls: list):
        self.urlcount = len(urls)
        if not self.urlcount:
            return
        savepath = QFileDialog.getExistingDirectory(self, 'Select a folder to save your documents',
                                                    self.outdir.absolutePath())
        if savepath:
            self.show_progress('Downloading pages from Baidu...')
            self.outdir = QDir(savepath)
            for url in urls:
                index = urls.index(url)
                swf_link = QUrl.fromUserInput(url)
                if swf_link.isValid():
                    self.work_folders.append(os.path.join(self.outdir.absolutePath(), '{0:03}'.format(index)))
                    os.makedirs(self.work_folders[index], exist_ok=True)
                    cmd = '{0} {1}'.format(Tools.DOWNLOAD.value, url)
                    self.procs.download.append(self.init_proc(cmd, self.work_folders[index], self.monitor_downloads))

    @pyqtSlot(int, QProcess.ExitStatus)
    def monitor_downloads(self, code: int, status: QProcess.ExitStatus):
        if code == 0 and status == QProcess.NormalExit:
            self.completecount += 1
            if self.completecount == self.urlcount:
                self.render_pngs()

    def render_pngs(self):
        self.update_progress('Converting pages to PNG images...', 2)
        for folder in self.work_folders:
            swfs = QDir(folder).entryList(['*.swf'])
            self.swfcount.append({'folder': folder, 'total': len(swfs), 'complete': 0})
            for swf in swfs:
                cmd = '{0} -r 240 {2} -o {3]'.format(Tools.RENDER.value, swf, swf.replace('.swf', '.png'))
                self.procs.render.append(self.init_proc(cmd, folder, self.convert))

    @pyqtSlot(int, QProcess.ExitStatus)
    def convert(self, code: int, status: QProcess.ExitStatus):
        if code == 0 and status == QProcess.NormalExit:
            folderswfs = [x for x in self.swfcount if x['folder'] == self.sender().workingDirectory()][0]
            folderswfs['complete'] += 1
            completed = [x for x in self.swfcount if x['complete'] == x['total']]
            if len(completed) == len(self.swfcount):
                self.update_progress('Merging pages into PDF documents...', 3)
                self.completecount = 0
                for folder in self.work_folders:
                    filename = os.path.join(self.outdir.absolutePath(), '{}.pdf'.format(QDir(folder).dirName()))
                    cmd = '{0} -adjoin {1} {2}'.format(Tools.CONVERT.value, '{}/*.png'.format(folder), filename)
                    self.procs.convert.append(self.init_proc(cmd, folder, self.complete))

    @pyqtSlot(int, QProcess.ExitStatus)
    def complete(self, code: int, status: QProcess.ExitStatus):
        if code == 0 and status == QProcess.NormalExit:
            self.completecount += 1
            if self.completecount == len(self.work_folders):
                self.update_progress('Processing complete...', 4)
                self.buttonwidget.setVisible(True)
                self.cleanup()

    def show_progress(self, msg: str):
        if self.overlay is not None:
            sip.delete(self.overlay)
            del self.overlay
        self.overlay = QDialog(self, Qt.Popup)
        self.progress = QProgressBar(self)
        self.progress.setStyle(QStyleFactory.create('Fusion'))
        self.progress.setTextVisible(True)
        self.progress.setRange(0, 4)
        self.progress.setValue(1)
        self.progresslabel = QLabel(msg, self)
        self.progresslabel.setStyleSheet('''
        QLabel {
            font-weight: bold;
            font-size: 11pt;
            text-align: center;
            color: #222;
        }''')
        self.openbutton.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.outdir.absolutePath())))
        self.continuebutton.clicked.connect(self.close_progress)
        buttonlayout = QHBoxLayout()
        buttonlayout.addStretch(1)
        buttonlayout.addWidget(self.openbutton)
        buttonlayout.addWidget(self.continuebutton)
        buttonlayout.addStretch(1)
        self.buttonwidget.setLayout(buttonlayout)
        self.buttonwidget.setVisible(False)
        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(self.progresslabel, Qt.AlignHCenter)
        layout.addWidget(self.progress)
        layout.addWidget(self.buttonwidget)
        layout.addStretch(1)
        self.overlay.setGeometry(self.geometry())
        self.overlay.setStyleSheet('background-color: #FFF;')
        self.overlay.setWindowOpacity(0.75)
        self.overlay.setLayout(layout)
        self.overlay.show()

    def update_progress(self, msg: str, step: int):
        self.progress.setValue(step)
        self.progresslabel.setText(msg)
        if self.progress.value() == self.progress.maximum():
            self.buttonwidget.setVisible(True)

    def close_progress(self):
        self.progress.hide()
        self.overlay.hide()
        self.progress = None
        self.overlay.deleteLater()

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

    def init_proc(self, cmd: str, workpath: str, finish: pyqtSlot = None):
        if not os.path.exists(workpath):
            self.handle_error('Invalid work path', 'An invalid working path was passed to QProcess:\n\n{}'
                              .format(workpath))
            return
        p = QProcess(self)
        p.setProcessEnvironment(QProcessEnvironment.systemEnvironment())
        p.setProcessChannelMode(QProcess.MergedChannels)
        p.setWorkingDirectory(workpath)
        if finish is not None:
            p.finished.connect(finish)
        p.start(cmd)
        return p

    @pyqtSlot()
    def cleanup(self):
        [shutil.rmtree(folder) for folder in self.work_folders]
        self.work_folders.clear()


class Tools(Enum):
    DOWNLOAD = BaiduDoc.get_path('bin/{0}/dl-baidu-swf{1}'
                                 .format(sys.platform, '.exe' if sys.platform == 'win32' else ''))
    RENDER = BaiduDoc.get_path('bin/{0}/swfrender{1}'
                               .format(sys.platform, '.exe' if sys.platform == 'win32' else ''))
    CONVERT = BaiduDoc.get_path('bin/{0}/convert{1}'
                                .format(sys.platform, '.exe' if sys.platform == 'win32' else ''))


def main():
    app = QApplication(sys.argv)
    if not sys.platform.startswith('linux'):
        app.setStyle('Fusion')
    baidu = BaiduDoc()
    baidu.show()
    app.setApplicationName('BaiduGrabber')
    app.setApplicationVersion('1.0')
    app.aboutToQuit.connect(baidu.cleanup)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
