"""
.. include:: README.md

Snek-charming incantations follow ...
"""

import logging
from configparser import ConfigParser

from typing import (Any, Callable, Dict, Generator, List, MutableMapping,
                    NamedTuple, Optional, Set, TextIO, Tuple, Union, ValuesView)

__author__  = 'Miguel Turner'
__version__ = '0.1.1'
__license__ = 'MIT'

# rename the original so we can use the name
_type = type

log = logging.getLogger(__name__)

class Config:
    """The main configuration object."""

    def __init__(self, *sources: Union[str, TextIO], format: Optional["Format"]=None,
            codec: Optional["Codec"]=None, strict: bool=True, delimiter: str='.'
        ):
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
        Otherwise, a warning is logged. This option can be overridden by
        individual sections.

        The *delimiter* is used to separate section names from option names.
        """
        self._sources = sources
        self._format = format or INIFormat()
        self._codec = codec or StringCodec()
        self._delimiter = delimiter

        self.strict = strict

        self._sections: Dict[str, Section] = {}

    def define(self, key: str, default: Any, type: Any=None) -> None:
        """Defines a new option.

        If *type* is not provided, it will be set to the type of the default
        value.
        """
        try:
            section, option = self._split_key(key)
        except ValueError:
            raise InvalidKey('key name must include section name')
        self.section(section).define(option, default, type)

    def get(self, key: str, default: Any=None) -> Any:
        """Returns the value of the option at *key*.

        If the option has not been
        defined, returns the *default* value.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def section(self, name: str, strict: Optional[bool]=None) -> "Section":
        """Returns the `Section` object for *name*.

        *strict* can be used to override the *strict* setting for this section.
        """
        return self._sections.setdefault(name, Section(self, name, strict))

    def sections(self) -> ValuesView["Section"]:
        """Returns all `Section` objects."""
        return self._sections.values()

    def clear(self) -> None:
        """Deletes all `Section` objects and their options."""
        self._sections.clear()

    def todict(self, encode: bool=False) -> Dict[str, Dict[str, Any]]:
        """Returns a dict of `{'section_name': {'option': <value>}}`.

        If *encode* is `True`, the *value* will be a string.
        """
        method = 'encoded_items' if encode else 'items'
        return {sct.name: dict(getattr(sct, method)()) for sct in self}

    ## special methods ##

    def __getitem__(self, key: str) -> Any:
        section, option = self._split_key(key)
        return self._sections[section][option]

    def __setitem__(self, key: str, value: Any) -> None:
        section, option = self._split_key(key)
        self._sections[section][option] = value

    def __iter__(self) -> Generator["Section", None, None]:
        yield from self.sections()

    def __len__(self) -> int:
        return len(self._sections)

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, self.todict())

    ## types ##

    def register_type(self, type: Any,
        encode: "EncodeFunction", decode: "DecodeFunction"
        ) -> None:
        self._codec.register_type(type, encode, decode)

    def unregister_type(self, type: Any) -> None:
        self._codec.unregister_type(type)

    def unregister_all_types(self) -> None:
        self._codec.unregister_all_types()

    ## persistence ##

    def read(self, *sources: Union[str, TextIO]) -> None:
        for source in sources or self._sources:
            try:
                if isinstance(source, str):
                    with open(source, 'r') as f:
                        self._format.read(f, self)
                else:
                    self._format.read(source, self)
            except OSError as e:
                log.warning('failed to open source: %s:\n  %s', source, e)

    def write(self, source: Union[str, TextIO, None]=None) -> None:
        source = source or self._sources[0]
        if isinstance(source, str):
            with open(source, 'w') as f:
                self._format.write(f, self)
        else:
            self._format.write(source, self)

    def _split_key(self, key: str) -> List[str]:
        return key.split(self._delimiter, 1)

class Section(MutableMapping[str, Any]):
    def __init__(self, config: Config, name: str, strict: Optional[bool]=None):
        self._config = config
        self._name = name

        self._strict = strict
        self._schema: Dict[str, _OptionInfo] = {}
        self._values: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def strict(self) -> bool:
        return self._config.strict if self._strict is None else self._strict

    @strict.setter
    def strict(self, strict: bool) -> None:
        self._strict = strict

    def define(self, name: str, default: Any, type: Any=None) -> None:
        type = self._config._codec.typename(type or _type(default))
        self._schema[name] = _OptionInfo(default, type)
        self._values[name] = default

    def get(self, name: str, default: Any=None, encode: bool=False) -> Any:
        self._strict_check(name)
        value = self._values.get(name, default)
        if encode:
            value = self._encode(name, value)
        return value

    def set(self, name: str, value: Any, decode: bool=False) -> None:
        self._strict_check(name)
        if decode:
            value = self._decode(name, value)
        self._values[name] = value

    def getdefault(self, name: str) -> Any:
        """Returns the default value for *name*."""
        return self._schema[name].default

    def encoded_items(self) -> Generator[Tuple[str, Any], None, None]:
        return ((name, self._encode(name, value))
            for name, value in self.items())

    def clear(self) -> None:
        self._schema.clear()
        self._values.clear()

    ## special methods ##

    def __getitem__(self, name: str) -> Any:
        self._strict_check(name)
        return self._values[name]

    def __setitem__(self, name: str, value: Any) -> None:
        self._strict_check(name)
        self._values[name] = value

    def __delitem__(self, name: str) -> None:
        self._strict_check(name)
        del self._schema[name]
        del self._values[name]

    def __iter__(self) -> Generator[str, None, None]:
        return (key for key in self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, self._values)

    ## internal ##

    def _encode(self, name: str, value: Any) -> str:
        type = self._schema.get(name, _OptionInfo()).type
        return self._config._codec.encode(value, type)

    def _decode(self, name: str, value: str) -> Any:
        type = self._schema.get(name, _OptionInfo()).type
        return self._config._codec.decode(value, type)

    def _strict_check(self, name: str) -> None:
        if self.strict and name not in self._schema:
            raise UnknownOption(name)

##
## formats
##

class Format:
    def read(self, file: TextIO, config: Config) -> None:
        raise NotImplementedError('abstract')

    def write(self, file: TextIO, config: Config) -> None:
        raise NotImplementedError('abstract')

class INIFormat(Format):
    """Support for reading/writing INI files using `configparser`.

    *parser* can be used to pass in a custom `configparser.ConfigParser`
        instance. The default instance disables interpolation.
    """
    def __init__(self, parser: Optional[ConfigParser]=None):
        self._parser = parser or ConfigParser(interpolation=None)

    def read(self, file: TextIO, config: Config) -> None:
        parser = self._parser

        parser.read_file(file)

        for section, options in parser.items():
            if not options:
                continue

            sct = config.section(section)
            for name, value in options.items():
                try:
                    sct.set(name, value, decode=True)
                except UnknownOption:
                    log.warning('unknown option: %s', name)
                    continue

        self._clear()

    def write(self, file: TextIO, config: Config) -> None:
        parser = self._parser

        for sct in config:
            parser.add_section(sct.name)
            for name, value in sct.encoded_items():
                parser[sct.name][name] = value

        parser.write(file)

        self._clear()

    def _clear(self) -> None:
        parser = self._parser
        for sct in parser.sections():
            parser.remove_section(sct)

##
## codecs
##

class Codec:
    def __init__(self) -> None:
        self._types: Dict[str, _CodecInfo] = {}
        self.register_default_types()

    def encode(self, value: Any, type: Any) -> str:
        type = self.typename(type)
        info = self._types.get(type, _CodecInfo())
        return info.encode(value) if info.encode else str(value)

    def decode(self, value: str, type: Any) -> Any:
        type = self.typename(type)
        info = self._types.get(type, _CodecInfo())
        return info.decode(value) if info.decode else value

    def register_default_types(self) -> None:
        pass

    ## types ##

    def typename(self, type: Any) -> str:
        return str(type)

    def register_type(self, type: Any,
        encode: Optional["EncodeFunction"], decode: Optional["DecodeFunction"],
        ) -> None:
        typename = self.typename(type)
        self._types[typename] = _CodecInfo(
            encode or (lambda v: str(v)),
            decode or (lambda v: v),
            )

    def unregister_type(self, type: Any) -> None:
        typename = self.typename(type)
        del self._types[typename]

    def unregister_all_types(self) -> None:
        self._types.clear()

class StringCodec(Codec):
    def register_default_types(self) -> None:
        self.register_type(str, None, None)
        self.register_type(int, str, int)
        self.register_type(float, str, float)

        _boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
            '0': False, 'no': False, 'false': False, 'off': False}
        self.register_type(bool,
            lambda x: 'true' if x else 'false',
            lambda x: _boolean_states[x.lower()])

        def clean_split(v: str) -> Generator[str, None, None]:
            yield from filter(None, (x.strip() for x in v.split(',')))

        self.register_type(Set[str],
            lambda v: ','.join(v),
            lambda v: set(clean_split(v)))
        self.register_type(List[str],
            lambda v: ','.join(v),
            lambda v: list(clean_split(v)))
        self.register_type(Tuple[str, ...],
            lambda v: ','.join(v),
            lambda v: tuple(clean_split(v)))

        self.register_type(Tuple[int, ...],
            lambda v: ','.join(str(x) for x in v),
            lambda v: tuple(int(x) for x in clean_split(v)))

##
## exceptions
##

class ConfigError(Exception):
    pass

class UnknownOption(ConfigError):
    pass

class InvalidKey(ConfigError):
    pass

##
## internal
##

EncodeFunction = Callable[[Any], str]
DecodeFunction = Callable[[str], Any]

class _OptionInfo(NamedTuple):
    default: Any = None
    type: Optional[str] = None

class _CodecInfo(NamedTuple):
    encode: Optional[EncodeFunction] = None
    decode: Optional[DecodeFunction] = None
