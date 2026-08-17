# -*- coding: utf-8 -*-
"""Every Owl expression in the dashboards must be tokenizable.

Owl compiles `t-esc` / `t-att-*` / `t-if` attributes as JavaScript expressions,
IN THE BROWSER. A malformed one therefore passes module installation, passes the
XML parser, passes every server-side test — and then blows up as a white screen
the first time a user opens that view:

    OwlError: Tokenizer error: could not tokenize
    `tr('A truck's job cannot be changed ...')`

That exact error shipped: an apostrophe inside a single-quoted string closed the
string early, and the rest of the sentence became garbage tokens. Nothing on the
server could have caught it, because the server never reads the expression.

So this test reads them the way Owl does. It is deliberately narrow — it checks
QUOTING, not semantics — because quoting is the failure mode that survives every
other check and is invisible in review: `truck's` looks like ordinary English.

Note the four layers a template string passes through on its way here: shell →
Python patch script → XML attribute → Owl tokenizer. Each has its own escaping
rules, and getting any one of them wrong produces exactly this bug. The habit
this test encodes is simpler than remembering all four: **do not put an
apostrophe inside a single-quoted Owl string.** Reword it.
"""
import os
import re
import xml.etree.ElementTree as ET

from odoo.tests.common import TransactionCase, tagged

# Attributes Owl parses as expressions rather than as literal text.
EXPRESSION_ATTRS = ('t-esc', 't-out', 't-if', 't-elif', 't-set', 't-value',
                    't-foreach', 't-key')
EXPRESSION_PREFIXES = ('t-att-', 't-on-', 't-model')

TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'static', 'src', 'xml')


def _is_expression_attr(name):
    if name in EXPRESSION_ATTRS:
        return True
    return any(name.startswith(p) for p in EXPRESSION_PREFIXES)


def _unbalanced_quotes(expr):
    """True when a single-quoted literal is left open.

    Counts apostrophes that are NOT preceded by a backslash — which is exactly
    what Owl's tokenizer does. An odd count means one of them terminated a
    string the author meant to continue.
    """
    unescaped = re.findall(r"(?<!\\)'", expr)
    return len(unescaped) % 2 == 1


@tagged('post_install', '-at_install')
class TestQwebExpressions(TransactionCase):

    def _templates(self):
        for name in sorted(os.listdir(TEMPLATE_DIR)):
            if name.endswith('.xml'):
                yield name, os.path.join(TEMPLATE_DIR, name)

    def test_the_templates_are_actually_being_read(self):
        """A guard on the guard: an empty sweep would pass and prove nothing."""
        found = 0
        for _name, path in self._templates():
            for element in ET.parse(path).iter():
                found += sum(1 for a in element.attrib if _is_expression_attr(a))
        self.assertGreater(found, 200,
                           'expected to find the dashboards\' expressions')

    def test_no_expression_has_an_unterminated_string(self):
        """The bug this file exists for.

        An apostrophe inside a single-quoted Owl string closes it early, and the
        remainder of the sentence becomes tokens the compiler cannot read. The
        view then fails to render — for the user, not for the developer.
        """
        broken = []
        for name, path in self._templates():
            for element in ET.parse(path).iter():
                for attr, value in element.attrib.items():
                    if not _is_expression_attr(attr):
                        continue
                    if _unbalanced_quotes(value):
                        broken.append('%s :: %s="%s"' % (name, attr, value[:120]))

        self.assertEqual(broken, [], '\n'.join(
            ['Owl cannot tokenize these — reword to avoid the apostrophe:']
            + broken))

    def test_no_expression_mixes_an_apostrophe_into_a_translated_string(self):
        """Even ESCAPED apostrophes are avoided in new strings.

        `\\'` does work inside an Owl string, but it has to survive shell,
        Python, XML and Owl escaping to get there — four sets of rules, and the
        bug that shipped came from getting one of them wrong. Existing strings
        that already escape correctly are left alone; what this pins is that the
        newest ones do not reintroduce the hazard.
        """
        risky = []
        for name, path in self._templates():
            for element in ET.parse(path).iter():
                for attr, value in element.attrib.items():
                    if not _is_expression_attr(attr):
                        continue
                    # Only flag the specific shape that broke: an apostrophe
                    # directly between two letters inside a quoted literal.
                    if re.search(r"[A-Za-z]'[A-Za-z]", value):
                        risky.append('%s :: %s="%s"' % (name, attr, value[:120]))

        self.assertEqual(risky, [], '\n'.join(
            ['Unescaped apostrophe inside an Owl expression — reword it:']
            + risky))
