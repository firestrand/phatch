from multiprocessing import freeze_support

from phatch.entrypoints import gui_main


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(gui_main())
