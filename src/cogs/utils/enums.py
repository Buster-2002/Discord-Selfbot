from enum import Enum


class _StrIsValue:
    def __str__(self) -> str:
        return self.value


class AnimationType(Enum):
    cycle_sentence = 1
    flush_char     = 2
    flush_word     = 3
    static         = 4


class AIDataType(_StrIsValue, Enum):
    content_moderation      = 'content-moderation'
    densecap                = 'densecap'
    demographic_recognition = 'demographic-recognition'
    neural_talk             = 'neuraltalk'
    neural_style            = 'neural-style'
    deep_dream              = 'deepdream'
    colorize                = 'colorizer'
    summarize               = 'summarization'
    sentiment_analysis      = 'sentiment-analysis'


class ServerLogType(_StrIsValue, Enum):
    edit   = 'edit'
    delete = 'delete'


class WebmEditType(_StrIsValue, Enum):
    expand   = 'expand'
    negative = 'negative'
    zero     = 'zero'


class JokeType(_StrIsValue, Enum):
    dark          = 'Dark'
    pun           = 'Pun'
    programming   = 'Programming'
    miscellaneous = 'Miscellaneous'
    christmas     = 'Christmas'
    spooky        = 'Spooky'


class ProxyType(_StrIsValue, Enum):
    http   = 'http'
    https  = 'https'
    socks4 = 'socks4'
    socks5 = 'socks5'
