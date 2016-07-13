  # -*- coding: utf-8 -*-
"""Tests xonsh tools."""
import os
import pathlib
from tempfile import TemporaryDirectory
import stat
import builtins

import pytest

from xonsh.platform import ON_WINDOWS
from xonsh.lexer import Lexer

from xonsh.tools import (
    EnvPath, always_false, always_true, argvquote,
    bool_or_int_to_str, bool_to_str, check_for_partial_string,
    dynamic_cwd_tuple_to_str, ensure_int_or_slice, ensure_string,
    env_path_to_str, escape_windows_cmd_string, executables_in,
    expand_case_matching, find_next_break, iglobpath, is_bool, is_bool_or_int,
    is_callable, is_dynamic_cwd_width, is_env_path, is_float, is_int,
    is_int_as_str, is_logfile_opt, is_slice_as_str, is_string,
    is_string_or_callable, logfile_opt_to_str, str_to_env_path,
    subexpr_from_unbalanced, subproc_toks, to_bool, to_bool_or_int,
    to_dynamic_cwd_tuple, to_logfile_opt, pathsep_to_set, set_to_pathsep,
    is_string_seq, pathsep_to_seq, seq_to_pathsep, is_nonstring_seq_of_strings,
    pathsep_to_upper_seq, seq_to_upper_pathsep, expandvars
    )
from xonsh.commands_cache import CommandsCache
from xonsh.built_ins import expand_path
from xonsh.environ import Env

from tools import skip_if_on_windows, skip_if_on_unix

LEXER = Lexer()
LEXER.build()

INDENT = '    '

TOOLS_ENV = {'EXPAND_ENV_VARS': True, 'XONSH_ENCODING_ERRORS':'strict'}
ENCODE_ENV_ONLY = {'XONSH_ENCODING_ERRORS': 'strict'}
PATHEXT_ENV = {'PATHEXT': ['.COM', '.EXE', '.BAT']}

def test_subproc_toks_x():
    exp = '![x]'
    obs = subproc_toks('x', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_ls_l():
    exp = '![ls -l]'
    obs = subproc_toks('ls -l', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_git():
    s = 'git commit -am "hello doc"'
    exp = '![{0}]'.format(s)
    obs = subproc_toks(s, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_git_semi():
    s = 'git commit -am "hello doc"'
    exp = '![{0}];'.format(s)
    obs = subproc_toks(s + ';', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_git_nl():
    s = 'git commit -am "hello doc"'
    exp = '![{0}]\n'.format(s)
    obs = subproc_toks(s + '\n', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_indent_ls():
    s = 'ls -l'
    exp = INDENT + '![{0}]'.format(s)
    obs = subproc_toks(INDENT + s, mincol=len(INDENT), lexer=LEXER,
                       returnline=True)
    assert (exp == obs)


def test_subproc_toks_indent_ls_nl():
    s = 'ls -l'
    exp = INDENT + '![{0}]\n'.format(s)
    obs = subproc_toks(INDENT + s + '\n', mincol=len(INDENT), lexer=LEXER,
                       returnline=True)
    assert (exp == obs)


def test_subproc_toks_indent_ls_no_min():
    s = 'ls -l'
    exp = INDENT + '![{0}]'.format(s)
    obs = subproc_toks(INDENT + s, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_indent_ls_no_min_nl():
    s = 'ls -l'
    exp = INDENT + '![{0}]\n'.format(s)
    obs = subproc_toks(INDENT + s + '\n', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_indent_ls_no_min_semi():
    s = 'ls'
    exp = INDENT + '![{0}];'.format(s)
    obs = subproc_toks(INDENT + s + ';', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_indent_ls_no_min_semi_nl():
    s = 'ls'
    exp = INDENT + '![{0}];\n'.format(s)
    obs = subproc_toks(INDENT + s + ';\n', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_ls_comment():
    s = 'ls -l'
    com = '  # lets list'
    exp = '![{0}]{1}'.format(s, com)
    obs = subproc_toks(s + com, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_ls_42_comment():
    s = 'ls 42'
    com = '  # lets list'
    exp = '![{0}]{1}'.format(s, com)
    obs = subproc_toks(s + com, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_ls_str_comment():
    s = 'ls "wakka"'
    com = '  # lets list'
    exp = '![{0}]{1}'.format(s, com)
    obs = subproc_toks(s + com, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_indent_ls_comment():
    ind = '    '
    s = 'ls -l'
    com = '  # lets list'
    exp = '{0}![{1}]{2}'.format(ind, s, com)
    obs = subproc_toks(ind + s + com, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_indent_ls_str():
    ind = '    '
    s = 'ls "wakka"'
    com = '  # lets list'
    exp = '{0}![{1}]{2}'.format(ind, s, com)
    obs = subproc_toks(ind + s + com, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_ls_l_semi_ls_first():
    lsdl = 'ls -l'
    ls = 'ls'
    s = '{0}; {1}'.format(lsdl, ls)
    exp = '![{0}]; {1}'.format(lsdl, ls)
    obs = subproc_toks(s, lexer=LEXER, maxcol=6, returnline=True)
    assert (exp == obs)


def test_subproc_toks_ls_l_semi_ls_second():
    lsdl = 'ls -l'
    ls = 'ls'
    s = '{0}; {1}'.format(lsdl, ls)
    exp = '{0}; ![{1}]'.format(lsdl, ls)
    obs = subproc_toks(s, lexer=LEXER, mincol=7, returnline=True)
    assert (exp == obs)


def test_subproc_toks_hello_mom_first():
    fst = "echo 'hello'"
    sec = "echo 'mom'"
    s = '{0}; {1}'.format(fst, sec)
    exp = '![{0}]; {1}'.format(fst, sec)
    obs = subproc_toks(s, lexer=LEXER, maxcol=len(fst)+1, returnline=True)
    assert (exp == obs)


def test_subproc_toks_hello_mom_second():
    fst = "echo 'hello'"
    sec = "echo 'mom'"
    s = '{0}; {1}'.format(fst, sec)
    exp = '{0}; ![{1}]'.format(fst, sec)
    obs = subproc_toks(s, lexer=LEXER, mincol=len(fst), returnline=True)
    assert (exp == obs)


def test_subproc_toks_comment():
    exp = None
    obs = subproc_toks('# I am a comment', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_not():
    exp = 'not ![echo mom]'
    obs = subproc_toks('not echo mom', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_paren():
    exp = '(![echo mom])'
    obs = subproc_toks('(echo mom)', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_paren_ws():
    exp = '(![echo mom])  '
    obs = subproc_toks('(echo mom)  ', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_not_paren():
    exp = 'not (![echo mom])'
    obs = subproc_toks('not (echo mom)', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_and_paren():
    exp = 'True and (![echo mom])'
    obs = subproc_toks('True and (echo mom)', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_paren_and_paren():
    exp = '(![echo a]) and (echo b)'
    obs = subproc_toks('(echo a) and (echo b)', maxcol=9, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_semicolon_only():
    exp = None
    obs = subproc_toks(';', lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_pyeval():
    s = 'echo @(1+1)'
    exp = '![{0}]'.format(s)
    obs = subproc_toks(s, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_twopyeval():
    s = 'echo @(1+1) @(40 + 2)'
    exp = '![{0}]'.format(s)
    obs = subproc_toks(s, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_pyeval_parens():
    s = 'echo @(1+1)'
    inp = '({0})'.format(s)
    exp = '(![{0}])'.format(s)
    obs = subproc_toks(inp, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_twopyeval_parens():
    s = 'echo @(1+1) @(40+2)'
    inp = '({0})'.format(s)
    exp = '(![{0}])'.format(s)
    obs = subproc_toks(inp, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_pyeval_nested():
    s = 'echo @(min(1, 42))'
    exp = '![{0}]'.format(s)
    obs = subproc_toks(s, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_pyeval_nested_parens():
    s = 'echo @(min(1, 42))'
    inp = '({0})'.format(s)
    exp = '(![{0}])'.format(s)
    obs = subproc_toks(inp, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_capstdout():
    s = 'echo $(echo bat)'
    exp = '![{0}]'.format(s)
    obs = subproc_toks(s, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_capproc():
    s = 'echo !(echo bat)'
    exp = '![{0}]'.format(s)
    obs = subproc_toks(s, lexer=LEXER, returnline=True)
    assert (exp == obs)


def test_subproc_toks_pyeval_redirect():
    s = 'echo @("foo") > bar'
    inp = '{0}'.format(s)
    exp = '![{0}]'.format(s)
    obs = subproc_toks(inp, lexer=LEXER, returnline=True)
    assert (exp == obs)


@pytest.mark.parametrize('inp, exp', [
    ('f(x.', 'x.'),
    ('f(1,x.', 'x.'),
    ('f((1,10),x.y', 'x.y'),
])
def test_subexpr_from_unbalanced_parens(inp, exp):
    obs = subexpr_from_unbalanced(inp, '(', ')')
    assert exp == obs


@pytest.mark.parametrize('line, mincol, exp', [
    ('ls && echo a', 0, 4),
    ('ls && echo a', 6, None),
    ('ls && echo a || echo b', 6, 14),
    ('(ls) && echo a', 1, 4),
    ('not ls && echo a', 0, 8),
    ('not (ls) && echo a', 0, 8),
])
def test_find_next_break(line, mincol, exp):
    obs = find_next_break(line, mincol=mincol, lexer=LEXER)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    (42, True),
    (42.0, False),
    ('42', False),
    ('42.0', False),
    ([42], False),
    ([], False),
    (None, False),
    ('', False)
])
def test_is_int(inp, exp):
    obs = is_int(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ('42', True),
    ('42.0', False),
    (42, False),
    ([42], False),
    ([], False),
    (None, False),
    ('', False),
    (False, False),
    (True, False),
])
def test_is_int_as_str(inp, exp):
    obs = is_int_as_str(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    (42.0, True),
    (42.000101010010101010101001010101010001011100001101101011100, True),
    (42, False),
    ('42', False),
    ('42.0', False),
    ([42], False),
    ([], False),
    (None, False),
    ('', False),
    (False, False),
    (True, False),
])
def test_is_float(inp, exp):
    obs = is_float(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    (42, False),
    (None, False),
    ('42', False),
    ('-42', False),
    (slice(1,2,3), False),
    ([], False),
    (False, False),
    (True, False),
    ('1:2:3', True),
    ('1::3', True),
    ('1:', True),
    (':', True),
    ('[1:2:3]', True),
    ('(1:2:3)', True),
    ('r', False),
    ('r:11', False),
])
def test_is_slice_as_str(inp, exp):
    obs = is_slice_as_str(inp)
    assert exp == obs


def test_is_string_true():
    assert is_string('42.0')

def test_is_string_false():
    assert not is_string(42.0)


def test_is_callable_true():
    assert is_callable(lambda: 42.0)


def test_is_callable_false():
    assert not is_callable(42.0)


@pytest.mark.parametrize('inp', ['42.0', lambda: 42.0])
def test_is_string_or_callable_true(inp):
    assert is_string_or_callable(inp)


def test_is_string_or_callable_false():
    assert not is_string(42.0)


@pytest.mark.parametrize('inp', [42, '42'])
def test_always_true(inp):
    assert always_true(inp)


@pytest.mark.parametrize('inp', [42, '42'])
def test_always_false(inp):
    assert not always_false(inp)


@pytest.mark.parametrize('inp, exp', [(42, '42'), ('42', '42'),])
def test_ensure_string(inp, exp):
    obs = ensure_string(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ('', set()),
    ('a', {'a'}),
    (os.pathsep.join(['a', 'b']), {'a', 'b'}),
    (os.pathsep.join(['a', 'b', 'c']), {'a', 'b', 'c'}),
])
def test_pathsep_to_set(inp, exp):
    obs = pathsep_to_set(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    (set(), ''),
    ({'a'}, 'a'),
    ({'a', 'b'}, os.pathsep.join(['a', 'b'])),
    ({'a', 'b', 'c'}, os.pathsep.join(['a', 'b', 'c'])),
])
def test_set_to_pathsep(inp, exp):
    obs = set_to_pathsep(inp, sort=(len(inp) > 1))
    assert exp == obs


@pytest.mark.parametrize('inp', ['42.0', ['42.0']])
def test_is_string_seq_true(inp):
    assert is_string_seq(inp)


def test_is_string_seq_false():
    assert not is_string_seq([42.0])


def test_is_nonstring_seq_of_strings_true():
    assert is_nonstring_seq_of_strings(['42.0'])


def test_is_nonstring_seq_of_strings_true():
    assert not is_nonstring_seq_of_strings([42.0])


@pytest.mark.parametrize('inp, exp', [
    ('', []),
    ('a', ['a']),
    (os.pathsep.join(['a', 'b']), ['a', 'b']),
    (os.pathsep.join(['a', 'b', 'c']), ['a', 'b', 'c']),
])
def test_pathsep_to_seq():
    obs = pathsep_to_seq(inp)
    assert exp == obs

@pytest.mark.parametrize('inp, exp', [
    ([], ''),
    (['a'], 'a'),
    (['a', 'b'], os.pathsep.join(['a', 'b'])),
    (['a', 'b', 'c'], os.pathsep.join(['a', 'b', 'c'])),
])
def test_seq_to_pathsep():
    obs = seq_to_pathsep(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ('', []),
    ('a', ['A']),
    (os.pathsep.join(['a', 'B']), ['A', 'B']),
    (os.pathsep.join(['A', 'b', 'c']), ['A', 'B', 'C']),
])
def test_pathsep_to_upper_seq():
    obs = pathsep_to_upper_seq(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
        ([], ''),
        (['a'], 'A'),
        (['a', 'b'], os.pathsep.join(['A', 'B'])),
        (['a', 'B', 'c'], os.pathsep.join(['A', 'B', 'C'])),
        ])
def test_seq_to_upper_pathsep():
    obs = seq_to_upper_pathsep(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ('/home/wakka', False),
    (['/home/jawaka'], False),
    (EnvPath(['/home/jawaka']), True),
    (EnvPath(['jawaka']), True),
    (EnvPath(b'jawaka:wakka'), True),
])
def test_is_env_path():
    obs = is_env_path(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ('/home/wakka', ['/home/wakka']),
    ('/home/wakka' + os.pathsep + '/home/jawaka',
     ['/home/wakka', '/home/jawaka']),
    (b'/home/wakka', ['/home/wakka']),
])
def test_str_to_env_path(inp, exp):
    obs = str_to_env_path(inp)
    assert exp == obs.paths


@pytest.mark.parametrize('inp, exp', [
    (['/home/wakka'], '/home/wakka'),
    (['/home/wakka', '/home/jawaka'],
     '/home/wakka' + os.pathsep + '/home/jawaka'),
])
def test_env_path_to_str(inp, exp):
    obs = env_path_to_str(inp)
    assert exp == obs


# helper
def expand(path):
    return os.path.expanduser(os.path.expandvars(path))

@pytest.mark.parametrize('env', [TOOLS_ENV, ENCODE_ENV_ONLY])
@pytest.mark.parametrize('inp, exp', [
    ('xonsh_dir', 'xonsh_dir'),
    ('.', '.'),
    ('../', '../'),
    ('~/', '~/'),
    (b'~/../', '~/../'),
])
def test_env_path_getitem(inp, exp, xonsh_builtins, env):
    xonsh_builtins.__xonsh_env__ = env
    obs = EnvPath(inp)[0] # call to __getitem__
    if env.get('EXPAND_ENV_VARS'):
        assert expand(exp) == obs
    else:
        assert exp == obs


@pytest.mark.parametrize('env', [TOOLS_ENV, ENCODE_ENV_ONLY])
@pytest.mark.parametrize('inp, exp', [
    (os.pathsep.join(['xonsh_dir', '../', '.', '~/']),
     ['xonsh_dir', '../', '.', '~/']),
    ('/home/wakka' + os.pathsep + '/home/jakka' + os.pathsep + '~/',
     ['/home/wakka', '/home/jakka', '~/'])
])
def test_env_path_multipath(inp, exp, xonsh_builtins, env):
    # cases that involve path-separated strings
    xonsh_builtins.__xonsh_env__ = env
    if env == TOOLS_ENV:
        obs = [i for i in EnvPath(inp)]
        assert [expand(i) for i in exp] == obs
    else:
        obs = [i for i in EnvPath(inp)]
        assert [i for i in exp] == obs


@pytest.mark.parametrize('inp, exp', [
    (pathlib.Path('/home/wakka'), ['/home/wakka'.replace('/',os.sep)]),
    (pathlib.Path('~/'), ['~']),
    (pathlib.Path('.'), ['.']),
    (['/home/wakka', pathlib.Path('/home/jakka'), '~/'],
     ['/home/wakka', '/home/jakka'.replace('/',os.sep), '~/']),
    (['/home/wakka', pathlib.Path('../'), '../'],
     ['/home/wakka', '..', '../']),
    (['/home/wakka', pathlib.Path('~/'), '~/'],
     ['/home/wakka', '~', '~/']),
])
def test_env_path_with_pathlib_path_objects(inp, exp, xonsh_builtins):
    xonsh_builtins.__xonsh_env__ = TOOLS_ENV
    # iterate over EnvPath to acquire all expanded paths
    obs = [i for i in EnvPath(inp)]
    assert [expand(i) for i in exp] == obs

@pytest.mark.parametrize('inp', ['42.0', [42.0]] )
def test_is_nonstring_seq_of_strings_false(inp):
    assert not is_nonstring_seq_of_strings(inp)


@pytest.mark.parametrize('inp, exp', [
    ('', []),
    ('a', ['a']),
    (os.pathsep.join(['a', 'b']), ['a', 'b']),
    (os.pathsep.join(['a', 'b', 'c']), ['a', 'b', 'c']),
])
def test_pathsep_to_seq(inp, exp):
    obs = pathsep_to_seq(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ([], ''),
    (['a'], 'a'),
    (['a', 'b'], os.pathsep.join(['a', 'b'])),
    (['a', 'b', 'c'], os.pathsep.join(['a', 'b', 'c'])),
])
def test_seq_to_pathsep(inp, exp):
    obs = seq_to_pathsep(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ('', []),
    ('a', ['A']),
    (os.pathsep.join(['a', 'B']), ['A', 'B']),
    (os.pathsep.join(['A', 'b', 'c']), ['A', 'B', 'C']),
])
def test_pathsep_to_upper_seq(inp, exp):
    obs = pathsep_to_upper_seq(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ([], ''),
    (['a'], 'A'),
    (['a', 'b'], os.pathsep.join(['A', 'B'])),
    (['a', 'B', 'c'], os.pathsep.join(['A', 'B', 'C'])),
])
def test_seq_to_upper_pathsep(inp, exp):
    obs = seq_to_upper_pathsep(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ('/home/wakka', False),
    (['/home/jawaka'], False),
    (EnvPath(['/home/jawaka']), True),
    (EnvPath(['jawaka']), True),
    (EnvPath(b'jawaka:wakka'), True),
])
def test_is_env_path(inp, exp):
    obs = is_env_path(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ('/home/wakka', ['/home/wakka']),
    ('/home/wakka' + os.pathsep + '/home/jawaka',
     ['/home/wakka', '/home/jawaka']),
    (b'/home/wakka', ['/home/wakka']),
])
def test_str_to_env_path(inp, exp):
    obs = str_to_env_path(inp)
    assert exp == obs.paths


@pytest.mark.parametrize('inp, exp', [
    (['/home/wakka'], '/home/wakka'),
    (['/home/wakka', '/home/jawaka'],
     '/home/wakka' + os.pathsep + '/home/jawaka'),
])
def test_env_path_to_str(inp, exp):
    obs = env_path_to_str(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    (pathlib.Path('/home/wakka'), ['/home/wakka'.replace('/',os.sep)]),
    (pathlib.Path('~/'), ['~']),
    (pathlib.Path('.'), ['.']),
    (['/home/wakka', pathlib.Path('/home/jakka'), '~/'],
     ['/home/wakka', '/home/jakka'.replace('/',os.sep), '~/']),
    (['/home/wakka', pathlib.Path('../'), '../'],
     ['/home/wakka', '..', '../']),
    (['/home/wakka', pathlib.Path('~/'), '~/'],
     ['/home/wakka', '~', '~/']),
])
def test_env_path_with_pathlib_path_objects(inp, exp, xonsh_builtins):
    xonsh_builtins.__xonsh_env__ = TOOLS_ENV
    # iterate over EnvPath to acquire all expanded paths
    obs = [i for i in EnvPath(inp)]
    assert [expand(i) for i in exp] == obs


# helper
def mkpath(*paths):
    """Build os-dependent paths properly."""
    return os.sep + os.sep.join(paths)


@pytest.mark.parametrize('inp, exp', [
    ([mkpath('home', 'wakka'),
      mkpath('home', 'jakka'),
      mkpath('home', 'yakka')],
     [mkpath('home', 'wakka'),
      mkpath('home', 'jakka')])
])
def test_env_path_slice_get_all_except_last_element(inp, exp):
    obs = EnvPath(inp)[:-1]
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
        ([mkpath('home', 'wakka'),
          mkpath('home', 'jakka'),
          mkpath('home', 'yakka')],
         [mkpath('home', 'jakka'),
          mkpath('home', 'yakka')])
])
def test_env_path_slice_get_all_except_first_element(inp, exp):
    obs = EnvPath(inp)[1:]
    assert exp == obs


@pytest.mark.parametrize('inp, exp_a, exp_b', [
        ([mkpath('home', 'wakka'),
          mkpath('home', 'jakka'),
          mkpath('home', 'yakka'),
          mkpath('home', 'takka')],
         [mkpath('home', 'wakka'),
          mkpath('home', 'yakka')],
         [mkpath('home', 'jakka'),
          mkpath('home', 'takka')])
])
def test_env_path_slice_path_with_step(inp, exp_a, exp_b):
    obs_a = EnvPath(inp)[0::2]
    assert exp_a == obs_a
    obs_b = EnvPath(inp)[1::2]
    assert exp_b == obs_b


@pytest.mark.parametrize('inp, exp', [
        ([mkpath('home', 'wakka'),
          mkpath('home', 'xakka'),
          mkpath('other', 'zakka'),
          mkpath('another', 'akka'),
          mkpath('home', 'bakka')],
         [mkpath('other', 'zakka'),
          mkpath('another', 'akka')])
])
def test_env_path_keep_only_non_home_paths(inp, exp):
    obs = EnvPath(inp)[2:4]
    assert exp == obs


@pytest.mark.parametrize('inp', [True, False])
def test_is_bool_true(inp):
    assert True == is_bool(inp)


@pytest.mark.parametrize('inp', [1, 'yooo hooo!'])
def test_is_bool_false(inp):
    assert False == is_bool(inp)


@pytest.mark.parametrize('inp, exp', [
    (True, True),
    (False, False),
    (None, False),
    ('', False),
    ('0', False),
    ('False', False),
    ('NONE', False),
    ('TRUE', True),
    ('1', True),
    (0, False),
    (1, True),
])
def test_to_bool(inp, exp):
    obs = to_bool(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [(True, '1'), (False, '')])
def test_bool_to_str(inp, exp):
    assert bool_to_str(inp) == exp


@pytest.mark.parametrize('inp, exp', [
    (True, True),
    (False, True),
    (1, True),
    (0, True),
    ('Yolo', False),
    (1.0, False),
])
def test_is_bool_or_int(inp, exp):
    obs = is_bool_or_int(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    (True, True),
    (False, False),
    (1, 1),
    (0, 0),
    ('', False),
    (0.0, False),
    (1.0, True),
    ('T', True),
    ('f', False),
    ('0', 0),
    ('10', 10),
])
def test_to_bool_or_int(inp, exp):
    obs = to_bool_or_int(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    (True, '1'),
    (False, ''),
    (1, '1'),
    (0, '0'),
])
def test_bool_or_int_to_str(inp, exp):
    obs = bool_or_int_to_str(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
        (42, 42),
        (None, slice(None, None, None)),
        ('42', 42),
        ('-42', -42),
        ('1:2:3', slice(1, 2, 3)),
        ('1::3', slice(1, None, 3)),
        (':', slice(None, None, None)),
        ('1:', slice(1, None, None)),
        ('[1:2:3]', slice(1, 2, 3)),
        ('(1:2:3)', slice(1, 2, 3)),
        ('r', False),
        ('r:11', False),
        ])
def test_ensure_int_or_slice(inp, exp):
    obs = ensure_int_or_slice(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ('20', False),
    ('20%', False),
    ((20, 'c'), False),
    ((20.0, 'm'), False),
    ((20.0, 'c'), True),
    ((20.0, '%'), True),
])
def test_is_dynamic_cwd_width(inp, exp):
    obs = is_dynamic_cwd_width(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ('throwback.log', True),
    ('', True),
    (None, True),
    (True, False),
    (False, False),
    (42, False),
    ([1, 2, 3], False),
    ((1, 2), False),
    (("wrong", "parameter"), False),
    skip_if_on_windows(('/dev/null', True))
])
def test_is_logfile_opt(inp, exp):
    obs = is_logfile_opt(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
        (True, None),
        (False, None),
        (1, None),
        (None, None),
        ('throwback.log', 'throwback.log'),
        skip_if_on_windows(('/dev/null', '/dev/null')),
        skip_if_on_windows(('/dev/nonexistent_dev', None))
    ])
def test_to_logfile_opt(inp, exp):
    obs = to_logfile_opt(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    (None, ''),
    ('', ''),
    ('throwback.log', 'throwback.log'),
    ('/dev/null', '/dev/null')
])
def test_logfile_opt_to_str(inp, exp):
    obs = logfile_opt_to_str(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ('20', (20.0, 'c')),
    ('20%', (20.0, '%')),
    ((20, 'c'), (20.0, 'c')),
    ((20, '%'), (20.0, '%')),
    ((20.0, 'c'), (20.0, 'c')),
    ((20.0, '%'), (20.0, '%')),
    ('inf', (float('inf'), 'c')),
])
def test_to_dynamic_cwd_tuple(inp, exp):
    obs = to_dynamic_cwd_tuple(inp)
    assert exp == obs


@pytest.mark.parametrize('inp, exp', [
    ((20.0, 'c'), '20.0'),
    ((20.0, '%'), '20.0%'),
    ((float('inf'), 'c'), 'inf'),
])
def test_dynamic_cwd_tuple_to_str(inp, exp):
    obs = dynamic_cwd_tuple_to_str(inp)
    assert exp == obs


@pytest.mark.parametrize('st, esc', [
    ('', ''),
    ('foo', 'foo'),
    ('foo&bar', 'foo^&bar'),
    ('foo$?-/_"\\', 'foo$?-/_^"\\'),
    ('^&<>|', '^^^&^<^>^|'),
    ('this /?', 'this /.')
])
def test_escape_windows_cmd_string(st, esc):
    obs = escape_windows_cmd_string(st)
    assert esc == obs


@pytest.mark.parametrize('st, esc', [
    ('', '""'),
    ('foo', 'foo'),
    (r'arg1 "hallo, "world""  "\some\path with\spaces")',
     r'"arg1 \"hallo, \"world\"\"  \"\some\path with\spaces\")"'),
    (r'"argument"2" argument3 argument4',
     r'"\"argument\"2\" argument3 argument4"'),
    (r'"\foo\bar bar\foo\" arg',
     r'"\"\foo\bar bar\foo\\\" arg"')
])
def test_argvquote(st, esc):
    obs = argvquote(st)
    assert esc == obs


_leaders = ('', 'not empty')
_r = ('r', '')
_b = ('b', '')
_u = ('u', '')
_chars = set(i+j+k for i in _r for j in _b for k in _u)
_chars |= set(i+j+k for i in _r for j in _u for k in _b)
_chars |= set(i+j+k for i in _b for j in _u for k in _r)
_chars |= set(i+j+k for i in _b for j in _r for k in _u)
_chars |= set(i+j+k for i in _u for j in _r for k in _b)
_chars |= set(i+j+k for i in _u for j in _b for k in _r)
_squote = ('"""', '"', "'''", "'")
_startend = {c+s: s for c in _chars for s in _squote}

inners = "this is a string"


def test_partial_string():
    # single string at start
    assert check_for_partial_string('no strings here') == (None, None, None)
    assert check_for_partial_string('') == (None, None, None)
    for s, e in _startend.items():
        _test = s + inners + e
        for l in _leaders:
            for f in _leaders:
                # single string
                _res = check_for_partial_string(l + _test + f)
                assert _res == (len(l), len(l) + len(_test), s)
                # single partial
                _res = check_for_partial_string(l + f + s + inners)
                assert _res == (len(l+f), None, s)
                for s2, e2 in _startend.items():
                    _test2 = s2 + inners + e2
                    for l2 in _leaders:
                        for f2 in _leaders:
                            # two strings
                            _res = check_for_partial_string(l + _test + f + l2 + _test2 + f2)
                            assert _res == (len(l+_test+f+l2), len(l+_test+f+l2+_test2), s2)
                            # one string, one partial
                            _res = check_for_partial_string(l + _test + f + l2 + s2 + inners)
                            assert _res == (len(l+_test+f+l2), None, s2)


def test_executables_in(xonsh_builtins):
    expected = set()
    types = ('file', 'directory', 'brokensymlink')
    if ON_WINDOWS:
        # Don't test symlinks on windows since it requires admin
        types = ('file', 'directory')
    executables = (True, False)
    with TemporaryDirectory() as test_path:
        for _type in types:
            for executable in executables:
                fname = '%s_%s' % (_type, executable)
                if _type == 'none':
                    continue
                if _type == 'file' and executable:
                    ext = '.exe' if ON_WINDOWS else ''
                    expected.add(fname + ext)
                else:
                    ext = ''
                path = os.path.join(test_path, fname + ext)
                if _type == 'file':
                    with open(path, 'w') as f:
                        f.write(fname)
                elif _type == 'directory':
                    os.mkdir(path)
                elif _type == 'brokensymlink':
                    tmp_path = os.path.join(test_path, 'i_wont_exist')
                    with open(tmp_path, 'w') as f:
                        f.write('deleteme')
                        os.symlink(tmp_path, path)
                    os.remove(tmp_path)
                if executable and not _type == 'brokensymlink':
                    os.chmod(path, stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR)
            if ON_WINDOWS:
                xonsh_builtins.__xonsh_env__ = PATHEXT_ENV
                result = set(executables_in(test_path))
            else:
                result = set(executables_in(test_path))
    assert (expected == result)


@pytest.mark.parametrize('inp, exp', [
    ('yo', '[Yy][Oo]'),
    ('[a-f]123e', '[a-f]123[Ee]'),
    ('${HOME}/yo', '${HOME}/[Yy][Oo]'),
    ('./yo/mom', './[Yy][Oo]/[Mm][Oo][Mm]'),
    ('Eßen', '[Ee][Ss]?[Ssß][Ee][Nn]'),
])
def test_expand_case_matching(inp, exp):
    obs = expand_case_matching(inp)
    assert exp == obs


def test_commands_cache_lazy():
    cc = CommandsCache()
    assert not cc.lazyin('xonsh')
    assert 0 == len(list(cc.lazyiter()))
    assert 0 == cc.lazylen()


@pytest.mark.parametrize('inp, exp', [
    ("foo", "foo"),
    ("$foo $bar", "bar $bar"),
    ("$foobar", "$foobar"),
    ("$foo $spam", "bar eggs"),
    ("$an_int$spam$a_bool", "42eggsTrue"),
    ("bar$foo$spam$foo $an_int $none", "barbareggsbar 42 None"),
    ("$foo/bar", "bar/bar"),
    ("${'foo'} $spam", "bar eggs"),
    ("${'foo'} ${'a_bool'}", "bar True"),
    ("${'foo'}bar", "barbar"),
    ("${'foo'}/bar", "bar/bar"),
    ("${\"foo\'}", "${\"foo\'}"),
    ("$?bar", "$?bar"),
    ("$foo}bar", "bar}bar"),
    ("${'foo", "${'foo"),
    skip_if_on_unix(("%foo%bar", "barbar")),
    skip_if_on_unix(("%foo% %a_bool%", "bar True")),
    skip_if_on_unix(("%foo%%an_int%", "bar42")),
    skip_if_on_unix(("%foo% $spam ${'a_bool'}", "bar eggs True")),
    (b"foo", "foo"),
    (b"$foo bar", "bar bar"),
    (b"${'foo'}bar", "barbar"),
    skip_if_on_unix((b"%foo%bar", "barbar")),
])
def test_expandvars(inp, exp, xonsh_builtins):
    """Tweaked for xonsh cases from CPython `test_genericpath.py`"""
    env = Env({'foo':'bar', 'spam': 'eggs', 'a_bool': True, 'an_int': 42, 'none': None})
    xonsh_builtins.__xonsh_env__ = env
    assert expandvars(inp) == exp
