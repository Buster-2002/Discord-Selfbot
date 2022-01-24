# -*- coding: utf-8 -*-
from discord.ext.commands import CommandError


class NoPasswordSet(CommandError):
    '''Exception for when a command where a password is needed, when it is not set, is being used'''


class OnlyDM(CommandError):
    '''Exception for when a command was trying to be used that is only available in DMs'''


class NoFFMPEG(CommandError):
    '''Exception for when ffmpeg wasn't found in the systems path'''


class InvalidExtension(CommandError):
    '''Exception for when an invalid extension was attempted to be loaded'''
    def __init__(self, name: str, *args, **kwargs):
        self.name = name
        super().__init__(*args, **kwargs)


class CommandExists(CommandError):
    '''Exception for when a custom comamnd is attempted to be added, when it already exists as a default one'''
    def __init__(self, name: str, *args, **kwargs):
        self.name = name
        super().__init__(*args, **kwargs)


class CommandDoesntExist(CommandError):
    '''Exception for when a custom command is attempted to be deleted, when it doesn't exist as one'''
    def __init__(self, name: str, *args, **kwargs):
        self.name = name
        super().__init__(*args, **kwargs)


class BadSettings(CommandError):
    '''Exception for when bad selfbot settings are encountered'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class BadUrl(CommandError):
    '''Exception for when an argument to the ImageConverter couldn\'t result in any image URL'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class BadToken(CommandError):
    '''Exception for when an invalid Discord token has been provided to the TokenConverter'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DataNotFound(CommandError):
    '''Exception for when expected data from an API call or local files does not exist'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class BytesNotFound(CommandError):
    '''Exception for when expected bytes for fileops werent found'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class BadTime(CommandError):
    '''Exception for when an invalid arg has been passed to the TimeConverter or DateConverter'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class NotEnabled(CommandError):
    '''Exception for when some internal bot setting is not enabled'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
