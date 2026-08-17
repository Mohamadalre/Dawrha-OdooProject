# -*- coding: utf-8 -*-
"""A component method called inside an arrow handler must go through `this`.

Owl compiles an inline handler into a function whose scope holds the template
variables, not the component. So a bare call inside an arrow body:

    t-on-click="() => this.openViewer(url, tr('Licence — Front'))"
                                          ^^^^ unbound

resolves `tr` as a free identifier and calls it with no receiver. The method
reads `this.state.lang`, and the click produces:

    TypeError: Cannot read properties of undefined (reading 'state')

That shipped: clicking a licence scan on the driver page crashed the dashboard.
Nothing on the server could have caught it — the attribute is valid XML, the
expression tokenizes, the template compiles, and the failure only happens when
somebody clicks.

Outside an arrow body the same call is fine: `t-esc="tr('X')"` is evaluated with
the component as the receiver. So this checks one narrow thing — a call inside
an inline arrow handler — because that is the shape that breaks, and flagging
the rest would flag almost every line in the dashboards.
"""
import os
import re
import xml.etree.ElementTree as ET

from odoo.tests.common import TransactionCase, tagged

TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'static', 'src', 'xml')

# Handlers written as an arrow function: `() => …` or `(e) => …`.
ARROW_HANDLER = re.compile(r'^\s*\(([^)]*)\)\s*=>(.*)$', re.DOTALL)

# A call that is NOT preceded by a dot — i.e. not `this.foo(` or `obj.foo(`.
BARE_CALL = re.compile(r'(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(')

# Names that legitimately appear bare inside a handler: JavaScript globals and
# the operators Owl allows. Anything else must be a component member.
ALLOWED_BARE = {
    'Number', 'String', 'Boolean', 'Array', 'Object', 'Math', 'JSON', 'Date',
    'parseInt', 'parseFloat', 'isNaN', 'encodeURIComponent', 'decodeURIComponent',
    'console', 'alert', 'confirm', 'setTimeout', 'clearTimeout', 'if', 'for',
    'while', 'return', 'typeof', 'function', 'switch', 'catch',
}


def _handler_attrs(element):
    for name, value in element.attrib.items():
        if name.startswith('t-on-'):
            yield name, value


@tagged('post_install', '-at_install')
class TestQwebHandlerBinding(TransactionCase):

    def _templates(self):
        for name in sorted(os.listdir(TEMPLATE_DIR)):
            if name.endswith('.xml'):
                yield name, os.path.join(TEMPLATE_DIR, name)

    def test_the_sweep_actually_finds_the_handlers(self):
        """A guard on the guard: an empty sweep would pass and prove nothing."""
        found = 0
        for _name, path in self._templates():
            for element in ET.parse(path).iter():
                for _attr, value in _handler_attrs(element):
                    if ARROW_HANDLER.match(value):
                        found += 1
        self.assertGreater(found, 100, 'expected to find the inline handlers')

    def test_every_call_inside_an_arrow_handler_is_bound(self):
        """The bug this file exists for.

        Reproduces as a runtime TypeError on click, never on the server.
        """
        unbound = []
        for name, path in self._templates():
            for element in ET.parse(path).iter():
                for attr, value in _handler_attrs(element):
                    match = ARROW_HANDLER.match(value)
                    if not match:
                        continue
                    params, body = match.group(1), match.group(2)
                    # A parameter of the handler is a local, not a member.
                    locals_ = {p.strip() for p in params.split(',') if p.strip()}
                    for call in BARE_CALL.finditer(body):
                        fn = call.group(1)
                        if fn in ALLOWED_BARE or fn in locals_:
                            continue
                        unbound.append(
                            '%s :: %s="%s"' % (name, attr, value[:130]))
                        break

        self.assertEqual(unbound, [], '\n'.join(
            ['Unbound call inside an arrow handler — prefix it with `this.`:']
            + unbound))
