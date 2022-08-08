"""
.. include:: README.md

Snek-charming incantations follow ...
"""

import logging
import collections
import configparser

__author__  = 'Miguel Turner'
__version__ = '0.1.0'
__license__ = 'MIT'

# rename the original so we can use the name
_type = type

_Definition = collections.namedtuple('Definition', 'default type')
_CodecType = collections.namedtuple('CodecType', 'encode decode')
_CodecNop = _CodecType(lambda v: v, lambda v: v)

log = logging.getLogger(__name__)

class Config:
    """The main configuration object."""

    def __init__(self, *sources, format=None, codec=None, strict=True, delimiter='.'):
        """Creates a `Config` object.

        *sources* can be any number of paths or file objects. When calling
        `Config.read` each of these will be read from sequentially. When calling
        `Config.write`, only the first source will be written to.

        *format* can be used to set a configuration file format. The default
        is `INIFormat`.

        *codec* can be used to set an object to encode/decode values. The
        default `StringCodec` which converts all values to/from strings.

        When *strict* is `True` (default), an exception is raised when setting
        values for options that were not initialized using `Config.init`.
        Otherwise, a warning is logged.

        The *delimiter* is used to separate section names from option names.
        """
        self._sources = sources
        self._format = format or INIFormat()
        self._codec = codec or StringCodec()
        self._strict = strict
        self._delimiter = delimiter

        self._sections = {}

    def define(self, key, default, type=None):
        """Defines a new option.

        If *type* is not provided, it will be set to the type of the default
        value.
        """
        section, option = self._split_key(key)
        self.section(section).define(option, default, type)

    def get(self, key, default=None):
        """Returns the value of the option at *key*.

        If the option has not been
        defined, returns the *default* value.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def section(self, section):
        """Returns the `Section` object for *section*."""
        return self._sections.get(section, Section(section, self))

    def sections(self):
        """Yields all `Section` objects."""
        yield from self._sections.values()

    def clear(self):
        """Deletes all `Section` objects and their options."""
        self._sections.clear()

    def todict(self, encode=False):
        """Returns a dict of `{'section_name': {'option': <value>}}`.

        If *encode* is `True`, the *value* will be a string.
        """
        return {sct.name: dict(sct.items(encode)) for sct in self}

    ## special methods ##

    def __getitem__(self, key):
        section, option = self._split_key(key)
        return self._sections[section][option]

    def __setitem__(self, key, value):
        section, option = self._split_key(key)
        self._sections[section][option] = value

    def __iter__(self):
        yield from self.sections()

    def __len__(self):
        return len(self._sections())

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.todict())

    ## types ##

    def register_type(self, type, encode, decode):
        self._codec.register_type(type, encode, decode)

    def unregister_type(self, type):
        self._codec.unregister_type(type)

    def unregister_all_types(self):
        self._codec.unregister_all_types()

    ## persistence ##

    def read(self, *sources):
        for source in sources or self._sources:
            try:
                if isinstance(source, str):
                    with open(source, 'r') as f:
                        self._format.read(f, self)
                else:
                    self._format.read(source, self)
            except OSError as e:
                log.warning('failed to open source: %s:\n  %s', source, e)

    def write(self, source=None):
        source = source or self._sources[0]
        if isinstance(source, str):
            with open(source, 'w') as f:
                self._format.write(f, self)
        else:
            self._format.write(source, self)

    def _split_key(self, key):
        return key.split(self._delimiter, 1)

class Section(collections.abc.MutableMapping):
    def __init__(self, name, config):
        self._name = name
        self._config = config

        self._schema = {}
        self._values = {}

    @property
    def name(self):
        return self._name

    def define(self, name, default, type=None):
        type = self._config._codec.typename(type or _type(default))
        self._schema[name] = _Definition(default, type)
        self._values[name] = default

        self._set_section()

    def get(self, name, default=None, encode=False):
        self._strict_check(name)
        value = self._values.get(name, default)
        if encode:
            value = self._encode(name, value)
        return value

    def set(self, name, value, decode=False):
        self._strict_check(name)
        if decode:
            value = self._decode(name, value)
        self._values[name] = value

        self._set_section()

    def getdefault(self, name):
        """Returns the default value for *name*."""
        return self._schema[name].default

    def items(self, encode=False):
        items = super().items()
        if not encode:
            return items
        return [(name, self._encode(name, value)) for name, value in items]

    def clear(self):
        self._schema.clear()
        self._values.clear()

    ## special methods ##

    def __getitem__(self, name):
        self._strict_check(name)
        return self._values[name]

    def __setitem__(self, name, value):
        self._strict_check(name)
        self._values[name] = value

        self._set_section()

    def __delitem__(self, name):
        self._strict_check(name)
        del self._schema[name]
        del self._values[name]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self._values)

    ## internal ##

    def _set_section(self):
        self._config._sections[self.name] = self

    def _encode(self, name, value):
        type = self._schema.get(name, _Definition(None, None)).type
        return self._config._codec.encode(value, type)

    def _decode(self, name, value):
        type = self._schema.get(name, _Definition(None, None)).type
        return self._config._codec.decode(value, type)

    def _strict_check(self, name):
        if name in self._schema:
            return
        elif self._config._strict:
            raise UnknownOption(name)
        else:
            log.warning('unknown option: %s', name)

##
## formats
##

class Format:
    def read(self, file, config):
        raise NotImplementedError('abstract')

    def write(self, file, config):
        raise NotImplementedError('abstract')

class INIFormat(Format):
    """Support for reading/writing INI files using `configparser`.

    *parser* can be used to pass in a custom `configparser.ConfigParser`
        instance. The default instance disables interpolation.
    """
    def __init__(self, parser=None):
        self._parser = parser or configparser.ConfigParser(interpolation=None)

    def read(self, file, config):
        parser = self._parser

        parser.read_file(file)

        for section, options in parser.items():
            sct = config.section(section)
            for name, value in options.items():
                try:
                    sct.set(name, value, decode=True)
                except UnknownOption:
                    log.warning('unknown option: %s', name)
                    continue

        self._clear()

    def write(self, file, config):
        parser = self._parser

        for sct in config:
            parser.add_section(sct.name)
            for name, value in sct.items(encode=True):
                parser[sct.name][name] = value

        parser.write(file)

        self._clear()

    def _clear(self):
        parser = self._parser
        for sct in parser.sections():
            parser.remove_section(sct)

##
## codecs
##

class Codec:
    def __init__(self):
        self._types = {}
        self.register_default_types()

    def encode(self, value, type):
        type = self.typename(type)
        return self._types.get(type, _CodecNop).encode(value)

    def decode(self, value, type):
        type = self.typename(type)
        return self._types.get(type, _CodecNop).decode(value)

    def register_default_types(self):
        pass

    ## types ##

    def typename(self, type):
        return str(type)

    def register_type(self, type, encode, decode):
        typename = self.typename(type)
        self._types[typename] = _CodecType(
            encode or (lambda v: v),
            decode or (lambda v: v),
            )

    def unregister_type(self, type):
        typename = self.typename(type)
        del self._types[typename]

    def unregister_all_types(self):
        self._types.clear()

class StringCodec(Codec):
    def register_default_types(self):
        self.register_type(str, None, None)
        self.register_type(int, str, int)
        self.register_type(float, str, float)

        _boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
            '0': False, 'no': False, 'false': False, 'off': False}
        self.register_type(bool,
            lambda x: 'true' if x else 'false',
            lambda x: _boolean_states[x.lower()])

        def clean_split(v):
            yield from filter(None, (x.strip() for x in v.split(',')))

        self.register_type('set[str]',
            lambda v: ','.join(v),
            lambda v: set(clean_split(v)))
        self.register_type('list[str]',
            lambda v: ','.join(v),
            lambda v: list(clean_split(v)))
        self.register_type('tuple[str, ...]',
            lambda v: ','.join(v),
            lambda v: tuple(clean_split(v)))

        self.register_type('tuple[int, ...]',
            lambda v: ','.join(str(x) for x in v),
            lambda v: tuple(int(x) for x in clean_split(v)))

##
## exceptions
##

class ConfigError(Exception):
    pass

class UnknownOption(ConfigError):
    pass
