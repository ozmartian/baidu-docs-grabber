#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# baidu-grabber - convert and save Baidu Docs to PDF
#
# copyright © 2018 Pete Alexandrou
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#######################################################################

import os
import shutil
import signal
import sip
import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

# noinspection PyUnresolvedReferences
from baidugrabber import resources
from baidugrabber.munch import Munch
import baidugrabber

signal.signal(signal.SIGINT, signal.SIG_DFL)
signal.signal(signal.SIGTERM, signal.SIG_DFL)


#   LINKS FOR TESTING:
#
#   https://wenku.baidu.com/view/44a0c50aba1aa8114431d979.html
#   https://wenku.baidu.com/view/7d31c296dd88d0d233d46ad8.html
#   https://wenku.baidu.com/view/5c4aa3716c85ec3a87c2c5f2.html

class BaiduDoc(QWidget):
    def __init__(self, parent=None):
        super(BaiduDoc, self).__init__(parent)
        self.workspace, self.filename = None, None
        self.urlcount, self.completecount = 0, 0
        self.overlay, self.progress, self.progresslabel = None, None, None
        self.outdir = QDir(QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
        self.openbutton, self.continuebutton = None, None
        self.procs = Munch(download=[], render=[], convert=[], merge=[])
        self.work_folders, self.pdfs = [], []
        self.setWindowTitle('Baidu Docs Grabber')   
        qApp.setWindowIcon(QIcon(':images/icon.png'))
        self.input_links = QTextEdit(self)
        self.input_links.setStyleSheet('''QTextEdit {
            background: #FFF url(:images/watermark.png) no-repeat center center;
            font-family: "Microsoft YaHei", sans-serif;
            font-size: 10pt;
            color: #000;
        }''')
        self.input_links.setAcceptRichText(False)
        placeholder = 'copy & paste one or more Baidu Docs page links here\n\nexample:\n\n' \
                      'https://wenku.baidu.com/view/44a0c50aba1aa8114431d979.html\n' \
                      'https://wenku.baidu.com/view/5c4aa3716c85ec3a87c2c5f2.html'
        self.input_links.setPlaceholderText(placeholder)
        self.input_links.setWordWrapMode(QTextOption.NoWrap)
        self.input_links.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.input_links.ensureCursorVisible()
        self.input_links.setAutoFormatting(QTextEdit.AutoNone)
        clear_button = QPushButton('Clear', self)
        start_button = QPushButton('Start', self)
        start_button.setDefault(True)
        self.input_buttons = QDialogButtonBox(self)
        self.input_buttons.addButton(clear_button, QDialogButtonBox.ResetRole)
        self.input_buttons.addButton(start_button, QDialogButtonBox.AcceptRole)
        self.input_buttons.clicked.connect(self.handle_actions)
        logolabel = QLabel(self)
        logolabel.setPixmap(QPixmap(':images/logo.png'))
        bottomlayout = QHBoxLayout()
        bottomlayout.setContentsMargins(0, 0, 0, 0)
        bottomlayout.addWidget(logolabel)
        bottomlayout.addStretch(1)
        bottomlayout.addWidget(self.input_buttons)
        mainlayout = QVBoxLayout()
        mainlayout.setContentsMargins(10, 10, 10, 8)
        mainlayout.addWidget(self.input_links)
        mainlayout.addLayout(bottomlayout)
        mainwidget = QWidget(self)
        mainwidget.setLayout(mainlayout)
        self.stackedlayout = QStackedLayout()
        self.stackedlayout.setStackingMode(QStackedLayout.StackAll)
        self.stackedlayout.addWidget(mainwidget)
        self.setLayout(self.stackedlayout)
        self.setMinimumSize(600, 400)

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
        self.completecount = 0
        if not len(urls):
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
                    self.work_folders.append(os.path.join(self.outdir.absolutePath(), '{0:03}'.format(index + 1)))
                    os.makedirs(self.work_folders[index], exist_ok=True)
                    cmd = '{0} {1}'.format(Tools.DOWNLOAD, url)
                    self.procs.download.append(self.run_cmd(cmd, self.work_folders[index], self.monitor_downloads))

    @pyqtSlot(int, QProcess.ExitStatus)
    def monitor_downloads(self, code: int, status: QProcess.ExitStatus):
        if code == 0 and status == QProcess.NormalExit:
            completed = 0
            for proc in self.procs.download:
                if type(proc) is QProcess and proc.state() == QProcess.NotRunning:
                    proc.close()
                    completed += 1
            if completed == len(self.procs.download):
                self.procs.download.clear()
                self.render_pngs()

    def render_pngs(self):
        self.update_progress('Rendering pages to image files...', 2)
        self.rendercount, self.totalcount = 0, 0
        watcher = QFileSystemWatcher(self)
        watcher.directoryChanged.connect(self.render_progress)
        for folder in self.work_folders:
            self.totalcount += len(QDir(folder).entryList(['*.swf']))
            watcher.addPath(folder)
            if sys.platform == 'win32':
                cmd = 'cmd /c "for %f in (*.swf) do ( {} -r 240 \"%f\" -o \"%~nf.png\" && '.format(Tools.RENDER)
                cmd += '{} -quiet \"%~nf.png\" \"%~nf.jpg\" )"'.format(Tools.CONVERT)
            else:
                cmd = Tools.RENDER
            self.procs.render.append(self.run_cmd(cmd, folder, self.monitor_render))

    @pyqtSlot(str)
    def render_progress(self, folder: str):
        if os.path.exists(folder):
            self.rendercount += 1
            self.update_progress('Rendering pages to image files... [{0:02d}/{1:02d}]'
                                 .format(self.rendercount, self.totalcount), 2)

    @pyqtSlot(int, QProcess.ExitStatus)
    def monitor_render(self, code: int, status: QProcess.ExitStatus):
        if code == 0 and status == QProcess.NormalExit:
            completed = 0
            for proc in self.procs.render:
                if type(proc) is QProcess and proc.state() == QProcess.NotRunning:
                    proc.close()
                    completed += 1
            if completed == len(self.procs.render):
                self.procs.render.clear()
                # self.convert()
                self.merge()

    # def convert(self):
    #     self.update_progress('Converting images to JPG format...', 3)
    #     for folder in self.work_folders:
    #         if sys.platform == 'win32':
    #             cmd = 'cmd /c "for %d in (*.png) do {} \"%f\" \"%~nf.jpg\""'.format(Tools.CONVERT)
    #         else:
    #             cmd = Tools.CONVERT
    #         self.procs.convert.append(self.run_cmd(cmd, folder, self.complete))
    #
    # @pyqtSlot(int, QProcess.ExitStatus)
    # def monitor_convert(self, code: int, status: QProcess.ExitStatus):
    #     if code == 0 and status == QProcess.NormalExit:
    #         completed = 0
    #         for proc in self.procs.convert:
    #             if type(proc) is QProcess and proc.state() == QProcess.NotRunning:
    #                 proc.close()
    #                 completed += 1
    #         if completed == len(self.procs.convert):
    #             self.procs.convert.clear()
    #             self.merge()

    def merge(self):
        self.update_progress('Creating PDF documents...', 3)
        for folder in self.work_folders:
            pdffile = os.path.join(self.outdir.absolutePath(), '{}.pdf'.format(QDir(folder).dirName()))
            self.pdfs.append(pdffile)
            jpgs = ' '.join(QDir(folder).entryList(['*.jpg' if sys.platform == 'win32' else '*.png']))
            cmd = '{0} -o {1} {2}'.format(Tools.MERGE, pdffile, jpgs)
            self.procs.merge.append(self.run_cmd(cmd, folder, self.complete))

    @pyqtSlot(int, QProcess.ExitStatus)
    def complete(self, code: int, status: QProcess.ExitStatus):
        if code == 0 and status == QProcess.NormalExit:
            completed = 0
            for proc in self.procs.merge:
                if type(proc) is QProcess and proc.state() == QProcess.NotRunning:
                    proc.close()
                    completed += 1
            if completed == len(self.procs.merge):
                self.update_progress('COMPLETE! Your documents are ready...', 4)
                self.procs.merge.clear()
                self.cleanup()

    def show_progress(self, msg: str, steps: int=4):
        self.progress = BaiduProgressBar(msg, steps, self)
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 10, 50, 10)
        layout.addStretch(1)
        layout.addWidget(self.progress)
        layout.addStretch(1)
        self.overlay = QWidget(self)
        self.overlay.setObjectName('ov')
        self.overlay.setStyleSheet('QWidget#ov { border-image: url(:images/overlay.png) 0 0 0 0 stretch stretch; }')
        self.overlay.setLayout(layout)
        self.stackedlayout.addWidget(self.overlay)
        self.stackedlayout.setCurrentWidget(self.overlay)

    def update_progress(self, msg: str, step: int):
        self.progress.update(step, msg)
        if self.progress.value == self.progress.maximum:
            self.openbutton = QPushButton('Open Folder', self)
            self.openbutton.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.outdir.absolutePath())))
            self.continuebutton = QPushButton('Continue', self)
            self.continuebutton.clicked.connect(self.close_progress)
            buttonlayout = QHBoxLayout()
            buttonlayout.addStretch(1)
            buttonlayout.addWidget(self.openbutton)
            buttonlayout.addWidget(self.continuebutton)
            buttonlayout.addStretch(1)
            self.overlay.layout().insertSpacing(self.overlay.layout().count() - 1, 15)
            self.overlay.layout().insertLayout(self.overlay.layout().count() - 1, buttonlayout)

    def close_progress(self):
        self.overlay.hide()
        item = self.stackedlayout.takeAt(self.stackedlayout.count() - 1)
        sip.delete(self.overlay)
        del self.overlay
        sip.delete(item)
        del item

    def handle_error(self, title: str, msg: str):
        QMessageBox.critical(self, title, msg, QMessageBox.Ok)

    @staticmethod
    def get_path(path: str = None):
        if getattr(sys, 'frozen', False) and getattr(sys, '_MEIPASS', False):
            # noinspection PyProtectedMember, PyUnresolvedReferences
            prepath = sys._MEIPASS
        else:
            prepath = QDir.currentPath()
        if path is not None:
            return os.path.join(prepath, path)
        else:
            return prepath

    def run_cmd(self, cmd: str, workpath: str, finish: pyqtSlot):
        if not os.path.exists(workpath):
            self.handle_error('Invalid work path', 'An invalid working path was passed to QProcess:\n\n{}'
                              .format(workpath))
            return
        p = QProcess(self)
        p.setProcessEnvironment(QProcessEnvironment.systemEnvironment())
        p.setProcessChannelMode(QProcess.MergedChannels)
        p.setWorkingDirectory(workpath)
        p.finished.connect(finish)
        p.errorOccurred.connect(self.cmd_error)
        print('starting QProcess: {}'.format(cmd))
        p.start(cmd)
        return p

    @pyqtSlot()
    def cmd_error(self):
        self.handle_error('An error occurred', self.sender().errorString())

    @pyqtSlot()
    def cleanup(self):
        self.procs.download.clear()
        self.procs.render.clear()
        self.procs.convert.clear()
        self.procs.merge.clear()
        [shutil.rmtree(folder) for folder in self.work_folders]
        self.work_folders.clear()


class BaiduProgressBar(QWidget):
    def __init__(self, msg: str, steps: int, parent=None):
        super(BaiduProgressBar, self).__init__(parent)
        self.parent = parent
        self.setStyle(QStyleFactory.create('Fusion'))
        self.progresslabel = QLabel(msg, self)
        self.progresslabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.progresslabel.setAlignment(Qt.AlignHCenter)
        self.progresslabel.setStyleSheet('''
            QLabel {
                font-weight: bold;
                font-size: 11pt;
                text-align: center;
                color: #000;
            }
        ''')
        self.progresslabel.setText(msg)
        self.progressbar = QProgressBar(self)
        self.progressbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # palette = self.progressbar.palette()
        # palette.setColor(QPalette.Highlight, QColor(100, 44, 104))
        # self.progressbar.setPalette(palette)
        self.progressbar.setTextVisible(True)
        self.progressbar.setRange(0, steps)
        self.progressbar.setValue(1)
        layout = QVBoxLayout()
        layout.addWidget(self.progresslabel)
        layout.addWidget(self.progressbar)
        self.setLayout(layout)

    def update(self, value: int, msg: str):
        self.progressbar.setValue(value)
        self.progresslabel.setText(msg)
        qApp.processEvents()

    @property
    def value(self):
        return self.progressbar.value()

    @property
    def maximum(self):
        return self.progressbar.maximum()


Tools = Munch(
    DOWNLOAD=QDir.toNativeSeparators(
            BaiduDoc.get_path('bin/{0}/dl-baidu-swf{1}'.format(sys.platform, '.exe' if sys.platform == 'win32' else ''))),
    RENDER=QDir.toNativeSeparators(
            BaiduDoc.get_path('bin/{0}/swfrender{1}'.format(sys.platform, '.exe' if sys.platform == 'win32' else ''))),
    CONVERT=QDir.toNativeSeparators(
            BaiduDoc.get_path('bin/{0}/convert{1}'.format(sys.platform, '.exe' if sys.platform == 'win32' else ''))),
    MERGE=QDir.toNativeSeparators(
            BaiduDoc.get_path('bin/{0}/img2pdf{1}'.format(sys.platform, '.exe' if sys.platform == 'win32' else ''))))


def main():
    if not sys.platform.startswith('linux'):
        QApplication.setStyle('Fusion')
    app = QApplication(sys.argv)
    app.setApplicationName(baidugrabber.__appname__)
    app.setApplicationVersion(baidugrabber.__version__)
    app.setOrganizationDomain(baidugrabber.__domain__)
    app.setQuitOnLastWindowClosed(True)
    baidu = BaiduDoc()
    app.aboutToQuit.connect(baidu.cleanup)
    baidu.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
