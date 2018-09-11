import re

# will hold the regular expression rules for converting lexemes to tokens
scanner_rules = []
# will hold the errors found in the program (both lexical and syntax errors)
errors = []
# will hold the tokens found in the input file
tokens = []
# will hold the classes found in the input file
classes = []
# will hold the methods found in the input file, corresponding to each class
methods = []
# points to the next token to be parsed from the list of input tokens identified
token_index = 0


'''
This function scans and parses the input file, and, based on the result,
outputs either the file structure (classes and their corresponding methods),
or a list of lexical and syntax errors identified.

:param filename: the name of the file to be parsed
'''
def parse(filename):
    global tokens

    with open(filename, 'r') as input_file:
        # get the tokens
        tokens = scan(input_file)
        # parse the program
        program_0()
        # output
        if not errors:
            print_file_structure()
        else:
            print_errors()
    input_file.closed


'''
This function generates the scanner rules to be used for lexing, identifies the
lexemes contained in the file, along with their coordinates (row and column in
the file) for more informative error messages, and then tokenises the lexemes
and returns a list of tuples of tokens and their corresponding coordinates, and
their values/names, if they are integers, strings, or identifiers.

:param input_file: the input file
:returns: a list of tokens found in the file, along with their position in the
          file as a (row, column) pair, and their value/name, if they are
          integers, strings, or identifiers
'''
def scan(input_file):
    global tokens
    global scanner_rules

    # generate lexing regular expressions
    scanner_rules = generate_scanner_rules()
    # split the file into lines
    lines = input_file.read().split('\n')
    lexemes = []
    for line in lines:
        # split each line into words
        words = line.split()
        line_lexemes = []
        # split each word into lexemes
        for word in words:
            line_lexemes = line_lexemes + get_lexemes(word)
        # bind lexemes that form strings into single lexemes, and add them to
        # the list of lexemes
        lexemes = lexemes + bind_strings(line_lexemes)
    # obtain the coordinates for each lexeme
    coordinates = get_coordinates(input_file, lexemes)
    # replace the rule that accepts single characters (used to prevent errors
    # when encountering non-COOL symbols in strings) with a rule that
    # identifies strings (used to match lexemes to tokens)
    scanner_rules[-2] = ('string', re.compile('^\".*\"$'))
    # match the lexemes to tokens
    tokens = match_lexemes(lexemes, coordinates, scanner_rules)

    return tokens


'''
This function creates a list of (token, regex) pairs that define the scanning
rules for COOL programs. Lists of keywords and symbols are defined in the
function, but regular expressions are mostly built automatically, to ease the
generation of these rules. The final entry in the list is the error token that
matches anything. Matching will usually be done by trying each rule, starting
with the first one, so reaching the last rule means that the token is an error.

:returns: a list of (token, regex) rules representing the scanner rules
'''
def generate_scanner_rules():
    scanner_rules = []
    # list of case insensitive keywords
    keyword_matches = ['class', 'else', 'fi', 'if', 'in', 'inherits',
                       'isvoid', 'let', 'loop', 'pool', 'then', 'while', 'case',
                       'esac', 'new', 'of', 'not']
    # list of keywords and symbols that must match exactly like this
    exact_matches = ['true', 'false', '{', '}', ':', ';', ',', '<-', '=>', '@',
                     '-', '/', '~', '<', '<=', '=']
    # list of symbols that need to be escaped in regular expressions
    escaped_matches = ['(', ')', '.', '+', '*', '"']

    # add rules for all the symbols above
    for match in keyword_matches:
        scanner_rules.append((match, re.compile('^' + match + '$'),
                              re.IGNORECASE))
    for match in exact_matches:
        scanner_rules.append((match, re.compile('^' + match + '$')))
    for match in escaped_matches:
        scanner_rules.append((match, re.compile('^\\' + match + '$')))
    # add a rule for escaped characters, i.e. characters followed by a '\'
    scanner_rules.append(('escaped_char', re.compile('^\\\\.$')))
    # add rules for tokens which can have many forms, such as identifiers
    scanner_rules.append(('integer', re.compile('^[0-9]+$')))
    scanner_rules.append(('type_id', re.compile('^[A-Z]\w*$')))
    scanner_rules.append(('obj_id', re.compile('^[a-z]\w*$')))
    scanner_rules.append(('char', re.compile('^.$')))
    # everything else is an error
    scanner_rules.append(('error', re.compile('.*')))

    return scanner_rules


'''
This function splits a word (a sequence of characters with no whitespaces) into
lexemes using the maximal munch principle.

:param word: the input word
:returns: a list of lexemes made from the given word
'''
def get_lexemes(word):
    front = word
    back = ''
    lexemes = []

    while front != '':
        # attempt to match the front part
        token = match_lexeme(front)
        # if unsuccessful, try matching the same string without the last
        # character, which is added to the back part
        if token == 'error':
            back = front[-1] + back
            front = front[:-1]
        else:
            # append the found lexeme to the list and do the same thing for the
            # back part
            lexemes.append(front)
            return lexemes + get_lexemes(back)
    return lexemes


'''
This function attemps to match a string to any of the regular expressions that
make up the COOL token rules.

:param lexeme: the input string
:returns: the matched token type
'''
def match_lexeme(lexeme):
    for rule in scanner_rules:
        result = rule[1].match(lexeme)
        # if a match is made, return that token; a match is guaranteed to be
        # made eventually, as the error regular expression matches everything
        if result:
            return rule[0]


'''
This function takes the lexemes found on a single line in the input file, and
attempts to bind together the lexemes that should make up a string.

:param line_lexemes: a list of lexemes found on a single line
:returns: the modified list, with strings as single lexemes
'''
def bind_strings(line_lexemes):
    in_string = False
    quotation_marks = 0

    # count the number of quotation marks found on the line
    for lexeme in line_lexemes:
        if lexeme == '"':
            quotation_marks = quotation_marks + 1

    i = 0
    while i < len(line_lexemes):
        # if a quotation mark is encountered, it means that a string has just
        # begun, or just ended
        if line_lexemes[i] == '"':
            quotation_marks = quotation_marks - 1
            in_string = not in_string

            # if a string has just been opened, and there are no more quotation
            # marks on the line, then there is an error, so don't merge any more
            # characters
            if in_string and quotation_marks == 0:
                break
        # if the lexeme is in a string, and the lexeme is not a quotation mark,
        # or the lexeme isn't in a string, and it is a quotation mark, merge
        # it with the previous lexeme and delete it from the list
        if in_string != (line_lexemes[i] == '"'):
            line_lexemes[i - 1] = line_lexemes[i - 1] + line_lexemes[i]
            del(line_lexemes[i])
        else:
            i = i + 1

    return line_lexemes


'''
This function returns a list of (row, column) pairs which represent the file
coordinates of each lexeme. This will be useful for debugging, since error
messages will show exactly where the problems are.

:param input_file: the input file from which symbols are read
:lexemes: the list of lexemes
:returns: a list of (row, column) pairs, where the ith pair represents the file
          coordinates of the first character of the ith lexeme
'''
def get_coordinates(input_file, lexemes):
    coordinates = []
    row = 1
    column = 0

    input_file.seek(0)
    # the lexemes are already ordered as they appear in the file, so a single
    # file read will suffice
    for lexeme in lexemes:
        # find the first character of the lexeme
        while True:
            c = input_file.read(1)
            if not c:
                break
            # if a newline character is found, increment the row and reset the
            # column coordinate
            if c == '\n':
                row = row + 1
                column = 0
            else:
                # increment the column
                column = column + 1
                # if the first character of the lexeme has been found, add
                # the current coordinates to the list and skip the remaining
                # characters of that lexeme
                if c == lexeme[0]:
                    coordinates.append((row, column))
                    input_file.seek(input_file.tell() + len(lexeme) - 1)
                    column = column + len(lexeme) - 1
                    break

    return coordinates


'''
This function turns a list of lexemes and their coordinates into a list of
(token, coordinates) tuples, which can be then parsed. The coordinates of each
token will be helpful when printing error messages. If a token is an identifier,
a (token, coordinates, id_name) tuple will be added instead, again to aid in
outputting error messages or the file structure.

:param lexemes: the list of lexemes identified in the file; ignores erroneous
                lexemes
:param coordinates: the list of coordinates for each lexeme
:param scanner_rules: the regular expressions used to convert lexemes to tokens
:returns: a list of tokens, their coordinates, and their names, if they are
          identifiers
'''
def match_lexemes(lexemes, coordinates, scanner_rules):
    tokens = []

    for lexeme, coordinate in zip(lexemes, coordinates):
        token = ''
        # test each rule against the given lexeme and assign it the first token
        # that matches it
        token = match_lexeme(lexeme)
        # if the lexeme matched to an error, prepare a message to be printed out
        if token == 'error':
            errors.append('Lexical error: Unknown token \'' + lexeme +
                          '\' at position ' + str(coordinate) + '.')
        # if the token is an identifier, also add its name to the list
        elif token in ['type_id', 'obj_id', 'integer', 'string']:
            tokens.append((token, coordinate, lexeme))
        # otherwise, append the token type and coordinates
        else:
            tokens.append((token, coordinate))

    # get the coordinates of the end of file and add an EOF token to the list
    if not tokens:
        eof_coordinate = (0, 0)
    else:
        eof_coordinate = (coordinates[-1][0],
                           coordinates[-1][1] + len(lexeme))
    tokens.append(('eof', eof_coordinate))

    return tokens


'''
This function attempts to match the current token to the given token. If they
are of the same type, it will return True and increment the token index.
Otherwise, it will add a syntax error to the error list and skip to the first
encounter of the requested token, or the end of file if it is not found.

:param token: the requested token
:returns: True if the token is found until the end of file, False otherwise
'''
def match(token):
    global token_index

    # if the requested token is found, increment the index and return True
    if check(token):
        token_index = token_index + 1
        return True

    # otherwise, add an error, and return True if the token is found eventually,
    # or False, otherwise
    add_syntax_error([token])
    if skip_to([token]):
        token_index = token_index + 1
        return True
    return False


'''
This function adds a syntax error to the error list, specifying the unexpected
token, its coordinates in the file, as well as a list of tokens that were
expected instead.

:param expected: the list of expected tokens
'''
def add_syntax_error(expected):
    # if the token is an identifier, output its name instead of its type
    if tokens[token_index][0] in ['obj_id', 'type_id', 'integer', 'string']:
        token = tokens[token_index][2]
    else:
        token = tokens[token_index][0]

    error = ('Syntax Error: Unexpected token \'' + token + '\' at ' +
              str(tokens[token_index][1]) + '.')
    # add the expected values
    for i in range(0, len(expected)):
        if i == 0:
            error = error + ' Expected \'' + expected[i] + '\''
        elif i < len(expected) - 1:
            error = error + ', \'' + expected[i] + '\''
        else:
            error = error + ' or \'' + expected[i] + '\''
    error = error + '.'
    errors.append(error)


'''
This function increments the token index until one of the expcted tokens is
encountered. This is done to allow the program to recover from errors by
ignoring erroneous tokens until the needed token is found, and then resuming
the syntax analysis from there.

:param expected: the list of expected tokens
:returns: True if any of the expected tokens is encountered, False otherwise
'''
def skip_to(expected):
    global token_index
    while token_index < len(tokens) - 1:
        token_index = token_index + 1
        # check if any expected token matches the current token
        for token in expected:
            if check(token):
                #match(token)
                return True
    return False


'''
This function checks if the current token is of the same type as the given
token.

:param token: the expected token
:returns: True if the expected token is found, False otherwise
'''
def check(token):
    if tokens[token_index][0] == token:
        return True
    return False


'''
This function prints the file structure, i.e. the classes and their methods. It
will only be called if the program is error-free.
'''
def print_file_structure():
    print('No errors found')
    for i in range(0, len(classes)):
        print(classes[i])
        for method in methods[i]:
            print('    ' + method)


'''
This function prints the errors found in the program, starting with lexical
errors, then syntax errors, both in order of appearance in the file. It will
only be called if errors are found.
'''
def print_errors():
    print('Errors found')
    for error in errors:
        print(error)


'''
The remaining functions model the COOL grammar. The grammar has been modified
such that every non-terminal has no more than one production rule for each
token. As such, each of the following functions will try to pick the correct
rule based on the current token. If none is found, an error is recorded and a
recovery is attempted by going through the next tokens until one that matches
one of its rules is found, such that the process can resume.

The functions return True or False, and the production rules are modelled using
boolean 'and'. This makes use of the fact that Python boolean expression
evaluation is lazy. For example, the production rule A ::= BCD would be
expressed as a function A which returns B() and C() and D(). If B throws an
error and it cannot recover, it will return False, such that C() and D() don't
get called anymore.

The function names are taken from the COOl grammar provided in the manual, and
modified as follows:
- an indexed rule (_0, _1, _2, etc.) represents a part of the original rule,
  which has been broken down into several rules to eliminate backtracking
- a rule with a _p after its name represents a variation of the rule without _p
  (_p stands for prime, i.e. ')
- expression rules have letter indices (_a, _b, etc.), because the expression
  rule has been broken down into multiple rules for precedence
'''
def program_0():
    return (match('class') and match('type_id') and class_0() and class_1() and
            match(';') and program_1())


def program_1():
    if check('eof'):
        return True
    return program_0()


def class_0():
    classes.append(tokens[token_index - 1][2])
    methods.append([])

    if check('{'):
        return match('{')
    if check('inherits'):
        return match('inherits') and match('type_id') and match('{')
    add_syntax_error(['{', 'inherits'])
    return skip_to(['{', 'inherits']) and class_0()


def class_1():
    if check('}'):
        return match('}')
    if check('obj_id'):
        return match('obj_id') and feature_0() and class_1()
    add_syntax_error(['}', 'obj_id'])
    return skip_to(['}', 'obj_id']) and class_1()


def feature_0():
    if check('('):
        return (match('(') and feature_1() and match(':') and match('type_id')
                and match('{') and expr_a() and match('}') and match(';'));
    if check(':'):
        return match(':') and match('type_id') and feature_2()
    add_syntax_error(['(', ':'])
    return skip_to(['(', ':']) and feature_0()


def feature_1():
    methods[-1].append(tokens[token_index - 2][2])
    if check('obj_id'):
        return match('obj_id') and match(':') and match('type_id') and formals()
    if check(')'):
        return match(')')
    add_syntax_error(['obj_id', ')'])
    return skip_to(['obj_id', ')']) and feature_1()


def feature_2():
    if check(';'):
        return match(';')
    if check('<-'):
        return match('<-') and expr_a() and match(';')
    add_syntax_error([';', '<-'])
    return skip_to([';', '<-']) and feature_2()


def formals():
    if check(','):
        return (match(',') and match('obj_id') and match(':') and
                match('type_id') and formals())
    if check(')'):
        return match(')')
    add_syntax_error([',', ')'])
    return skip_to([',', ')']) and formals()


def expr_a():
    # this is the only case of looking up two characters, to distinguish
    # between assignment and just an object ID
    if check('obj_id') and tokens[token_index + 1][0] == '<-':
        return match('obj_id') and match('<-') and expr_a()
    return expr_b()


def expr_b():
    if check('not'):
        return match('not') and expr_b()
    return expr_c0()


def expr_c0():
    return expr_d0() and expr_c1()


def expr_c1():
    if check('<'):
        return match('<') and expr_c0()
    if check('<='):
        return match('<=') and expr_c0()
    if check('='):
        return match('=') and expr_c0()
    return True


def expr_d0():
    return expr_e0() and expr_d1()


def expr_d1():
    if check('+'):
        return match('+') and expr_d0()
    if check('-'):
        return match('-') and expr_d0()
    return True


def expr_e0():
    return expr_f() and expr_e1()


def expr_e1():
    if check('*'):
        return match('*') and expr_e0()
    if check('/'):
        return match('/') and expr_e0()
    return True


def expr_f():
    if check('isvoid'):
        return match('isvoid') and expr_f()
    return expr_g()


def expr_g():
    if check('~'):
        return match('~') and expr_g()
    return expr_h0()


def expr_h0():
    return expr_i0() and expr_h1()


def expr_h1():
    if check('@'):
        return (match('@') and match('type_id') and match('.') and
                match('obj_id') and match('(') and expr_h2() and expr_h1())
    return True


def expr_h2():
    if check(')'):
        return match(')')
    return exprs_0()


def expr_i0():
    return expr_j() and expr_i1()


def expr_i1():
    if check('.'):
        return (match('.') and match('obj_id') and match('(') and expr_i2() and
                expr_i1())
    return True


def expr_i2():
    if check(')'):
        return match(')')
    return exprs_0()


def expr_j():
    if check('('):
        return match('(') and expr_a() and match(')')
    return expr_k0()


def expr_k0():
    if check('obj_id'):
        return match('obj_id') and expr_k1()
    if check('if'):
        return (match('if') and expr_a() and match('then') and expr_a() and
                match('else') and expr_a() and match('fi'))
    if check('while'):
        return (match('while') and expr_a() and match('loop') and expr_a() and
                match('pool'))
    if check('{'):
        return match('{') and expr_a() and match(';') and expr_k3()
    if check('let'):
        return (match('let') and match('obj_id') and match(':') and
                match('type_id') and expr_k4())
    if check('case'):
        return (match('case') and expr_a() and match('of') and match('obj_id')
                and match(':') and match('type_id') and match('=>') and
                expr_a() and match(';') and expr_k6())
    if check('new'):
        return match('new') and match('type_id')
    if check('integer'):
        return match('integer')
    if check('string'):
        return match('string')
    if check('true'):
        return match('true')
    if check('false'):
        return match('false')
    add_syntax_error(['obj_id', 'if', 'while', '{', 'let', 'case', 'new',
                      'integer', 'string', 'true', 'false'])
    return skip_to(['obj_id', 'if', 'while', '{', 'let', 'case', 'new',
                    'integer', 'string', 'true', 'false']) and expr_k0()


def expr_k1():
    if check('('):
        return match('(') and expr_k2()
    return True


def expr_k2():
    if check(')'):
        return match(')')
    return exprs_0()


def expr_k3():
    if check('}'):
        return match('}')
    return exprs_p0()


def expr_k4():
    if check('<-'):
        return match('<-') and expr_a() and expr_k5()
    return expr_k5()


def expr_k5():
    if check(','):
        return (match(',') and match('obj_id') and match(':') and
                match('type_id') and expr_k4())
    if check('in'):
        return match('in') and expr_a()
    add_syntax_error([',', 'in'])
    return skip_to([',', 'in']) and expr_k5()


def expr_k6():
    if check('obj_id'):
        return (match('obj_id') and match(':') and match('type_id') and
                match('=>') and expr_a() and match(';') and expr_k6())
    if check('esac'):
        return match('esac')
    add_syntax_error(['obj_id', 'esac'])
    return skip_to(['obj_id', 'esac']) and expr_k6()


def exprs_0():
    return expr_a() and exprs_1()


def exprs_1():
    if check(','):
        return match(',') and exprs_0()
    if check(')'):
        return match(')')
    add_syntax_error([',', ')'])
    return skip_to([',', ')']) and exprs_1()


def exprs_p0():
    return expr_a() and match(';') and exprs_p1()


def exprs_p1():
    if check('}'):
        return match('}')
    return exprs_p0()


# start the parser
if __name__ == '__main__':
    import sys
    parse(sys.argv[1])
