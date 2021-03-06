import re

from ply.lex \
    import \
        lex, LexToken

from bento.errors \
    import \
        ParseError, InternalBentoError
from bento.parser.utils \
    import \
        Peeker, BackwardGenerator, count_lines

import six

word_fields = [
    ("AUTHOR_EMAIL_ID", r"AuthorEmail"),
    ("COMPILED_LIBRARY_ID", r"CompiledLibrary"),
    ("CONFIG_PY_ID", r"ConfigPy"),
    ("DATAFILES_ID", r"DataFiles"),
    ("DEFAULT_ID", r"Default"),
    ("DESCRIPTION_FROM_FILE_ID", r"DescriptionFromFile"),
    ("DOWNLOAD_URL_ID", r"DownloadUrl"),
    ("EXECUTABLE_ID", r"Executable"),
    ("FLAG_ID", r"Flag"),
    ("PATH_ID", r"Path"),
    ("FUNCTION_ID", r"Function"),
    ("LIBRARY_ID", r"Library"),
    ("MAINTAINER_EMAIL_ID", r"MaintainerEmail"),
    ("MODULE_ID", r"Module"),
    ("NAME_ID", r"Name"),
    ("SRCDIR_ID", r"SourceDir"),
    ("SUB_DIRECTORY_ID", r"SubDirectory"),
    ("TARGET_ID", r"TargetDir"),
    ("URL_ID", r"Url"),
    ("VERSION_ID", r"Version"),
]

line_fields = [
    ("AUTHOR_ID", r"Author"),
    ("LICENSE_ID", r"License"),
    ("MAINTAINER_ID", r"Maintainer"),
    ("SUMMARY_ID", r"Summary"),
]

comma_line_fields = [
    ("BUILD_REQUIRES_ID", r"BuildRequires"),
    ("CLASSIFIERS_ID", r"Classifiers"),
    ("INSTALL_REQUIRES_ID", r"InstallRequires"),
    ("PLATFORMS_ID", r"Platforms"),
]

comma_word_fields = [
    ("EXTENSION_ID", r"Extension"),
    ("EXTRA_SOURCE_FILES_ID", r"ExtraSourceFiles"),
    ("FILES_ID", r"Files"),
    ("HOOK_FILE_ID", r"HookFile"),
    ("INCLUDE_DIRS_ID", r"IncludeDirs"),
    ("KEYWORDS_ID", r"Keywords"),
    ("META_TEMPLATE_FILE_ID", r"MetaTemplateFile"),
    ("META_TEMPLATE_FILES_ID", r"MetaTemplateFiles"),
    ("MODULES_ID", r"Modules"),
    ("PACKAGES_ID", r"Packages"),
    ("RECURSE_ID", r"Recurse"),
    ("SOURCES_ID", r"Sources"),
    ("USE_BACKENDS_ID", r"UseBackends"),
]

multilines_fields = [
    ("DESCRIPTION_ID", r"Description"),
]

keyword_fields = word_fields + line_fields + comma_line_fields + comma_word_fields + multilines_fields
keyword_tokens = [k[0] for k in keyword_fields]

keyword_misc = dict([
        ('if', 'IF'),
        ('else', 'ELSE'),
        ('true', 'TRUE'),
        ('false', 'FALSE'),
        ('not', 'NOT_OP'),
        ('flag', 'FLAG_OP'),
        ('os', 'OS_OP'),
])
keyword_misc_tokens = keyword_misc.values()

tokens = ["COLON", "WS", "WORD", "NEWLINE", "STRING", "MULTILINES_STRING",
          "BLOCK_MULTILINES_STRING", "COMMA", "INDENT", "DEDENT", "LPAR",
          "RPAR", "BACKSLASH"] \
        + list(keyword_tokens) + list(keyword_misc_tokens)

states = [
        ("insidestring", "exclusive"),
        ("insideword", "exclusive"),
        # To be used for keywords that accept multiline values (description,
        # etc...)
        ("insidemstring", "exclusive"),
        ("insidemstringnotcontinued", "exclusive"),

        ("insidewcommalistfirstline", "inclusive"),
        ("insidewcommalist", "inclusive"),

        ("insidescommalistfirstline", "exclusive"),
        ("insidescommalist", "exclusive"),
]

ESCAPING_CHAR = {"BACKSLASH": True}

def t_NEWLINE(t):
    r"(\n|\r\n)"
    t.lexer.lineno += len(t.value)
    return t
NEWLINE_PATTERN = t_NEWLINE.__doc__

def t_BACKSLASH(t):
    r"\\"
    return t

def t_TAB(t):
    r"\t"
    raise SyntaxError("Tab not supported")

R_NEWLINE = re.compile(t_NEWLINE.__doc__)

t_WS = r" [ ]+"

def t_COLON(t):
    r":"
    return t

keywords_dict = dict((v, k) for k, v in keyword_fields)
keywords_dict.update(keyword_misc)
word_keywords = dict((k, v) for k, v in word_fields)
line_keywords = dict((k, v) for k, v in line_fields)
multilines_keywords = dict((k, v) for k, v in multilines_fields)
comma_line_keywords = dict((k, v) for k, v in comma_line_fields)
comma_word_keywords = dict((k, v) for k, v in comma_word_fields)

def t_FIELD(t):
    r"\w+(?=\s*:)"
    try:
        type = keywords_dict[t.value]
    except KeyError:
        raise ParseError("Unrecognized keyword: %r" % (t.value,), t)
    else:
        t.type = type
        if type in line_keywords:
            t_begin_insidestring(t)
        elif type in multilines_keywords:
            # FIXME: we differentiate between top Description (accepting multiline)
            # and description within flag block (where we cannot currently accept
            # multilines).
            if t.lexpos >= 1:
                if R_NEWLINE.match(t.lexer.lexdata[t.lexpos-1]):
                    t_begin_insidemstring(t)
                else:
                     t_begin_insidestring(t)
            else:
                t_begin_insidemstring(t)
        elif type in comma_line_keywords:
            t_begin_inside_scommalistfirstline(t)
        elif type in comma_word_keywords:
            t_begin_inside_wcommalistfirstline(t)
        else:
            t_begin_inside_word(t)
        return t

def t_COMMENT(t):
    r'[ ]*\#[^\r\n]*'
    pass

def t_WORD(t):
    r'[^\#^\s\\\(\)]+'
    if t.value in keyword_misc:
        t.type = keyword_misc[t.value]
    return t

t_LPAR = r"\("
t_RPAR = r"\)"

def t_begin_inside_word(t):
    r'start_insideword'
    t.lexer.begin('insideword')

def t_end_inside_word(t):
    r'start_insideword'
    t.lexer.begin('INITIAL')

def t_begin_insidestring(t):
    r'start_insidestring'
    t.lexer.begin('insidestring')

def t_end_insidestring(t):
    r'end_insidestring'
    t.lexer.begin('INITIAL')

def t_begin_insidemstring(t):
    r'start_insidemstring'
    t.lexer.begin('insidemstring')

def t_end_insidemstring(t):
    r'end_insidemstring'
    t.lexer.begin('INITIAL')

def t_begin_inside_mstringnotcontinued(t):
    r'start_inside_mstringnotcontinued'
    t.lexer.begin("insidemstringnotcontinued")

def t_end_inside_mstringnotcontinued(t):
    r'end_inside_mstringnotcontinued'
    t.lexer.begin("INITIAL")

# Word comma list
def t_begin_inside_wcommalist(t):
    r'start_inside_wcommalist'
    t.lexer.begin('insidewcommalist')

def t_end_inside_wcommalist(t):
    r'end_inside_wcommalist'
    t.lexer.begin('INITIAL')

def t_begin_inside_wcommalistfirstline(t):
    r'start_inside_wcommalistfirstline'
    t.lexer.begin('insidewcommalistfirstline')

def t_end_inside_wcommalistfirstline(t):
    r'end_inside_wcommalistfirstline'
    t.lexer.begin('INITIAL')

# string comma list
def t_begin_inside_scommalist(t):
    r'start_inside_commalistw'
    t.lexer.begin('insidescommalist')

def t_end_inside_scommalist(t):
    r'end_inside_commalistw'
    t.lexer.begin('INITIAL')

def t_begin_inside_scommalistfirstline(t):
    r'start_inside_scommalistfirstline'
    t.lexer.begin('insidescommalistfirstline')

def t_end_inside_scommalistfirstline(t):
    r'end_inside_scommalistfirstline'
    t.lexer.begin('INITIAL')

#------------
# Inside word
#------------
def t_insideword_NEWLINE(t):
    t.lexer.lineno += len(t.value)
    t_end_inside_word(t)
    return t
t_insideword_NEWLINE.__doc__ = NEWLINE_PATTERN

def t_insideword_COLON(t):
    return t
t_insideword_COLON.__doc__ = t_COLON.__doc__

def t_insideword_WS(t):
    return t
t_insideword_WS.__doc__ = t_WS

def t_insideword_WORD(t):
    return t
t_insideword_WORD.__doc__ = t_WORD.__doc__

t_insideword_COMMENT = t_COMMENT

#-------------------------------
# Inside single line string rule
#-------------------------------
def t_insidestring_newline(t):
    t.lexer.lineno += len(t.value)
    t.type = "NEWLINE"
    t_end_insidestring(t)
    return t
t_insidestring_newline.__doc__ = NEWLINE_PATTERN

def t_insidestring_COLON(t):
    r':'
    return t

def t_insidestring_WS(t):
    r' [ ]+'
    return t

def t_insidestring_STRING(t):
    r'[^\\\r\n]+'
    t_end_insidestring(t)
    return t

#-----------------------
# multiline string rules
#-----------------------
def t_insidemstring_COLON(t):
    r':(?=.*\S+.*)'
    return t

def t_insidemstring_COLON_NO_CONTINUED(t):
    r':(?!.*\S.*)'
    t.type = "COLON"
    t_begin_inside_mstringnotcontinued(t)
    return t

def t_insidemstring_WS(t):
    r'[ ]+'
    return t

def t_insidemstring_NEWLINE(t):
    t.lexer.lineno += len(t.value)
    return t
t_insidemstring_NEWLINE.__doc__ = t_NEWLINE.__doc__

def t_insidemstring_MULTILINES_STRING(t):
    r'.+((\n[ ]+.+$)|(\n^[ ]*$))*'
    t.lexer.lineno += count_lines(t.value) - 1
    t_end_inside_mstringnotcontinued(t)
    return t

# Multiline string that starts on same line as Description
def t_insidemstringnotcontinued_NEWLINE(t):
    return t
t_insidemstringnotcontinued_NEWLINE.__doc__ = t_NEWLINE.__doc__

def t_insidemstringnotcontinued_WS(t):
    return t
t_insidemstringnotcontinued_WS.__doc__ = t_WS

def t_insidemstringnotcontinued_BLOCK_MULTILINES_STRING(t):
    r'.+((\n[ ]+.+$)|(\n^[ ]*$))*'
    t_end_inside_mstringnotcontinued(t)
    return t

#------------------------
# inside comma word list rules
#------------------------
def t_insidewcommalistfirstline_COLON(t):
    r":"
    return t

def t_insidewcommalistfirstline_WS(t):
    r' [ ]+'
    return t

def t_insidewcommalistfirstline_WORD(t):
    r'[^,\#^\s\\\(\)]+(?=,)'
    t_begin_inside_wcommalist(t)
    return t

def t_insidewcommalistfirstline_WORD_STOP(t):
    r'[^\#,\s\\\(\)]+(?!,)'
    t.type = "WORD"
    t_end_inside_wcommalistfirstline(t)
    return t

def t_insidewcommalistfirstline_NEWLINE(t):
    t.lexer.lineno += len(t.value)
    return t
t_insidewcommalistfirstline_NEWLINE.__doc__ = NEWLINE_PATTERN

def t_insidewcommalistfirstline_COMMA(t):
    r','
    return t

def t_insidewcommalist_WORD(t):
    r'[^,\s]+(?=,)'
    return t

def t_insidewcommalist_WORD_STOP(t):
    r'[^,\s]+(?!,)'
    t.type = "WORD"
    t_end_inside_wcommalist(t)
    return t

def t_insidewcommalist_NEWLINE(t):
    t.lexer.lineno += len(t.value)
    return t
t_insidewcommalist_NEWLINE.__doc__ = NEWLINE_PATTERN

def t_insidewcommalist_WS(t):
    r' [ ]+'
    return t

def t_insidewcommalist_COMMA(t):
    r','
    return t

#------------------
# comma list string
#------------------
def t_insidescommalistfirstline_COLON(t):
    r":"
    return t

def t_insidescommalistfirstline_WS(t):
    r' [ ]+'
    return t

def t_insidescommalistfirstline_STRING(t):
    r'[^,\n(\r\n)]+(?=,)'
    t_begin_inside_scommalist(t)
    return t

def t_insidescommalistfirstline_STRING_STOP(t):
    r'[^,\n(\r\n)]+(?!,)'
    t.type = "STRING"
    t_end_inside_scommalistfirstline(t)
    return t

def t_insidescommalistfirstline_NEWLINE(t):
    t.lexer.lineno += len(t.value)
    return t
t_insidescommalistfirstline_NEWLINE.__doc__ = NEWLINE_PATTERN

def t_insidescommalistfirstline_COMMA(t):
    r','
    return t

def t_insidescommalist_WS(t):
    r' [ ]+'
    return t

def t_insidescommalist_STRING(t):
    r'[^,\n(\r\n)]+(?=,)'
    return t

def t_insidescommalist_STRING_STOP(t):
    r'[^,\n(\r\n)]+(?!,)'
    t.type = "STRING"
    t_end_inside_scommalist(t)
    return t

def t_insidescommalist_NEWLINE(t):
    t.lexer.lineno += len(t.value)
    return t
t_insidescommalist_NEWLINE.__doc__ = NEWLINE_PATTERN

def t_insidescommalist_COMMA(t):
    r','
    return t

# Error handling rule
def t_error(t):
    raise ParseError("Illegal character '%s'" % t.value[0], t)

def t_insideword_error(t):
    raise ParseError("Illegal character (inside word state) '%s'" % t.value[0], t)

def t_insidestring_error(t):
    raise ParseError("Illegal character (insidestring state) '%s'" % t.value[0], t)

def t_insidemstring_error(t):
    raise ParseError("Illegal character (insidemstring state) '%s'" % t.value[0], t)

def t_insidemstringnotcontinued_error(t):
    raise ParseError("Illegal character (inside_mstringnotcontinued state) '%s'" % t.value[0], t)

def t_insidewcommalist_error(t):
    raise ParseError("Illegal character (inside wcommalist state) '%s'" % t.value[0], t)

def t_insidewcommalistfirstline_error(t):
    raise ParseError("Illegal character (inside wcommalistfirstline state) '%s'" % t.value[0], t)

def t_insidescommalist_error(t):
    raise ParseError("Illegal character (inside scommalist state) '%s'" % t.value[0], t)

def t_insidescommalistfirstline_error(t):
    raise ParseError("Illegal character (inside scommalistfirstline state) '%s'" % t.value[0], t)

#--------
# Filters
#--------
def detect_escaped(stream):
    """Post process the given stream (token iterator) to generate escaped
    character for characters preceded by the escaping token."""
    for t in stream:
        is_escaping_char = ESCAPING_CHAR.get(t.type, False)
        if is_escaping_char:
            try:
                t = six.advance_iterator(stream)
            except StopIteration:
                raise SyntaxError("EOF while escaping token %r (line %d)" %
                                  (t.value, t.lineno-1))
            t.escaped = True
        else:
            t.escaped = False
        yield t

def merge_escaped(stream):
    """Merge tokens whose escaped attribute is True together.

    Must be run after detect_escaped.

    Parameters
    ----------
    stream: iterator
    """
    stream = Peeker(stream, EOF)
    queue = []

    t = six.advance_iterator(stream)
    while t:
        if t.escaped:
            queue.append(t)
        else:
            if t.type == "WORD":
                if queue:
                    queue.append(t)
                    n = stream.peek()
                    if not n.escaped:
                        t.value = "".join([c.value for c in queue])
                        yield t
                        queue = []
                else:
                    n = stream.peek()
                    if n.escaped:
                        queue.append(t)
                    else:
                        yield t
            else:
                if queue:
                    queue[-1].value = "".join([c.value for c in queue])
                    queue[-1].type = "WORD"
                    yield queue[-1]
                    queue = []
                yield t
        try:
            t = six.advance_iterator(stream)
        except StopIteration:
            if queue:
                t.value = "".join([c.value for c in queue])
                t.type = "WORD"
                yield t
            return

def filter_ws_and_newline(stream):
    """Remove NEWLINE and WS tokens from the stream.

    Parameters
    ----------
    stream: iterator
        iterator of tokens."""
    for item in stream:
        if item.type not in ["NEWLINE", "WS"]:
            yield item

def remove_lines_indent(s, indent=None):
    lines = s.splitlines()
    if len(lines) > 1:
        if indent is None:
            indent = len(lines[1]) - len(lines[1].lstrip())
        for i in range(1, len(lines)):
            if len(lines[i]) >= indent:
                lines[i] = lines[i][indent:]
            else:
                lines[i] = ""
        return "\n".join(lines)
    else:
        return s

def post_process_string(it):
    """Remove spurious spacing from *MULTILINE_STRING tokens."""
    it = BackwardGenerator(it)
    for token in it:
        if token.type == "BLOCK_MULTILINES_STRING":
            previous = it.previous()
            if not previous.type == "INDENT":
                raise InternalBentoError(
                        "Error while post processing block line: %s -> %s" \
                        % (previous, token))
            else:
                indent = previous.value
                token.value = remove_lines_indent(token.value, indent)
                token.type = "MULTILINES_STRING"
        elif token.type == "MULTILINES_STRING":
            token.value = remove_lines_indent(token.value)
        yield token

def indent_generator(toks):
    """Post process the given stream of tokens to generate INDENT/DEDENT
    tokens.
    
    Note
    ----
    Each generated token's value is the total amount of spaces from the
    beginning of the line.
    
    The way indentation tokens are generated is similar to how it works in
    python."""
    stack = [0]

    # Dummy token to track the token just before the current one
    former = LexToken()
    former.type = "NEWLINE"
    former.value = "dummy"
    former.lineno = 0
    former.lexpos = -1

    def generate_dedent(stck, tok):
        amount = stck.pop(0)
        return new_dedent(amount, tok)

    for token in toks:
        if former.type == "NEWLINE":
            if token.type == "WS":
                indent = len(token.value)
            else:
                indent = 0

            if indent == stack[0]:
                former = token
                if indent > 0:
                    token = six.advance_iterator(toks)
                    former = token
                    yield token
                else:
                    yield former
            elif indent > stack[0]:
                stack.insert(0, indent)
                ind = new_indent(indent, token)
                former = ind
                yield ind
            elif indent < stack[0]:
                if not indent in stack:
                    raise ValueError("Wrong indent at line %d" % token.lineno)
                while stack[0] > indent:
                    former = generate_dedent(stack, token)
                    yield former
                if stack[0] > 0:
                    former = six.advance_iterator(toks)
                    yield former
                else:
                    former = token
                    yield token
        else:
            former = token
            yield token

    # Generate additional DEDENT so that the number of INDENT/DEDENT always
    # match
    while len(stack) > 1:
        former = generate_dedent(stack, token)
        yield former

def new_indent(amount, token):
    tok = LexToken()
    tok.type = "INDENT"
    tok.value = amount
    tok.lineno = token.lineno
    tok.lexpos = token.lexpos
    return tok

def new_dedent(amount, token):
    tok = LexToken()
    tok.type = "DEDENT"
    tok.value = amount
    tok.lineno = token.lineno
    tok.lexpos = token.lexpos
    return tok

class _Dummy(object):
    def __init__(self):
        self.type = "EOF"
        self.escaped = False
        self.value = None

    def __repr__(self):
        return "DummyToken(EOF)"

EOF = _Dummy()

class BentoLexer(object):
    def __init__(self, optimize=False):
        self.lexer = lex(reflags=re.UNICODE|re.MULTILINE, debug=0, optimize=optimize, nowarn=0, lextab='lextab')

    def input(self, data):
        self.lexer.input(data)
        stream = iter(self.lexer.token, None)
        stream = detect_escaped(stream)
        stream = merge_escaped(stream)
        stream = indent_generator(stream)
        stream = filter_ws_and_newline(stream)
        stream = post_process_string(stream)
        self.stream = stream

    def __iter__(self):
        return iter(self.token, None)

    def token(self):
        try:
            return six.advance_iterator(self.stream)
        except StopIteration:
            pass
