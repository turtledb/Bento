import os

from bento.distutils.utils \
    import \
        _is_setuptools_activated
if _is_setuptools_activated():
    from setuptools.command.bdist_egg \
        import \
            bdist_egg as old_bdist_egg
else:
    raise ValueError("You cannot use bdist_egg without setuptools enabled first")

class bdist_egg(old_bdist_egg):
    cmd_name = "build_egg"
    def run(self):
        self.distribution.run_command_in_context(self.cmd_name, [])
