"""Compiles the DoorstopDemo document hierarchy."""

import os
import sys
import shutil
import subprocess
import logging
from itertools import chain

from demo.core.base import clear_document_cache, clear_item_cache
from demo.common import DemoError, DemoWarning, DemoInfo
from demo.core.document import Document
from demo.core import vcs


class Tree(object):  # pylint: disable=R0902

    """A bidirectional tree structure to store the hierarchy of documents.

    Although requirements link "upwards", bidirectionality simplifies
    document processing and validation.

    """

    def __init__(self, document, parent=None, root=None):
        self.document = document
        self.root = root or document.root  # allows non-documents in tests
        self.parent = parent
        self.children = []
        self._vcs = None
        self._loaded = False
        self._item_cache = {}
        self._document_cache = {}

    def __str__(self):
        # Build parent prefix string (getattr to support testing)
        prefix = getattr(self.document, 'prefix', self.document)
        # Build children prefix strings
        children = ", ".join(str(c) for c in self.children)
        # Format the tree
        if children:
            return "{} <- [ {} ]".format(prefix, children)
        else:
            return "{}".format(prefix)

    def __len__(self):
        if self.document:
            return 1 + sum(len(child) for child in self.children)
        else:
            return 0

    def __getitem__(self, key):
        raise IndexError("{} cannot be indexed by key".format(self.__class__))

    def __iter__(self):
        if self.document:
            yield self.document
        yield from chain(*(iter(c) for c in self.children))

    @staticmethod
    def from_list(documents, root=None):
        """Get a new tree from a list of documents.

        @param documents: list of Documents
        @param root: path to root of the project

        @return: new Tree

        @raise DemoError: when the tree cannot be built

        """
        if not documents:
            return Tree(document=None, root=root)
        unplaced = list(documents)
        for document in list(unplaced):
            if document.parent is None:
                logging.debug("added root of tree: {}".format(document))
                tree = Tree(document)
                logging.info("root of the tree: {}".format(document))
                unplaced.remove(document)
                break
        else:
            raise DemoError("no root document")

        while unplaced:
            count = len(unplaced)
            for document in list(unplaced):
                if document.parent is None:
                    logging.info("root of the tree: {}".format(document))
                    raise DemoError("multiple root documents")
                try:
                    tree._place(document)  # pylint: disable=W0212
                except DemoError as error:
                    logging.debug(error)
                else:
                    logging.info("added to tree: {}".format(document))
                    unplaced.remove(document)

            if len(unplaced) == count:  # no more documents could be placed
                logging.debug("unplaced documents: {}".format(unplaced))
                msg = "unplaced document: {}".format(unplaced[0])
                raise DemoError(msg)

        return tree

    def _place(self, document):
        """Attempt to place the document in the current tree.

        @param document: Document to add

        @raise DemoError: if the document cannot yet be placed

        """
        logging.debug("trying to add '{}'...".format(document))
        if not self.document:

            # Tree is empty
            if document.parent:
                msg = "unknown parent for {}: {}".format(document,
                                                         document.parent)
                raise DemoError(msg)
            self.document = document

        elif (document.parent and
              document.parent.lower() == self.document.prefix.lower()):

            # Current document is the parent
            node = Tree(document, self)
            self.children.append(node)

        else:

            # Search for the parent
            for child in self.children:
                try:
                    child._place(document)  # pylint: disable=W0212
                except DemoError:
                    pass  # the error is raised later
                else:
                    break
            else:
                msg = "unknown parent for {}: {}".format(document,
                                                         document.parent)
                raise DemoError(msg)

    # attributes #############################################################

    @property
    def vcs(self):
        """Get the working copy."""
        if self._vcs is None:
            self._vcs = vcs.load(self.root)
        return self._vcs

    # actions ################################################################

    @clear_document_cache
    @clear_item_cache
    def new(self, path, prefix, sep=None, digits=None, parent=None):  # pylint: disable=R0913
        """Create a new document and add it to the tree.

        @param path: directory path for the new document
        @param prefix: document's prefix
        @param sep: separator between prefix and numbers
        @param digits: number of digits for the document's numbers
        @param parent: parent document's prefix

        @return: newly created and placed Document

        @raise DemoError: if the document cannot be created

        """
        document = Document.new(path, self.root, prefix,
                                sep=sep, digits=digits,
                                parent=parent)
        try:
            self._place(document)
        except DemoError:
            msg = "deleting unplaced directory {}...".format(document.path)
            logging.debug(msg)
            if os.path.exists(document.path):
                shutil.rmtree(document.path)
            raise
        return document

    @clear_item_cache
    def add(self, prefix):
        """Add a new item to an existing document by prefix.

        @param prefix: document's prefix

        @return: newly created Item

        @raise DemoError: if the item cannot be created

        """
        document = self.find_document(prefix)
        self.vcs.lock(document.config)  # prevents duplicate item IDs
        item = document.add()
        return item

    @clear_item_cache
    def remove(self, identifier):
        """Remove an item from a document by ID.

        @param identifier: item's ID

        @return: removed Item

        @raise DemoError: if the item cannot be removed

        """
        for document in self:
            try:
                document.find_item(identifier)
            except DemoError:
                pass  # item not found in that document
            else:
                item = document.remove(identifier)
                return item

        raise DemoError("no matching ID: {}".format(identifier))

    def link(self, cid, pid):
        """Add a new link between two items by IDs.

        @param cid: child item's ID
        @param pid: parent item's ID

        @return: child Item, parent Item

        @raise DemoError: if the link cannot be created

        """
        logging.info("linking {} to {}...".format(cid, pid))
        # Find child item
        child = self.find_item(cid, _kind='child')
        # Find parent item
        parent = self.find_item(pid, _kind='parent')
        # Add link
        child.add_link(parent.id)
        return child, parent

    def unlink(self, cid, pid):
        """Remove a link between two items by IDs.

        @param cid: child item's ID
        @param pid: parent item's ID

        @return: child Item, parent Item

        @raise DemoError: if the link cannot be removed

        """
        logging.info("unlinking '{}' from '{}'...".format(cid, pid))
        # Find child item
        child = self.find_item(cid, _kind='child')
        # Find parent item
        parent = self.find_item(pid, _kind='parent')
        # Remove link
        child.remove_link(parent.id)
        return child, parent

    def edit(self, identifier, tool=None, launch=False):
        """Open an item for editing by ID.

        @param identifier: ID of item to edit
        @param tool: alternative text editor to open the item
        @param launch: open the default text editor

        @raise DemoError: if the item cannot be found

        """
        logging.debug("looking for {}...".format(identifier))
        # Find item
        item = self.find_item(identifier)
        # Lock the item
        self.vcs.lock(item.path)
        # Open item
        if launch:
            _open(item.path, tool=tool)
            # TODO: force an item reload without touching a private attribute
            item._loaded = False  # pylint: disable=W0212
        # Return the item
        return item

    def find_document(self, prefix):
        """Get a document by its prefix.

        @param prefix: document's prefix

        @return: matching Document

        @raise DemoError: if the document cannot be found

        """
        logging.debug("looking for document '{}'...".format(prefix))
        try:
            document = self._document_cache[prefix]
            if document:
                logging.debug("found cached document: {}".format(document))
                return document
            else:
                logging.debug("found cached unknown: {}".format(prefix))
        except KeyError:
            for document in self:
                if document.prefix.lower() == prefix.lower():
                    logging.debug("found document: {}".format(document))
                    self._document_cache[prefix] = document
                    return document
            logging.debug("could not find document: {}".format(prefix))
            self._document_cache[prefix] = None

        raise DemoError("no matching prefix: {}".format(prefix))

    def find_item(self, identifier, _kind=''):
        """Get an item by its ID.

        @param identifier: item ID

        @return: matching Item

        @raise DemoError: if the item cannot be found

        """
        _kind = (' ' + _kind) if _kind else _kind  # for logging messages
        logging.debug("looking for{} item '{}'...".format(_kind, identifier))
        try:
            item = self._item_cache[identifier]
            if item:
                logging.debug("found cached item: {}".format(item))
                return item
            else:
                logging.debug("found cached unknown: {}".format(identifier))
        except KeyError:
            for document in self:
                try:
                    item = document.find_item(identifier, _kind=_kind)
                except DemoError:
                    pass  # item not found in that document
                else:
                    logging.debug("found item: {}".format(item))
                    self._item_cache[identifier] = item
                    return item
            logging.debug("could not find item: {}".format(identifier))
            self._item_cache[identifier] = None

        raise DemoError("no matching{} ID: {}".format(_kind, identifier))

    def valid(self, document_hook=None, item_hook=None):
        """Check the tree (and its documents) for validity.

        @param document_hook: function to call for custom document validation
        @param item_hook: function to call for custom item validation

        @return: indication that the tree is valid

        """
        valid = True
        logging.info("checking tree...")
        # Display all issues
        for issue in self.issues(document_hook=document_hook,
                                 item_hook=item_hook):
            if isinstance(issue, DemoInfo):
                logging.info(issue)
            elif isinstance(issue, DemoWarning):
                logging.warning(issue)
            else:
                assert isinstance(issue, DemoError)
                logging.error(issue)
                valid = False
        # Return the result
        return valid

    def issues(self, document_hook=None, item_hook=None):
        """Yield all the tree's issues.

        @param document_hook: function to call for custom document validation
        @param item_hook: function to call for custom item validation

        @return: generator of DemoError, DemoWarning, DemoInfo

        """
        documents = list(self)
        # Check for documents
        if not documents:
            yield DemoWarning("no documents")
        # Check each document
        for document in documents:
            for issue in chain(document_hook(document=document, tree=self)
                               if document_hook else [],
                               document.issues(tree=self,
                                               item_hook=item_hook)):
                # Prepend the document's prefix to yielded exceptions
                if isinstance(issue, Exception):
                    yield type(issue)("{}: {}".format(document.prefix, issue))

    @clear_document_cache
    @clear_item_cache
    def load(self, reload=False):
        """Load the tree's documents and items.

        Unlike the Document and Item class, this load method is not
        used internally. Its purpose is to force the loading of
        content in large trees where lazy loading may be too slow.

        """
        if self._loaded and not reload:
            return
        logging.info("loading the tree...")
        for document in self:
            document.load(reload=True)
        # Set meta attributes
        self._loaded = True


def _open(path, tool=None):  # pragma: no cover, integration test
    """Open the text file using the default editor."""
    if tool:
        args = [tool, path]
        logging.debug("$ {}".format(' '.join(args)))
        subprocess.call(args)
    elif sys.platform.startswith('darwin'):
        args = ['open', path]
        logging.debug("$ {}".format(' '.join(args)))
        subprocess.call(args)
    elif os.name == 'nt':
        logging.debug("$ (start) {}".format(path))
        os.startfile(path)  # pylint: disable=E1101
    elif os.name == 'posix':
        args = ['xdg-open', path]
        logging.debug("$ {}".format(' '.join(args)))
        subprocess.call(args)


def build(cwd=None, root=None):
    """Build a tree from the current working directory or explicit root.

    @param cwd: current working directory
    @param root: path to root of the working copy

    @return: new Tree

    @raise DemoError: when the tree cannot be built

    """
    documents = []

    # Find the root of the working copy
    cwd = cwd or os.getcwd()
    root = root or vcs.find_root(cwd)

    # Find all documents in the working copy
    logging.info("looking for documents in {}...".format(root))
    _document_from_path(root, root, documents)
    for dirpath, dirnames, _ in os.walk(root):
        for dirname in dirnames:
            path = os.path.join(dirpath, dirname)
            _document_from_path(path, root, documents)

    # Build the tree
    if not documents:
        logging.info("no documents found in: {}".format(root))
    logging.info("building tree...")
    tree = Tree.from_list(documents, root=root)
    logging.info("built tree: {}".format(tree))
    return tree


def _document_from_path(path, root, documents):
    """Attempt to create and append a document from the specified path.

    @param path: path to a potential document
    @param root: path to root of working copy
    @param documents: list of Documents to append results

    """
    try:
        document = Document(path, root)
    except DemoError:
        pass  # no document in directory
    else:
        if document.skip:
            logging.debug("skipping document: {}".format(document))
        else:
            logging.info("found document: {}".format(document))
            documents.append(document)

# convenience functions ######################################################

_TREE = None  # implicitly created tree created for convenience functions


def find_document(prefix):
    """Find a document without an explicitly building a tree."""
    global _TREE  # pylint: disable=W0603
    if _TREE is None:
        _TREE = build()
    document = _TREE.find_document(prefix)
    return document


def find_item(identifier):
    """Find an item without an explicitly building a tree."""
    global _TREE  # pylint: disable=W0603
    if _TREE is None:
        _TREE = build()
    item = _TREE.find_item(identifier)
    return item
