import io
import unittest
from typing import List, Set, Tuple

import snekcfg

class TestConfig(unittest.TestCase):
    def test_init(self) -> None:
        cfg = snekcfg.Config()

        self.assertEqual(list(cfg.sections()), [])
        self.assertEqual(cfg.todict(), {})
        self.assertEqual(list(cfg), [])

    def test_define(self) -> None:
        cfg = snekcfg.Config()
        cfg.define('test.int', 3)
        cfg.define('test.str', 'sushki')

        self.assertEqual(cfg.todict(), {'test': {'int': 3, 'str': 'sushki'}})
        self.assertEqual(cfg['test.int'], 3)
        self.assertEqual(cfg['test.str'], 'sushki')

    def test_section(self) -> None:
        cfg = snekcfg.Config()
        sct = cfg.section('test')

        sct.define('int', 3)

        self.assertEqual(sct['int'], 3)

    def test_strict(self) -> None:
        cfg = snekcfg.Config()
        sct = cfg.section('test')
        sct.define('int', 3)

        with self.assertRaises(snekcfg.UnknownOption):
            sct['xyz'] = 3

        sct.strict = False
        sct['xyz'] = 3

        self.assertEqual(cfg.todict(), {'test': {'int': 3, 'xyz': 3}})

    def test_codecs(self) -> None:
        cfg = snekcfg.Config()
        sct = cfg.section('test')
        sct.define('int', '3', int)

        # no decoding on define
        self.assertEqual(sct['int'], '3')

        # no decoding on direct set
        sct['int'] = '3'
        self.assertEqual(sct['int'], '3')

        sct.set('int', '3', decode=True)
        self.assertEqual(sct['int'], 3)

        self.assertEqual(sct.get('int'), 3)
        self.assertEqual(sct.get('int', encode=True), '3')

    def test_write(self) -> None:
        cfg = snekcfg.Config()
        cfg.define('a.int', 1)

        s = io.StringIO()
        cfg.write(s)

        self.assertEqual(s.getvalue(), "[a]\nint = 1\n\n")

    def test_set_type(self) -> None:
        cfg = snekcfg.Config()
        sct = cfg.section('test')
        sct.define('value', {}, Set[str])

        s = io.StringIO('[test]\nvalue =   a,b  , c, d   ')
        cfg.read(s)

        self.assertEqual(sct['value'], set('abcd'))

    def test_list_type(self) -> None:
        cfg = snekcfg.Config()
        sct = cfg.section('test')
        sct.define('value', [], List[str])

        s = io.StringIO('[test]\nvalue =   a,b  , c, d   ')
        cfg.read(s)

        self.assertEqual(sct['value'], list('abcd'))

    def test_tuple_type(self) -> None:
        cfg = snekcfg.Config()
        sct = cfg.section('test')
        sct.define('value', (), Tuple[str, ...])

        s = io.StringIO('[test]\nvalue =   a,b  , c, d   ')
        cfg.read(s)

        self.assertEqual(sct['value'], tuple('abcd'))


if __name__ == '__main__':
    unittest.main()
