import sys
from importlib import abc, import_module, util

_LEGACY_PACKAGES = frozenset({"actions", "core", "data", "lib", "other"})


class _LegacyModuleLoader(abc.Loader):
    def __init__(self, canonical_name):
        self.canonical_name = canonical_name

    def exec_module(self, module):
        canonical_module = import_module(self.canonical_name)
        alias_metadata = {
            name: module.__dict__[name]
            for name in ("__loader__", "__name__", "__package__", "__spec__")
        }
        module.__dict__.update(canonical_module.__dict__)
        module.__dict__.update(alias_metadata)


class _LegacyModuleFinder(abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.partition(".")[0] not in _LEGACY_PACKAGES:
            return None
        canonical_name = f"phatch.{fullname}"
        canonical_spec = util.find_spec(canonical_name)
        if canonical_spec is None:
            return None
        return util.spec_from_loader(
            fullname,
            _LegacyModuleLoader(canonical_name),
            is_package=canonical_spec.submodule_search_locations is not None,
        )


sys.meta_path.insert(0, _LegacyModuleFinder())
