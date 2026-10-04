"""Compose the UI and robot controller. Run: python Main.py"""
from crawler_ui import CrawlerUI
from crawler_controller import CrawlerController


class Application:
    def __init__(self):
        self.ui = CrawlerUI()
        try:
            self.controller = CrawlerController(self.ui, robot_count=1)
        except Exception as error:
            self.ui.error("Startup error", str(error))
            self.ui.close()
            raise

    def start(self):
        self.controller.start()
        self.ui.start()


def CrawlerRun():
    Application().start()


if __name__ == '__main__':
    CrawlerRun()
