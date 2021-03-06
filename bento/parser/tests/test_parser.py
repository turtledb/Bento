from six.moves import cStringIO

from bento.errors \
    import \
        ParseError
from bento.utils.utils \
    import \
        extract_exception
from bento.parser.nodes \
    import \
        ast_pprint
from bento.parser.parser \
    import \
        parse

from bento.compat.api.moves import unittest

TestCase = unittest.TestCase

class _TestGrammar(TestCase):
    def _test(self, data, expected):
        s = cStringIO()

        p = parse(data)
        ast_pprint(p, string=s)

        try:
            self.assertEqual(s.getvalue(), expected)
        except AssertionError:
            msg = s.getvalue()
            msg += "\n%s" % str(expected)
            raise AssertionError("assertion error:\n%s" % msg)

class TestMeta(_TestGrammar):
    def test_meta_name(self):
        data = "Name: yo"
        expected = """\
Node(type='stmt_list'):
    Node(type='name', value='yo')\
"""

        self._test(data, expected)

    def test_meta_url(self):
        data = "Url: http://example.com"
        expected = """\
Node(type='stmt_list'):
    Node(type='url', value='http://example.com')\
"""

        self._test(data, expected)

    def test_recurse(self):
        data = "Recurse: foo, bar"
        expected = """\
Node(type='stmt_list'):
    Node(type='subento', value=['foo', 'bar'])\
"""

        self._test(data, expected)

    def test_meta_summary(self):
        data = "Summary: a few words of description."
        expected = """\
Node(type='stmt_list'):
    Node(type='summary', value='a few words of description.')"""

        self._test(data, expected)

    def test_meta_author(self):
        data = "Author: John Doe"
        expected = """\
Node(type='stmt_list'):
    Node(type='author', value='John Doe')"""

        self._test(data, expected)

    def test_meta_author_email(self):
        data = "AuthorEmail: john@doe.com"
        expected = """\
Node(type='stmt_list'):
    Node(type='author_email', value='john@doe.com')"""

        self._test(data, expected)

    def test_meta_maintainer_email(self):
        data = "MaintainerEmail: john@doe.com"
        expected = """\
Node(type='stmt_list'):
    Node(type='maintainer_email', value='john@doe.com')"""

        self._test(data, expected)

    def test_meta_maintainer(self):
        data = "Maintainer: John Doe"
        expected = """\
Node(type='stmt_list'):
    Node(type='maintainer', value='John Doe')"""

        self._test(data, expected)

    def test_meta_license(self):
        data = "License: BSD"
        expected = """\
Node(type='stmt_list'):
    Node(type='license', value='BSD')"""

        self._test(data, expected)

    def test_meta_version(self):
        data = "Version: 1.0"
        expected = """\
Node(type='stmt_list'):
    Node(type='version', value='1.0')\
"""

        self._test(data, expected)

    def test_meta_platforms(self):
        data = "Platforms: any"
        expected = """\
Node(type='stmt_list'):
    Node(type='platforms', value=['any'])"""

        self._test(data, expected)

    def test_meta_classifiers_single_line(self):
        data = "Classifiers: yo"
        expected = """\
Node(type='stmt_list'):
    Node(type='classifiers', value=['yo'])\
"""

        self._test(data, expected)

    def test_meta_classifiers_multi_lines(self):
        data = """\
Classifiers: yo,
    yeah
"""
        expected = """\
Node(type='stmt_list'):
    Node(type='classifiers', value=['yo', 'yeah'])\
"""

        self._test(data, expected)

    def test_meta_classifiers_indent_only(self):
        data = """\
Classifiers:
    yo1,
    yo2\
"""
        expected = """\
Node(type='stmt_list'):
    Node(type='classifiers', value=['yo1', 'yo2'])\
"""

        self._test(data, expected)

    def test_meta_classifiers_full(self):
        data = """\
Classifiers: yo1,
    yo2\
"""
        expected = """\
Node(type='stmt_list'):
    Node(type='classifiers', value=['yo1', 'yo2'])\
"""

        self._test(data, expected)

    def test_meta_stmts(self):
        data = """\
Name: yo
Summary: yeah\
"""
        expected = """\
Node(type='stmt_list'):
    Node(type='name', value='yo')
    Node(type='summary', value='yeah')"""

        self._test(data, expected)

    def test_empty(self):
        data = ""
        expected = "Node(type='stmt_list')"

        self._test(data, expected)

    def test_newline(self):
        data = "\n"
        expected = "Node(type='stmt_list')"

        self._test(data, expected)

    def test_description_single_line(self):
        data = "Description: some words."
        expected = """\
Node(type='stmt_list'):
    Node(type='description', value='some words.')"""

        self._test(data, expected)

    def test_description_simple_indent(self):
        data = """\
Description:
    some words."""
        expected = """\
Node(type='stmt_list'):
    Node(type='description', value='some words.')"""

        self._test(data, expected)

    def test_description_simple_indent_wse(self):
        "Test indented block with ws error."
        data = """\
Description:   
    some words."""
        expected = """\
Node(type='stmt_list'):
    Node(type='description', value='some words.')"""

        self._test(data, expected)

    def test_description_complex_indent(self):
        data = """\
Description:
    some
        indented
            words
    ."""

        description = """\
some
    indented
        words
."""
        expected = """\
Node(type='stmt_list'):
    Node(type='description', value=%r)""" % description

        self._test(data, expected)

class TestConditional(_TestGrammar):
    def test_not_bool(self):
        data = """\
Library:
    if not true:
        Modules: foo.py
"""
        expected = """\
Node(type='stmt_list'):
    Node(type='library'):
        Node(type='library_name', value='default')
        Node(type='library_stmts'):
            Node(type='conditional'):
                Node(type='library_stmts'):
                    Node(type='modules', value=['foo.py'])"""

        self._test(data, expected)

    def test_not_flag(self):
        data = """\
Flag: foo
    Default: true
    Description: yo mama

Library:
    if not flag(foo):
        Modules: foo.py
"""
        expected = """\
Node(type='stmt_list'):
    Node(type='flag'):
        Node(type='flag_declaration', value='foo')
        Node(type='flag_stmts'):
            Node(type='flag_default', value='true')
            Node(type='flag_description', value='yo mama')
    Node(type='library'):
        Node(type='library_name', value='default')
        Node(type='library_stmts'):
            Node(type='conditional'):
                Node(type='library_stmts'):
                    Node(type='modules', value=['foo.py'])"""

        self._test(data, expected)

class TestLibrary(_TestGrammar):
    def test_modules(self):
        data = """\
Library:
    Modules: foo.py
"""

        expected = """\
Node(type='stmt_list'):
    Node(type='library'):
        Node(type='library_name', value='default')
        Node(type='library_stmts'):
            Node(type='modules', value=['foo.py'])"""

        self._test(data, expected)

    def test_modules2(self):
        data = """\
Library:
    Modules: foo.py,
        bar.py,
        fubar.py
"""

        expected = """\
Node(type='stmt_list'):
    Node(type='library'):
        Node(type='library_name', value='default')
        Node(type='library_stmts'):
            Node(type='modules', value=['foo.py', 'bar.py', 'fubar.py'])"""

        self._test(data, expected)

    def test_modules3(self):
        data = """\
Library:
    Modules:
        bar.py,
        fubar.py
"""

        expected = """\
Node(type='stmt_list'):
    Node(type='library'):
        Node(type='library_name', value='default')
        Node(type='library_stmts'):
            Node(type='modules', value=['bar.py', 'fubar.py'])"""

        self._test(data, expected)

    def test_packages(self):
        data = """\
Library:
    Packages:
        foo, bar
"""

        expected = """\
Node(type='stmt_list'):
    Node(type='library'):
        Node(type='library_name', value='default')
        Node(type='library_stmts'):
            Node(type='packages', value=['foo', 'bar'])"""

        self._test(data, expected)

    def test_build_requires(self):
        data = """\
Library:
    BuildRequires:
        foo, bar
"""

        expected = """\
Node(type='stmt_list'):
    Node(type='library'):
        Node(type='library_name', value='default')
        Node(type='library_stmts'):
            Node(type='build_requires', value=['foo', 'bar'])"""

        self._test(data, expected)

    def test_build_requires2(self):
        data = """\
Library:
    BuildRequires:
        foo, bar
    BuildRequires: fubar
"""

        expected = """\
Node(type='stmt_list'):
    Node(type='library'):
        Node(type='library_name', value='default')
        Node(type='library_stmts'):
            Node(type='build_requires', value=['foo', 'bar'])
            Node(type='build_requires', value=['fubar'])"""

        self._test(data, expected)

    def test_subdir(self):
        data = """\
Library:
    SubDirectory: lib
"""

        expected = """\
Node(type='stmt_list'):
    Node(type='library'):
        Node(type='library_name', value='default')
        Node(type='library_stmts'):
            Node(type='sub_directory', value='lib')"""

        self._test(data, expected)

class TestExecutable(_TestGrammar):
    def test_simple(self):
        data = """\
Executable: foo
    Module: foo.bar
    Function: main
"""

        expected = """\
Node(type='stmt_list'):
    Node(type='executable'):
        Node(type='exec_name', value='foo')
        Node(type='exec_stmts'):
            Node(type='module', value='foo.bar')
            Node(type='function', value='main')"""

        self._test(data, expected)

class TestPath(_TestGrammar):
    def test_simple(self):
        data = """\
Path: foo
    Default: foo_default
    Description: foo_description
"""

        expected = """\
Node(type='stmt_list'):
    Node(type='path'):
        Node(type='path_declaration', value='foo')
        Node(type='path_stmts'):
            Node(type='path_default', value='foo_default')
            Node(type='path_description', value='foo_description')"""

        self._test(data, expected)

    def test_conditional(self):
        data = """\
Path: foo
    if true:
        Default: foo_default
    Description: foo_description
"""

        expected = """\
Node(type='stmt_list'):
    Node(type='path'):
        Node(type='path_declaration', value='foo')
        Node(type='path_stmts'):
            Node(type='conditional'):
                Node(type='path_stmts'):
                    Node(type='path_default', value='foo_default')
            Node(type='path_description', value='foo_description')"""

        self._test(data, expected)

class TestErrorHandling(TestCase):
    def test_invalid_keyword(self):
        data = """\
Library:
    Name: foo
"""

        try:
            parse(data)
            self.fail("parser did not raise expected ParseError")
        except ParseError:
            e = extract_exception()
            self.assertMultiLineEqual(e.msg, """\
yacc: Syntax error at line 2, Token(NAME_ID, 'Name')
    Name: foo
    ^""")

    def test_invalid_keyword_comment(self):
        """Check comments don't screw up line counting."""
        data = """\
# Some useless
# comments
Library:
    Name: foo
"""

        try:
            parse(data)
            self.fail("parser did not raise expected ParseError")
        except ParseError:
            e = extract_exception()
            self.assertMultiLineEqual(e.msg, """\
yacc: Syntax error at line 4, Token(NAME_ID, 'Name')
    Name: foo
    ^""")
