# -*- coding: utf-8 -*-
"""`t-elif` and `t-else` must follow a branch they can attach to.

The dashboards are one long chain per screen:

    <t t-if="state.view === 'a'"> … </t>
    <t t-elif="state.view === 'b'"> … </t>

Adding a screen means splicing a new `t-elif` into that chain, and putting
anything else between two links breaks it. Owl then raises

    OwlError: t-elif directive must follow t-if or t-elif directive

at COMPILE TIME IN THE BROWSER — so the module installs, the XML parses, every
server-side test passes, and the screen is a white page for the user. That has
already happened once here: a modal was inserted between two branches of the
manager dashboard.

The check is structural, not semantic: for each `t-elif`/`t-else` element, the
previous ELEMENT sibling must itself carry `t-if` or `t-elif`. Comments and
whitespace are ignored, because Owl ignores them too — it is real elements in
between that break the chain.
"""
import os
import xml.etree.ElementTree as ET

from odoo.tests.common import TransactionCase, tagged

TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'static', 'src', 'xml')


def _broken_links(path):
    """Yield a description of every t-elif/t-else with no branch before it."""
    # `parent_map` because ElementTree gives no parent pointer, and "the
    # previous sibling" is only answerable from the parent.
    tree = ET.parse(path)
    parents = {child: parent for parent in tree.iter() for child in parent}

    for element in tree.iter():
        for directive in ('t-elif', 't-else'):
            if directive not in element.attrib:
                continue
            parent = parents.get(element)
            if parent is None:
                yield '%s at the document root' % directive
                continue
            children = list(parent)
            index = children.index(element)
            if index == 0:
                yield '%s is the first child of <%s>' % (directive, parent.tag)
                continue
            previous = children[index - 1]
            if 't-if' not in previous.attrib and 't-elif' not in previous.attrib:
                yield '%s follows <%s> which is not a branch' % (
                    directive, previous.tag)


@tagged('post_install', '-at_install')
class TestQwebBranchChains(TransactionCase):

    def _templates(self):
        for name in sorted(os.listdir(TEMPLATE_DIR)):
            if name.endswith('.xml'):
                yield name, os.path.join(TEMPLATE_DIR, name)

    def test_the_sweep_actually_finds_the_chains(self):
        """A guard on the guard: an empty sweep would pass and prove nothing."""
        found = 0
        for _name, path in self._templates():
            for element in ET.parse(path).iter():
                if 't-elif' in element.attrib or 't-else' in element.attrib:
                    found += 1
        self.assertGreater(found, 100,
                           'expected to find the dashboards\' branch chains')

    def test_every_branch_follows_a_branch(self):
        """The bug this file exists for.

        A `t-elif` cut off from its `t-if` is invisible on the server and fatal
        in the browser: the whole component fails to compile, so the user gets a
        white screen rather than a broken section.
        """
        broken = []
        for name, path in self._templates():
            broken.extend('%s :: %s' % (name, problem)
                          for problem in _broken_links(path))

        self.assertEqual(broken, [], '\n'.join(
            ['Owl cannot compile these — the branch chain is cut:'] + broken))
