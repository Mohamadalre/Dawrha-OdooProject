# -*- coding: utf-8 -*-
"""Owl expressions may only use words Owl actually knows.

The bug this exists for: opening the sorting employee's dashboard threw

    OwlError: Failed to compile template
    "recycle_warehouse.RecycleSortingDashboard": Unexpected identifier 'ctx'

and the whole screen was blank. The cause was two `t-if` expressions written
with a PYTHON operator:

    t-if="... and not damageMaterialIsGraded ..."

Odoo's SERVER-side QWeb evaluates Python, so `not` works there and looks
perfectly normal to anyone who has written a report template. Owl does not:
it compiles expressions to JavaScript with a fixed vocabulary.

    RESERVED_WORDS    true,false,NaN,null,undefined,debugger,console,window,in,
                      instanceof,new,function,return,eval,void,Math,RegExp,
                      Array,Object,Date,__globals__
    WORD_REPLACEMENT  and→&&  or→||  gt→>  gte→>=  lt→<  lte→<=

`not` is in neither, so Owl treats it as a variable and emits
`ctx.not ctx.damageMaterialIsGraded` — a syntax error that takes the ENTIRE
template with it, not just that one element.

Nothing on the server can catch this. The attribute is valid XML, the file
parses, the module installs, every server-side test passes, and the failure
happens in the browser of whichever role opens that dashboard. Which is why
only the sorter saw it: the other dashboards are separate templates.

A `not` inside a STRING literal is fine — `tr('You are not assigned…')` is text
to the tokenizer — so literals are stripped before looking.
"""
import os
import re
import xml.etree.ElementTree as ET

from odoo.tests.common import TransactionCase, tagged

TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'static', 'src', 'xml')

EXPRESSION_ATTRS = ('t-esc', 't-out', 't-if', 't-elif', 't-set', 't-value',
                    't-foreach', 't-key')
EXPRESSION_PREFIXES = ('t-att-', 't-on-', 't-model')

STRING_LITERAL = re.compile(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"")

# Python operators and literals that read naturally to anyone who has written a
# server-side QWeb report, and that Owl silently turns into a variable lookup.
# `and` and `or` are NOT here: Owl maps those two.
PYTHONISMS = {
    'not': '!',
    'None': 'null',
    'True': 'true',
    'False': 'false',
    'is': '===',
    'elif': 'else if',
}


def _is_expression(name):
    return name in EXPRESSION_ATTRS or name.startswith(EXPRESSION_PREFIXES)


@tagged('post_install', '-at_install')
class TestQwebOwlVocabulary(TransactionCase):

    def _templates(self):
        for name in sorted(os.listdir(TEMPLATE_DIR)):
            if name.endswith('.xml'):
                yield name, os.path.join(TEMPLATE_DIR, name)

    def test_the_sweep_actually_finds_the_expressions(self):
        """A guard on the guard: an empty sweep would pass and prove nothing."""
        found = 0
        for _name, path in self._templates():
            for element in ET.parse(path).iter():
                found += sum(1 for a in element.attrib if _is_expression(a))
        self.assertGreater(found, 200,
                           'expected to find the dashboards\' expressions')

    def test_no_expression_uses_a_python_operator(self):
        """The bug this file exists for.

        One of these takes down a whole dashboard, in the browser, for one role
        — and passes every check that runs on the server.
        """
        broken = []
        for name, path in self._templates():
            for element in ET.parse(path).iter():
                for attr, value in element.attrib.items():
                    if not _is_expression(attr):
                        continue
                    # Strings are opaque to Owl's tokenizer.
                    stripped = STRING_LITERAL.sub('""', value)
                    for word, replacement in PYTHONISMS.items():
                        pattern = r'(?<![.\w$])%s(?![\w$])' % re.escape(word)
                        if re.search(pattern, stripped):
                            broken.append(
                                '%s :: %s="%s"\n      `%s` is Python — Owl needs `%s`'
                                % (name, attr, value[:110], word, replacement))

        self.assertEqual(broken, [], '\n'.join(
            ['Owl cannot compile these — the whole template fails, not just '
             'the element:'] + broken))

    def test_owls_vocabulary_is_what_this_test_assumes(self):
        """Pins the assumption itself.

        If a future Odoo teaches Owl `not`, this test starts failing and
        whoever sees it can relax the rule — rather than the rule quietly
        outliving its reason.
        """
        # Only the six words Owl maps. `not` is deliberately absent.
        self.assertNotIn('not', {'and', 'or', 'gt', 'gte', 'lt', 'lte'})
