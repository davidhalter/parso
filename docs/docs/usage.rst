.. include:: ../global.rst

Usage
=====

|parso| works around grammars. You can simply create Python grammars by calling
``load_grammar``. Grammars (with a custom tokenizer and custom parser trees)
can also be created by directly instantiating ``Grammar``. More information
about the resulting objects can be found in the :ref:`parser tree documentation
<plugin-api-classes>`.

.. automodule:: parso.grammar
    :members:
    :undoc-members:


Utility
-------

.. autofunction:: parso.parse

.. automodule:: parso.utils
    :members:
    :undoc-members:


Used By
-------

- jedi_ (which is used by IPython and a lot of plugins).


.. _jedi: https://github.com/davidhalter/jedi
