#!/usr/bin/env python

"""Command-line interface for DoorstopDemo."""

import os
import sys
import argparse
import logging

from demo import CLI, VERSION
from demo.gui.main import _run as gui
from demo.core.tree import build
from demo.core import report
from demo import common
from demo.common import DemoError, HelpFormatter, WarningFormatter
from demo import settings


def main(args=None):  # pylint: disable=R0915
    """Process command-line arguments and run the program."""
    # Shared options
    debug = argparse.ArgumentParser(add_help=False)
    debug.add_argument('-j', '--project', metavar='PATH',
                       help="path to the root of the project")
    debug.add_argument('-V', '--version', action='version', version=VERSION)
    debug.add_argument('-v', '--verbose', action='count', default=0,
                       help="enable verbose logging")
    shared = {'formatter_class': HelpFormatter, 'parents': [debug]}

    # Main parser
    parser = argparse.ArgumentParser(prog=CLI, description=__doc__, **shared)
    parser.add_argument('-F', '--no-reformat', action='store_true',
                        help="do not reformat item files during validation")
    parser.add_argument('-R', '--no-ref-check', action='store_true',
                        help="do not validate external file references")
    parser.add_argument('-L', '--no-rlinks-check', action='store_true',
                        help="do not validate reverse links")
    parser.add_argument('-g', '--gui', action='store_true',
                        help="launch the graphical user interface")
    subs = parser.add_subparsers(help="", dest='command', metavar="<command>")

    # New subparser
    sub = subs.add_parser('new',
                          help="create a new document directory",
                          **shared)
    sub.add_argument('prefix', help="document prefix for new item IDs")
    sub.add_argument('root', help="path to a directory for item files")
    sub.add_argument('-p', '--parent', help="prefix for parent item IDS")
    sub.add_argument('-d', '--digits', help="number of digits in item IDs")

    # Add subparser
    sub = subs.add_parser('add',
                          help="create an item file in a document directory",
                          **shared)
    sub.add_argument('prefix',
                     help="document prefix for the new item")

    # Remove subparser
    sub = subs.add_parser('remove',
                          help="remove an item file from a document directory",
                          **shared)
    sub.add_argument('id', metavar='ID',
                     help="item ID to remove from its document")

    # Link subparser
    sub = subs.add_parser('link',
                          help="add a new link between two items",
                          **shared)
    sub.add_argument('child',
                     help="child item ID to link to the parent")
    sub.add_argument('parent',
                     help="parent item ID to link from the child")

    # Unlink subparser
    sub = subs.add_parser('unlink',
                          help="remove a link between two items",
                          **shared)
    sub.add_argument('child',
                     help="child item ID to unlink from parent")
    sub.add_argument('parent',
                     help="parent item ID child is linked to")

    # Edit subparser
    sub = subs.add_parser('edit',
                          help="open an existing item file for editing",
                          **shared)
    sub.add_argument('id', metavar='ID', help="item ID to open for editing")
    sub.add_argument('-t', '--tool', metavar='PROGRAM',
                     help="text editor to open the document item")

    # Publish subparser
    sub = subs.add_parser('publish',
                          help="publish a document as text or another format",
                          **shared)
    sub.add_argument('prefix', help="prefix of document to publish")
    sub.add_argument('path', nargs='?', help="path of published file")
    sub.add_argument('-m', '--markdown', action='store_true',
                     help="output Markdown instead of raw text")
    sub.add_argument('-H', '--html', action='store_true',
                     help="output HTML converted from Markdown")
    sub.add_argument('-w', '--width', type=int,
                     help="limit line width on text output")

    # Parse arguments
    args = parser.parse_args(args=args)

    # Configure logging
    _configure_logging(args.verbose)

    # Run the program
    if args.gui:
        logging.debug("launching GUI...")
        function = gui
    elif args.command:
        logging.debug("launching command '{}'...".format(args.command))
        function = globals()['_run_' + args.command]
    else:
        logging.debug("launching main command...")
        function = _run
    try:
        success = function(args, os.getcwd(), parser.error)
    except KeyboardInterrupt:
        logging.debug("command cancelled")
        success = False
    if success:
        logging.debug("command succeeded")
    else:
        logging.debug("command failed")
        sys.exit(1)


def _configure_logging(verbosity=0):
    """Configure logging using the provided verbosity level (0+)."""
    assert common.STR_VERBOSITY == 3
    assert common.MAX_VERBOSITY == 4

    # Configure the logging level and format
    if verbosity == 0:
        level = settings.DEFAULT_LOGGING_LEVEL
        default_format = settings.DEFAULT_LOGGING_FORMAT
        verbose_format = settings.VERBOSE_LOGGING_FORMAT
    elif verbosity == 1:
        level = settings.VERBOSE_LOGGING_LEVEL
        default_format = settings.DEFAULT_LOGGING_FORMAT
        verbose_format = settings.VERBOSE_LOGGING_FORMAT
    elif verbosity == 2:
        level = settings.VERBOSE_LOGGING_LEVEL
        default_format = verbose_format = settings.VERBOSE_LOGGING_FORMAT
    elif verbosity == 3:
        level = settings.VERBOSE2_LOGGING_LEVEL
        default_format = verbose_format = settings.VERBOSE_LOGGING_FORMAT
    else:
        level = settings.VERBOSE2_LOGGING_LEVEL
        default_format = verbose_format = settings.VERBOSE2_LOGGING_FORMAT

    # Set a custom formatter
    logging.basicConfig(level=level)
    formatter = WarningFormatter(default_format, verbose_format)
    logging.root.handlers[0].setFormatter(formatter)

    # Warn about excessive verbosity
    if verbosity > common.MAX_VERBOSITY:
        msg = "maximum verbosity level is {}".format(common.MAX_VERBOSITY)
        logging.warn(msg)
        common.VERBOSITY = common.MAX_VERBOSITY
    else:
        common.VERBOSITY = verbosity


def _run(args, cwd, err):  # pylint: disable=W0613
    """Process arguments and run the `demo` subcommand.

    @param args: Namespace of CLI arguments
    @param cwd: current working directory
    @param err: function to call for CLI errors

    """
    # Configure validation settings
    if args.no_reformat is not None:
        settings.REFORMAT = not args.no_reformat
    if args.no_ref_check is not None:
        settings.CHECK_REF = not args.no_ref_check
    if args.no_rlinks_check is not None:
        settings.CHECK_CHILD_LINKS = not args.no_rlinks_check

    # Validate the tree
    try:
        tree = build(cwd, root=args.project)
        tree.load()
        valid = tree.valid()
    except DemoError as error:
        logging.error(error)
        return False
    else:
        if tree and valid:
            print("valid tree: {}".format(tree))
        return valid


def _run_new(args, cwd, _):
    """Process arguments and run the `demo new` subcommand.

    @param args: Namespace of CLI arguments
    @param cwd: current working directory
    @param err: function to call for CLI errors

    """
    try:
        tree = build(cwd, root=args.project)
        document = tree.new(args.root, args.prefix,
                            parent=args.parent, digits=args.digits)
    except DemoError as error:
        logging.error(error)
        return False
    else:
        print("created document: {}".format(document.prefix_relpath))
        return True


def _run_add(args, cwd, _):
    """Process arguments and run the `demo add` subcommand.

    @param args: Namespace of CLI arguments
    @param cwd: current working directory
    @param err: function to call for CLI errors

    """
    try:
        tree = build(cwd, root=args.project)
        item = tree.add(args.prefix)
    except DemoError as error:
        logging.error(error)
        return False
    else:
        print("added item: {}".format(item.id_relpath))
        return True


def _run_remove(args, cwd, _):
    """Process arguments and run the `demo remove` subcommand.

    @param args: Namespace of CLI arguments
    @param cwd: current working directory
    @param err: function to call for CLI errors

    """
    try:
        tree = build(cwd, root=args.project)
        item = tree.remove(args.id)
    except DemoError as error:
        logging.error(error)
        return False
    else:
        print("removed item: {}".format(item.id_relpath))
        return True


def _run_link(args, cwd, _):
    """Process arguments and run the `demo link` subcommand.

    @param args: Namespace of CLI arguments
    @param cwd: current working directory
    @param err: function to call for CLI errors

    """
    try:
        tree = build(cwd, root=args.project)
        child, parent = tree.link(args.child, args.parent)
    except DemoError as error:
        logging.error(error)
        return False
    else:
        print("linked item: {} -> {}".format(child.id_relpath,
                                             parent.id_relpath))
        return True


def _run_unlink(args, cwd, _):
    """Process arguments and run the `demo unlink` subcommand.

    @param args: Namespace of CLI arguments
    @param cwd: current working directory
    @param err: function to call for CLI errors

    """
    try:
        tree = build(cwd, root=args.project)
        child, parent = tree.unlink(args.child, args.parent)
    except DemoError as error:
        logging.error(error)
        return False
    else:
        print("unlinked item: {} -> {}".format(child.id_relpath,
                                               parent.id_relpath))
        return True


def _run_edit(args, cwd, _):
    """Process arguments and run the `demo edit` subcommand.

    @param args: Namespace of CLI arguments
    @param cwd: current working directory
    @param err: function to call for CLI errors

    """
    try:
        tree = build(cwd, root=args.project)
        item = tree.edit(args.id, tool=args.tool, launch=True)
    except DemoError as error:
        logging.error(error)
        return False
    else:
        print("opened item: {}".format(item.id_relpath))
        return True


def _run_publish(args, cwd, _):
    """Process arguments and run the `demo report` subcommand.

    @param args: Namespace of CLI arguments
    @param cwd: current working directory
    @param err: function to call for CLI errors

    """
    try:
        tree = build(cwd, root=args.project)
        document = tree.find_document(args.prefix)
    except DemoError as error:
        logging.error(error)
        return False
    else:

        kwargs = {'ignored': tree.vcs.ignored}
        if args.width:
            kwargs['width'] = args.width

        if args.path:
            ext = os.path.splitext(args.path)[-1]
        if args.markdown:
            ext = '.md'
        elif args.html:
            ext = '.html'
        elif not args.path:
            ext = '.txt'

        if args.path:
            print("publishing {} to {}...".format(document, args.path))
            report.publish(document, args.path, ext, **kwargs)
        else:
            for line in report.lines(document, ext, **kwargs):
                print(line)

        return True


if __name__ == '__main__':  # pragma: no cover, manual test
    main()
