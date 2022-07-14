"""
`snekcfg` is a light wrapper over `configparser` that offers a more
streamlined user experience. Expected options and their types are predefined
to prevent errors and minimize repetative logic within your codebase. This
allows for simple, direct access to your configuration within your program
without worrying about typos or type conversion.

Example::

    >>> cfg = snekcfg.Config('<filepath>')
    >>> sct = cfg.section('server')
    >>> sct.init('host', default='127.0.0.1')
    >>> sct.init('port', default=1337) # automatically typed as an int
    >>> cfg.init('whitelist.users', ['john', 'eric'], type=list[str])
    >>> cfg.write()
    >>> with open('<filepath>') as f:
    ...     print(f.read())
    [server]
    host = 127.0.0.1
    port = 1337

    [whitelist]
    users = john,eric
    >>> cfg.read()
    >>> cfg['server.port']
    1337 # int
    >>> cfg.section('whitelist')['users']
    ['john', 'eric']
"""
import collections
import configparser

# rename the original so we can use the name
_type = type

ConfigItem = collections.namedtuple('ConfigItem', 'default, type')
ConfigType = collections.namedtuple('ConfigType', 'encode, decode')

class Config:
    """The main configuration object."""
    def __init__(self, *sources):
        """Creates a `Config` object.

        *sources* can be any number of paths or file objects. When calling
        `Config.read` each of these will be read from sequentially. When calling
        `Config.write`, only the first source will be written to.
        """
        self._sources = sources
        self._parser = configparser.ConfigParser(interpolation=None)
        self._items = {}
        self._types = {}

        self._register_default_types()

    def init(self, key, default, typename):
        self._items[key] = ConfigItem(default, typename or _type(default))

        section_name, value_name = self._split_key(key)
        sct = self.section(section_name, create=True)

        sct[value_name] = default

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def options(self, section):
        return self._parser.options(section)

    def items(self, section):
        sct = self.section(section)
        return [(name, sct.get(name)) for name in sct.options()]

    def section(self, section, create=False):
        if create:
            try:
                self._parser.add_section(section)
            except configparser.DuplicateSectionError:
                pass
        return ConfigSection(section, self)

    def sections(self):
        return self._parser.sections()

    def todict(self):
        return {section: dict(self.section(section).items())
            for section in self.sections()}

    ## special methods ##

    def __getitem__(self, key):
        section_name, value_name = self._split_key(key)
        value = self._parser[section_name][value_name]
        typename = self._items[key].type
        return self.decode(value, typename)

    def __setitem__(self, key, value):
        section_name, value_name = self._split_key(key)
        typename = self._items[key].type
        enc_value = self.encode(value, typename)
        self._parser[section_name][value_name] = enc_value

    def __iter__(self):
        yield from self.sections()

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.todict())

    ## persistence ##

    def read(self, *sources):
        for source in sources or self._sources:
            if isinstance(source, str):
                self._parser.read(source)
            else:
                self._parser.read_file(source)

    def write(self, source=None):
        source = source or self._sources[0]
        if isinstance(source, str):
            with open(source, 'w') as f:
                self._parser.write(f)
        else:
            self._parser.write(source)

    def sync(self):
        self.read()
        self.write()

    ## encoding ##

    def encode(self, value, typename):
        typename = str(typename)
        try:
            encode = self._types[typename].encode
        except KeyError:
            raise UnknownType(typename)
        return encode(value)

    def decode(self, value, typename):
        typename = str(typename)
        try:
            decode = self._types[typename].decode
        except KeyError:
            raise UnknownType(typename)
        return decode(value)

    ## types ##

    def register_type(self, typename, encode, decode):
        typename = str(typename)
        self._types[typename] = ConfigType(
            encode or (lambda v: v),
            decode or (lambda v: v),
            )

    def unregister_type(self, typename):
        typename = str(typename)
        del self._types[typename]

    def unregister_all_types(self):
        self._types.clear()

    ## internal ##

    def _register_default_types(self):
        self.register_type(str, None, None)
        self.register_type(int, str, int)
        self.register_type(float, str, float)

        _boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
            '0': False, 'no': False, 'false': False, 'off': False}
        self.register_type(bool,
            lambda x: 'true' if x else 'false',
            lambda x: _boolean_states[x.lower()])

        self.register_type('list[str]',
            lambda v: ','.join(v),
            lambda v: tuple(x.strip() for x in v.split(',')))

        self.register_type('tuple[str, ...]',
            lambda v: ','.join(v),
            lambda v: tuple(x.strip() for x in v.split(',')))
        self.register_type('tuple[int, ...]',
            lambda v: ','.join(str(x) for x in v),
            lambda v: tuple(int(x.strip()) for x in v.split(',')))

    def _split_key(self, key):
        return key.split('.', 1)

class ConfigSection:
    def __init__(self, name, config):
        self._name = name
        self._config = config

    def init(self, name, default, typename=None):
        self._config.init(self._key(name), default, typename)

    def get(self, name, default=None):
        return self._config.get(self._key(name), default)

    def options(self):
        return self._config.options(self._name)

    def items(self):
        return self._config.items(self._name)

    def todict(self):
        return dict(self.items())

    ## special methods ##

    def __getitem__(self, name):
        return self._config[self._key(name)]

    def __setitem__(self, name, value):
        self._config[self._key(name)] = value

    def __iter__(self):
        yield from self.options()

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.todict())

    ## internal ##

    def _key(self, *names):
        return '.'.join((self._name,) + names)

class ConfigError(Exception):
    pass

class UnknownType(ConfigError):
    pass
