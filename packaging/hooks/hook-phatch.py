from PyInstaller.utils.hooks import collect_submodules


hiddenimports = (
    collect_submodules("phatch.actions")
    + collect_submodules("phatch.core")
    + collect_submodules("phatch.data")
    + collect_submodules("phatch.lib")
    + collect_submodules("phatch.other")
    + collect_submodules("phatch.services")
    + collect_submodules("phatch.pyWx")
)
