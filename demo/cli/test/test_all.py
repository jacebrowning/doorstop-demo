"""Integration tests for the demo.cli package."""

import unittest
from unittest.mock import patch, Mock

import os
import tempfile
import shutil

from demo.cli.main import main
from demo import common
from demo import settings

from demo.cli.test import ENV, REASON, TUTORIAL


@unittest.skipUnless(os.getenv(ENV), REASON)  # pylint: disable=R0904
class TestMain(unittest.TestCase):  # pylint: disable=R0904

    """Integration tests for the 'demo' command."""

    def setUp(self):
        self.cwd = os.getcwd()
        self.temp = tempfile.mkdtemp()
        self.backup = (settings.REFORMAT,
                       settings.CHECK_REF,
                       settings.CHECK_RLINKS)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.temp)
        (settings.REFORMAT,
         settings.CHECK_REF,
         settings.CHECK_RLINKS) = self.backup

    def test_main(self):
        """Verify 'demo' can be called."""
        self.assertIs(None, main([]))

    def test_main_help(self):
        """Verify 'demo --help' can be requested."""
        self.assertRaises(SystemExit, main, ['--help'])

    def test_main_error(self):
        """Verify 'demo' returns an error in an empty directory."""
        os.chdir(self.temp)
        self.assertRaises(SystemExit, main, [])

    def test_main_custom_root(self):
        """Verify 'demo' can be provided a custom root path."""
        os.chdir(self.temp)
        self.assertIs(None, main(['--project', '.']))

    @patch('demo.cli.main._run', Mock(return_value=False))
    def test_exit(self):
        """Verify 'demo' treats False as an error ."""
        self.assertRaises(SystemExit, main, [])

    @patch('demo.cli.main._run', Mock(side_effect=KeyboardInterrupt))
    def test_interrupt(self):
        """Verify 'demo' treats KeyboardInterrupt as an error."""
        self.assertRaises(SystemExit, main, [])

    def test_empty(self):
        """Verify 'demo' can be run in a working copy with no docs."""
        os.mkdir(os.path.join(self.temp, '.mockvcs'))
        os.chdir(self.temp)
        self.assertIs(None, main([]))
        self.assertTrue(settings.REFORMAT)
        self.assertTrue(settings.CHECK_REF)
        self.assertTrue(settings.CHECK_RLINKS)

    def test_options(self):
        """Verify 'demo' can be run with options."""
        os.mkdir(os.path.join(self.temp, '.mockvcs'))
        os.chdir(self.temp)
        self.assertIs(None, main(['--no-reformat',
                                  '--no-ref-check',
                                  '--no-rlinks-check']))
        self.assertFalse(settings.REFORMAT)
        self.assertFalse(settings.CHECK_REF)
        self.assertFalse(settings.CHECK_RLINKS)

    @patch('demo.cli.main.gui', Mock(return_value=True))
    def test_gui(self):
        """Verify 'demo --gui' launches the GUI."""
        self.assertIs(None, main(['--gui']))


@unittest.skipUnless(os.getenv(ENV), REASON)  # pylint: disable=R0904
class TestNew(unittest.TestCase):  # pylint: disable=R0904

    """Integration tests for the 'demo new' command."""

    def setUp(self):
        self.cwd = os.getcwd()
        self.temp = tempfile.mkdtemp()

    def tearDown(self):
        os.chdir(self.cwd)
        if os.path.exists(self.temp):
            shutil.rmtree(self.temp)

    def test_new(self):
        """Verify 'demo new' can be called."""
        self.assertIs(None, main(['new', '_TEMP', self.temp, '-p', 'REQ']))

    def test_new_error(self):
        """Verify 'demo new' returns an error with an unknown parent."""
        self.assertRaises(SystemExit, main,
                          ['new', '_TEMP', self.temp, '-p', 'UNKNOWN'])


@unittest.skipUnless(os.getenv(ENV), REASON)  # pylint: disable=R0904
class TestAdd(unittest.TestCase):  # pylint: disable=R0904

    """Integration tests for the 'demo add' command."""

    @classmethod
    def setUpClass(cls):
        last = sorted(os.listdir(TUTORIAL))[-1]
        number = int(last.replace('TUT', '').replace('.yml', '')) + 1
        filename = "TUT{}.yml".format(str(number).zfill(3))
        cls.path = os.path.join(TUTORIAL, filename)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_add(self):
        """Verify 'demo add' can be called."""
        self.assertIs(None, main(['add', 'TUT']))
        self.assertTrue(os.path.isfile(self.path))

    def test_add_error(self):
        """Verify 'demo add' returns an error with an unknown prefix."""
        self.assertRaises(SystemExit, main, ['add', 'UNKNOWN'])


@unittest.skipUnless(os.getenv(ENV), REASON)  # pylint: disable=R0904
class TestRemove(unittest.TestCase):  # pylint: disable=R0904

    """Integration tests for the 'demo remove' command."""

    ITEM = os.path.join(TUTORIAL, 'TUT003.yml')

    def setUp(self):
        with open(self.ITEM, 'r') as item:
            self.backup = item.read()

    def tearDown(self):
        with open(self.ITEM, 'w') as item:
            item.write(self.backup)

    def test_remove(self):
        """Verify 'demo remove' can be called."""
        self.assertIs(None, main(['remove', 'tut3']))
        self.assertFalse(os.path.exists(self.ITEM))

    def test_remove_error(self):
        """Verify 'demo remove' returns an error on unknown item IDs."""
        self.assertRaises(SystemExit, main, ['remove', 'tut9999'])


@unittest.skipUnless(os.getenv(ENV), REASON)  # pylint: disable=R0904
class TestLink(unittest.TestCase):  # pylint: disable=R0904

    """Integration tests for the 'demo link' command."""

    ITEM = os.path.join(TUTORIAL, 'TUT003.yml')

    def setUp(self):
        with open(self.ITEM, 'r') as item:
            self.backup = item.read()

    def tearDown(self):
        with open(self.ITEM, 'w') as item:
            item.write(self.backup)

    def test_link(self):
        """Verify 'demo link' can be called."""
        self.assertIs(None, main(['link', 'tut3', 'req2']))

    def test_link_unknown_child(self):
        """Verify 'demo link' returns an error with an unknown child."""
        self.assertRaises(SystemExit, main, ['link', 'unknown3', 'req2'])
        self.assertRaises(SystemExit, main, ['link', 'tut9999', 'req2'])

    def test_link_unknown_parent(self):
        """Verify 'demo link' returns an error with an unknown parent."""
        self.assertRaises(SystemExit, main, ['link', 'tut3', 'unknown2'])
        self.assertRaises(SystemExit, main, ['link', 'tut3', 'req9999'])


@unittest.skipUnless(os.getenv(ENV), REASON)  # pylint: disable=R0904
class TestUnlink(unittest.TestCase):  # pylint: disable=R0904

    """Integration tests for the 'demo unlink' command."""

    ITEM = os.path.join(TUTORIAL, 'TUT003.yml')

    def setUp(self):
        with open(self.ITEM, 'r') as item:
            self.backup = item.read()
        main(['link', 'tut3', 'req2'])  # create a temporary link

    def tearDown(self):
        with open(self.ITEM, 'w') as item:
            item.write(self.backup)

    def test_unlink(self):
        """Verify 'demo unlink' can be called."""
        self.assertIs(None, main(['unlink', 'tut3', 'req2']))

    def test_unlink_unknown_child(self):
        """Verify 'demo unlink' returns an error with an unknown child."""
        self.assertRaises(SystemExit, main, ['unlink', 'unknown3', 'req2'])
        self.assertRaises(SystemExit, main, ['link', 'tut9999', 'req2'])

    def test_unlink_unknown_parent(self):
        """Verify 'demo unlink' returns an error with an unknown parent."""
        self.assertRaises(SystemExit, main, ['unlink', 'tut3', 'unknown2'])
        self.assertRaises(SystemExit, main, ['unlink', 'tut3', 'req9999'])


@unittest.skipUnless(os.getenv(ENV), REASON)  # pylint: disable=R0904
class TestEdit(unittest.TestCase):  # pylint: disable=R0904

    """Integration tests for the 'demo edit' command."""

    @patch('demo.core.tree._open')
    def test_edit(self, mock_open):
        """Verify 'demo edit' can be called."""
        self.assertIs(None, main(['edit', 'tut2']))
        path = os.path.join(TUTORIAL, 'TUT002.yml')
        mock_open.assert_called_once_with(os.path.normpath(path), tool=None)

    def test_edit_error(self):
        """Verify 'demo edit' returns an error with an unknown ID."""
        self.assertRaises(SystemExit, main, ['edit', 'req9999'])


@unittest.skipUnless(os.getenv(ENV), REASON)  # pylint: disable=R0904
class TestPublish(unittest.TestCase):  # pylint: disable=R0904

    """Integration tests for the 'demo publish' command."""

    def setUp(self):
        self.cwd = os.getcwd()
        self.temp = tempfile.mkdtemp()

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.temp)

    def test_publish_text(self):
        """Verify 'demo publish' can create text output."""
        self.assertIs(None, main(['publish', 'tut', '--width', '75']))

    def test_publish_text_file(self):
        """Verify 'demo publish' can create a text file."""
        path = os.path.join(self.temp, 'req.txt')
        self.assertIs(None, main(['publish', 'req', path]))
        self.assertTrue(os.path.isfile(path))

    def test_publish_markdown(self):
        """Verify 'demo publish' can create Markdown output."""
        self.assertIs(None, main(['publish', 'req', '--markdown']))

    def test_publish_markdown_file(self):
        """Verify 'demo publish' can create a Markdown file."""
        path = os.path.join(self.temp, 'req.md')
        self.assertIs(None, main(['publish', 'req', path]))
        self.assertTrue(os.path.isfile(path))

    def test_publish_html(self):
        """Verify 'demo publish' can create HTML output."""
        self.assertIs(None, main(['publish', 'hlt', '--html']))

    def test_publish_html_file(self):
        """Verify 'demo publish' can create an HTML file."""
        path = os.path.join(self.temp, 'req.html')
        self.assertIs(None, main(['publish', 'req', path]))
        self.assertTrue(os.path.isfile(path))

    def test_report_error(self):
        """Verify 'demo publish' returns an error in an empty folder."""
        os.chdir(self.temp)
        self.assertRaises(SystemExit, main, ['publish', 'req'])


@patch('demo.cli.main._run', Mock(return_value=True))  # pylint: disable=R0904
class TestLogging(unittest.TestCase):  # pylint: disable=R0904

    """Integration tests for the DoorstopDemo CLI logging."""

    def test_verbose_1(self):
        """Verify verbose level 1 can be set."""
        self.assertIs(None, main(['-v']))

    def test_verbose_2(self):
        """Verify verbose level 2 can be set."""
        self.assertIs(None, main(['-vv']))

    def test_verbose_3(self):
        """Verify verbose level 3 can be set."""
        self.assertIs(None, main(['-vvv']))

    def test_verbose_4(self):
        """Verify verbose level 4 can be set."""
        self.assertIs(None, main(['-vvvv']))

    def test_verbose_5(self):
        """Verify verbose level 5 cannot be set."""
        self.assertIs(None, main(['-vvvvv']))
        self.assertEqual(4, common.VERBOSITY)
