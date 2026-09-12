from multiprocessing import freeze_support

from phatch.entrypoints import console_main


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(console_main())
