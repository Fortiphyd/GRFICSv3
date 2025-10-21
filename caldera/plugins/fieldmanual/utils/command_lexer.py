from pygments.lexer import RegexLexer, bygroups
from pygments.token import Keyword, Literal, Name, Punctuation, Whitespace, Text


class CalderaCommandLexer(RegexLexer):
    name = "CalderaCommand"
    aliases = ["caldera"]
    filenames = []

    tokens = {
        "root": [
            # Match the executable
            (r'(?:\./|\.\\)(?:[\w-]+(?:/[\w-]+)*/?)(?:[\w-]+(?:\.[\w]+)?)', Name.Function),

            # Match the #{fact} pattern
            (r"(\#\{)([^\}]+)(\})", bygroups(Punctuation, Keyword, Punctuation)),

            # Match command line flags
            (r"(-{1,2}[\w]+(?:-[\w]+)*=?)([\w\.\-]+)?", bygroups(Name.Variable, Literal.String)),

            (r'"([^"]*)"', Literal.String),
            (r"'([^']*)'", Literal.String),
            (r"[\w]+(?:-[\w]+)*", Literal.String),

            (r"\b\d+(\.\d+)?\b", Literal.Number),

            (r"\s+", Whitespace),

            (r".", Text),
        ],
    }
