import os
import shutil
import unittest
import tempfile

from bento.core \
    import \
        PackageDescription, PackageOptions
from bento.core.errors \
    import \
        InvalidPackage
from bento.core.node \
    import \
        create_root_with_source_tree
from bento.core.node_package \
    import \
        NodeRepresentation
from bento.commands.hooks \
    import \
        create_hook_module, find_pre_hooks
from bento.commands.context \
    import \
        ConfigureYakuContext

from bento.core.testing \
    import \
        create_fake_package_from_bento_infos
from bento.commands.tests.utils \
    import \
        prepare_configure

def comparable_representation(top_node, node_pkg):
    """Return a dictionary representing the node_pkg to be used for
    comparison."""
    d = {"packages": {}, "extensions": {}}
    for k, v in node_pkg.iter_category("extensions"):
        d["extensions"][k] = v.extension_from(top_node)
    for k, v in node_pkg.iter_category("packages"):
        d["packages"][k] = v
    return d

class TestRecurseBase(unittest.TestCase):
    def setUp(self):
        self.old_dir = os.getcwd()

        self.d = tempfile.mkdtemp()
        self.root = create_root_with_source_tree(self.d, os.path.join(self.d, "build"))
        self.run_node = self.root.find_node(self.d)
        self.top_node = self.run_node

        os.chdir(self.d)

    def tearDown(self):
        os.chdir(self.old_dir)
        shutil.rmtree(self.d)

    def _create_package_and_reference(self, bento_info, r_bento_info):
        pkg = PackageDescription.from_string(bento_info)
        node_pkg = NodeRepresentation(self.run_node, self.top_node)
        node_pkg.update_package(pkg)

        r_pkg = PackageDescription.from_string(r_bento_info)
        r_node_pkg = NodeRepresentation(self.run_node, self.top_node)
        r_node_pkg.update_package(r_pkg)

        return node_pkg, r_node_pkg

    def test_py_packages(self):
        run_node = self.run_node

        bento_info = """\
Name: foo

Recurse: bar

Library:
    Packages: bar
"""
        sub_bento_info = """\
Library:
    Packages: foo
"""

        r_bento_info = """\
Name: foo

Library:
    Packages: bar, bar.foo
"""

        bentos = {"bento.info": bento_info,
                  "bar/bento.info": sub_bento_info}
        create_fake_package_from_bento_infos(run_node, bentos)

        node_pkg, r_node_pkg = self._create_package_and_reference(bento_info, r_bento_info)
        self.assertEqual(node_pkg.iter_category("packages"), r_node_pkg.iter_category("packages"))

    def test_basics(self):
        run_node = self.run_node

        bento_info = """\
Name: foo

Recurse:
    bar
"""
        bento_info2 = """\
Recurse:
    foo

Library:
    Extension: _foo
        Sources: foo.c
    CompiledLibrary: _bar
        Sources: foo.c
"""

        bento_info3 = """\
Library:
    Packages: sub2
"""
        bentos = {"bento.info": bento_info, os.path.join("bar", "bento.info"): bento_info2,
                  os.path.join("bar", "foo", "bento.info"): bento_info3}
        create_fake_package_from_bento_infos(run_node, bentos)

        r_bento_info = """\
Name: foo

Library:
    Packages:
        bar.foo.sub2
    Extension: bar._foo
        Sources: bar/foo.c
    CompiledLibrary: bar._bar
        Sources: bar/foo.c
"""

        node_pkg, r_node_pkg = self._create_package_and_reference(bento_info, r_bento_info)

        self.assertEqual(comparable_representation(self.top_node, node_pkg),
                         comparable_representation(self.top_node, r_node_pkg))

    def test_py_module_invalid(self):
        """Ensure we get a package error when defining py modules in recursed
        bento.info."""
        bento_info = """\
Name: foo

Recurse: bar
"""
        sub_bento_info = """\
Library:
    Modules: foo
"""
        bentos = {"bento.info": bento_info,
                  os.path.join("bar", "bento.info"): sub_bento_info}
        self.assertRaises(InvalidPackage,
                          lambda: create_fake_package_from_bento_infos(self.run_node, bentos))

    def test_hook(self):
        root = self.root
        top_node = self.top_node

        bento_info = """\
Name: foo

HookFile:
    bar/bscript

Recurse:
    bar
"""
        bento_info2 = """\
Library:
    Packages: fubar
"""

        bscript = """\
from bento.commands import hooks
@hooks.pre_configure
def configure(ctx):
    packages = ctx.local_pkg.packages
    ctx.local_node.make_node("test").write(str(packages))
"""
        bentos = {"bento.info": bento_info, os.path.join("bar", "bento.info"): bento_info2}
        bscripts = {os.path.join("bar", "bscript"): bscript}
        create_fake_package_from_bento_infos(top_node, bentos, bscripts)

        conf, configure = prepare_configure(self.run_node, bento_info, ConfigureYakuContext)

        hook = top_node.search("bar/bscript")
        m = create_hook_module(hook.abspath())
        for hook in find_pre_hooks([m], "configure"):
            conf.pre_recurse(root.find_dir(hook.local_dir))
            try:
                hook(conf)
            finally:
                conf.post_recurse()

        test = top_node.search("bar/test")
        if test:
            self.failUnlessEqual(test.read(), "['fubar']")
        else:
            self.fail("test dummy not found")
