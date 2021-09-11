from PyQt5.QtCore import pyqtSignal, pyqtSlot, QThread
from PyQt5.QtWidgets import QAbstractItemView, QLabel, QListWidget, QLineEdit, QDialog, QPushButton, QHBoxLayout, QVBoxLayout, QApplication
import youtube_dl
import os
import shutil
import ffmpeg
import glob

target_url = ""

class MyMainGUI(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.search_button = QPushButton("검색")
        self.search_url = QLineEdit(self)
        self.video_list = QListWidget(self)

        self.status_label = QLabel("", self)

        self.download_button = QPushButton("다운로드")

        hbox = QHBoxLayout()
        hbox.addStretch(0)
        hbox.addWidget(self.search_url)
        hbox.addWidget(self.search_button)
        hbox.addStretch(0)

        hbox2 = QHBoxLayout()
        hbox2.addWidget(self.video_list)

        hbox3 = QHBoxLayout()
        hbox3.addWidget(self.download_button)

        vbox = QVBoxLayout()
        vbox.addStretch(1)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        vbox.addLayout(hbox2)
        vbox.addStretch(1)
        vbox.addLayout(hbox3)
        vbox.addStretch(1)
        vbox.addWidget(self.status_label)

        self.setLayout(vbox)

        self.setWindowTitle('PyConverter2')
        self.setGeometry(300, 300, 500, 300)


class MyMain(MyMainGUI):
    add_sec_signal = pyqtSignal()
    send_instance_singal = pyqtSignal("PyQt_PyObject")

    def __init__(self, parent=None):
        super().__init__(parent)

        self.search_button.clicked.connect(self.search)
        self.download_button.clicked.connect(self.download)
        self.video_list.setSelectionMode(QAbstractItemView.MultiSelection)

        self.search_url.textChanged[str].connect(self.title_update)
        self.video_list.itemClicked.connect(self.chkItemClicked)
        self.video_list.itemSelectionChanged.connect(self.chkItemClicked)

        self.th_search = searcher(parent=self)
        self.th_search.updated_list.connect(self.list_update)
        self.th_search.updated_label.connect(self.status_update)

        self.th_download = downloader(parent=self)
        self.th_download.updated_label.connect(self.status_update)

        self.show()
    
    def title_update(self, input):
        global target_url
        target_url = input
    
    def chkItemClicked(self):
        global selected_title
        selected_title = self.video_list.selectedItems()


    @pyqtSlot()
    def search(self):
        self.video_list.clear()
        self.th_search.start()

    @pyqtSlot()
    def download(self):
        self.th_download.start()

    @pyqtSlot(str)
    def list_update(self, msg):
        self.video_list.addItem(msg)
        self.video_list.selectAll()
    
    @pyqtSlot(str)
    def status_update(self, msg):
        self.status_label.setText(msg)


class searcher(QThread):
    updated_list = pyqtSignal(str)
    updated_label = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__()
        self.main = parent

    def __del__(self):
        self.wait()

    def run(self):

        global target_url
        global down_url_list
        global down_title_list

        down_url_list = []
        down_title_list = []
        
        if target_url != "":
            self.updated_label.emit("동영상 목록 읽는 중 ...")

            ydl_opts = {'format': 'bestaudio/best'}

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(target_url, download=False)

                if 'entries' in info_dict:
                    video = info_dict['entries']

                    for i, _ in enumerate(video):
                        video = info_dict['entries'][i]
                        self.updated_list.emit(info_dict['entries'][i]['title'])

                        down_url_list.append(info_dict['entries'][i]['webpage_url'])
                        down_title_list.append(info_dict['entries'][i]['title'])
                
                else:
                    video_title = info_dict.get('title', None)
                    self.updated_list.emit(video_title)

                    down_url_list.append(target_url)
                    down_title_list.append(video_title)

            self.updated_label.emit("불러오기 완료!")
        
        else:
            self.updated_label.emit("URL을 입력하세요")


class downloader(QThread):
    updated_label = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__()
        self.main = parent

    def __del__(self):
        self.wait()

    def run(self):
        global down_url_list
        global down_title_list
        global selected_title

        titles = []
        
        for x in range(len(selected_title)):
            titles.append(selected_title[x].text())

        cnt = 0

        for i, url in enumerate(down_url_list):
            if down_title_list[i] in titles:
                cnt += 1
                self.updated_label.emit("{}/{} 동영상 파일 다운로드 중 ...".format(cnt, len(titles)))

                output_dir = os.path.join('./', '%(title)s.%(ext)s')

                ydl_opt_audio = {
                    'outtmpl': output_dir,
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }

                with youtube_dl.YoutubeDL(ydl_opt_audio) as ydl:
                    ydl.download([url])

                ydl_opt_video = {
                    'outtmpl': output_dir,
                    'format': 'bestvideo/best',
                }

                with youtube_dl.YoutubeDL(ydl_opt_video) as ydl:
                    ydl.download([url])
                
                if len(glob.glob("./*.webm")) > 0:
                    video_name = (glob.glob("./*.webm"))[0]
                    os.rename((glob.glob("./*.webm"))[0], video_name.replace(".webm", ".mp4"))
                
                video_name = (glob.glob("./*.mp4"))[0]
                os.rename((glob.glob("./*.mp4"))[0], "input.mp4")
                os.rename((glob.glob("./*.mp3"))[0], "input.mp3")

                input_video = ffmpeg.input("input.mp4")
                input_audio = ffmpeg.input("input.mp3")

                ffmpeg.output(
                    input_video,
                    input_audio,
                    'output.mp4',
                    vcodec='copy',
                    acodec='copy',
                ).run()
                
                os.remove("input.mp4")
                os.remove("input.mp3")

                os.rename("output.mp4", video_name)

                if not os.path.exists("./변환된 파일"):
                    os.makedirs("./변환된 파일")

                shutil.move(video_name, "./변환된 파일/" + video_name)

        self.updated_label.emit("변환 완료!")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    form = MyMain()
    app.exec_()