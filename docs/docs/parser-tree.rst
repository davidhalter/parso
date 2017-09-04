.. include:: ../global.rst

.. _parser-tree:

Parser Tree
===========

The parser tree is returned by calling :py:meth:`parso.Grammar.parse`.

.. note:: Note that parso positions are always 1 based for lines and zero
   based for columns. This means the first position in a file is (1, 0).

Parser Tree Base Classes
------------------------

All nodes and leaves have these methods/properties:

.. autoclass:: parso.tree.BaseNode
    :show-inheritance:
    :members:

.. autoclass:: parso.tree.Leaf
    :show-inheritance:
    :members:

.. autoclass:: parso.tree.NodeOrLeaf
    :members:
    :undoc-members:
    :show-inheritance:


Python Parser Tree
------------------

.. currentmodule:: parso.python.tree

.. automodule:: parso.python.tree
    :members:
    :undoc-members:
    :show-inheritance:


Utility
-------

.. autofunction:: parso.tree.search_ancestor
