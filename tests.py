import unittest

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

if __name__ == '__main__':
    unittest.main()
