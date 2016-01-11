import os
import sys
import time
import tempfile
import subprocess

from PyQt5 import QtWidgets, QtGui, QtCore

OUTPUT = os.path.join(tempfile.gettempdir(), "out.png")


class Window(QtWidgets.QDialog):
    def __init__(self, executable, image, parent=None):
        super(Window, self).__init__(parent)
        self.setWindowTitle("Blur")
        self.setMouseTracking(True)

        pixmap = QtGui.QPixmap(image)
        label = QtWidgets.QLabel()
        label.setPixmap(pixmap)
        label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(label)
        layout.setContentsMargins(50, 50, 50, 50)

        fps = QtWidgets.QLabel("0fps", self)

        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.setInterval(5)
        timer.timeout.connect(self.updatePixmap)

        self.image = image
        self.executable = executable
        self.fps = fps
        self.label = label
        self.timer = timer

        # Run-time properties
        self.kernelSize = 9
        self.radius = 2
        self.pos = [0, 0]
        self.size = 80

        # Application switches
        self.startPos = None
        self.pressed = False
        self.isRunning = False
        self.buffer = []

        self.setStyleSheet("""
            QDialog { background: #fff; }
            QLabel { font-size: 15pt; }
        """)

    def resizeEvent(self, event):
        self.fps.move(5, event.size().height() - 30)

    def mousePressEvent(self, event):
        """Provide for altering the influence area by press-drag"""
        self.startSize = self.size
        self.startPos = event.pos()
        self.pressed = True

    def mouseReleaseEvent(self, event):
        self.pressed = False

    def mouseMoveEvent(self, event):
        if self.isRunning:
            # While processing the next frame,
            # do not instantiate a new process
            # as it would overwrite the output
            # simultaneously, leading to bugs.
            return

        x = event.pos().x()
        y = event.pos().y()

        # Offset
        x -= self.size
        y -= self.size

        x = max(1, x)  # Clip left
        y = max(1, y)  # Clip top

        x = min(x, self.label.width() - self.size)  # Clip right
        y = min(y, self.label.width() - self.size)  # Clip bottom

        # Adjust area of influence
        if self.pressed:
            self.size = max(
                10, self.startSize + event.pos().y() - self.startPos.y())

        self.pos = [x, y]

        self.timer.start()

    def updatePixmap(self):
        """Perform computation by launching a subprocess"""
        self.isRunning = True
        startTime = time.time()

        try:
            with subprocess.Popen([self.executable,
                                   "-x", str(self.pos[0]),
                                   "-y", str(self.pos[1]),
                                   "-s", str(self.size),
                                   "-k", str(self.kernelSize),
                                   "-r", str(self.radius),
                                   "-o", OUTPUT,
                                   self.image],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  bufsize=1,
                                  universal_newlines=True) as popen:
                for line in popen.stdout:
                    self.buffer.append(line)

        except Exception as e:
            print("An exception occurred in blur executable: %s" % e)
            print("Last lines of output..")
            for line in self.buffer:
                sys.stderr.write(line)
            self.close()

        # Wait for process to finish.
        popen.wait()

        pixmap = QtGui.QPixmap(OUTPUT)
        self.label.setPixmap(pixmap)

        self.isRunning = False
        self.fps.setText("%.1f fps" % (1 / (time.time() - startTime)))

    def closeEvent(self, event):
        print("Cleaning up..")
        os.remove(OUTPUT)
        print("Shutting down..")


def show(executable, image, kernel=9, radius=4):
    """Launch the Qt application and who the GUI

    This is normally run via __main__.py

    Example:
        $ python -m blur blur.exe image.png

    """

    print("Launching GUI..")
    app = QtWidgets.QApplication(sys.argv)
    window = Window(executable, image)
    window.kernelSize = kernel
    window.radius = radius
    window.show()
    app.exec_()
