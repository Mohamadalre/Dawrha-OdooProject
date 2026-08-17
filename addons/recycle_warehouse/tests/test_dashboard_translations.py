# -*- coding: utf-8 -*-
"""Every string the dashboards translate must have an Arabic entry.

The dashboards do not use Odoo's translation engine — they are Owl components
that call a `tr(...)` helper backed by a plain registry in
`recycle_i18n_shared.js`. That helper FALLS BACK TO THE ENGLISH SOURCE when a
key is missing. Which is the whole problem: an untranslated string does not
throw, does not warn, and does not look broken to a developer reading English.
It simply shows up as English inside an otherwise Arabic screen, and only the
user ever finds out.

176 strings had drifted into exactly that state before this test existed.

Two subtleties this file exists to pin down:

1. **XML entities are decoded before Owl sees them.** A template written as
   `tr('Confirm &amp; Store')` calls `tr('Confirm & Store')` at runtime, because
   the XML parser resolves the entity first. A registry key stored with the raw
   entity is therefore unreachable — it looks present in a text search and is
   never found at runtime. Ten such dead keys existed. The audit here decodes
   entities exactly as the browser does, so a key can only pass by being usable.

2. **Whitespace is normalised.** Long strings wrap across lines in the XML
   source; the browser collapses that run of whitespace into single spaces. The
   registry does the same via `normKey()`, so this test must too, or every
   wrapped string would read as missing.
"""
import io
import os
import re

from odoo.tests.common import TransactionCase, tagged

STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'static', 'src')
REGISTRY = os.path.join(STATIC_DIR, 'js', 'recycle_i18n_shared.js')

# Matches a single- or double-quoted literal passed straight to tr(). Calls
# built from a variable are skipped on purpose: their value is not knowable
# here, and the registry cannot be checked against something the source does
# not contain.
TR_SINGLE = re.compile(r"tr\(\s*'((?:[^'\\]|\\.)*)'\s*\)")
TR_DOUBLE = re.compile(r'tr\(\s*"((?:[^"\\]|\\.)*)"\s*\)')
REG_SINGLE = re.compile(r"reg\(\s*'((?:[^'\\]|\\.)*)'")
REG_DOUBLE = re.compile(r'reg\(\s*"((?:[^"\\]|\\.)*)"')


def _norm(text):
    """Collapse whitespace the way the browser and `normKey()` both do."""
    return re.sub(r'\s+', ' ', text).strip()


def _decode_entities(text):
    """Resolve the entities an XML parser resolves before Owl compiles.

    `&amp;` must be resolved LAST — doing it first would turn a literal
    `&amp;lt;` into `<`, inventing markup the author never wrote.
    """
    return (text.replace('&lt;', '<')
                .replace('&gt;', '>')
                .replace('&quot;', '"')
                .replace('&apos;', "'")
                .replace('&amp;', '&'))


@tagged('post_install', '-at_install')
class TestDashboardTranslations(TransactionCase):

    def _registered_keys(self):
        src = io.open(REGISTRY, encoding='utf-8').read()
        keys = set()
        for pattern, escaped in ((REG_SINGLE, "\\'"), (REG_DOUBLE, '\\"')):
            for match in pattern.finditer(src):
                keys.add(_norm(match.group(1).replace(escaped, escaped[-1])))
        return keys

    def _used_keys(self):
        """Map each translated literal to the files that ask for it."""
        used = {}
        for folder in ('js', 'xml'):
            directory = os.path.join(STATIC_DIR, folder)
            for name in sorted(os.listdir(directory)):
                if not name.endswith(('.js', '.xml')):
                    continue
                if name == os.path.basename(REGISTRY):
                    continue
                src = io.open(os.path.join(directory, name),
                              encoding='utf-8').read()
                is_xml = name.endswith('.xml')
                for pattern, escaped in ((TR_SINGLE, "\\'"), (TR_DOUBLE, '\\"')):
                    for match in pattern.finditer(src):
                        text = match.group(1).replace(escaped, escaped[-1])
                        if is_xml:
                            text = _decode_entities(text)
                        key = _norm(text)
                        if key:
                            used.setdefault(key, set()).add(name)
        return used

    def test_the_sweep_actually_finds_the_dashboards(self):
        """A guard on the guard: an empty sweep would pass and prove nothing."""
        self.assertGreater(len(self._registered_keys()), 1000)
        self.assertGreater(len(self._used_keys()), 1000)

    def test_every_translated_string_has_an_arabic_entry(self):
        """The bug this file exists for.

        A missing key is invisible: `tr()` returns the English source, so the
        screen renders perfectly and is simply in the wrong language.
        """
        registered = self._registered_keys()
        missing = sorted(
            '%s   [%s]' % (key, ', '.join(sorted(files)))
            for key, files in self._used_keys().items()
            if key not in registered)

        self.assertEqual(missing, [], '\n'.join(
            ['These strings reach the screen untranslated. Add a reg(...) '
             'entry for each in recycle_i18n_shared.js:'] + missing))

    def test_no_registry_key_carries_a_raw_xml_entity(self):
        """A key with `&amp;` in it can never be looked up.

        The template that would need it calls `tr('… & …')`, because the XML
        parser decoded the entity long before Owl compiled the expression. Such
        a key is dead weight that reads, to anyone searching the file, as proof
        the string is covered.
        """
        dead = sorted(k for k in self._registered_keys()
                      if _decode_entities(k) != k)

        self.assertEqual(dead, [], '\n'.join(
            ['Unreachable registry keys — store the DECODED text instead:']
            + dead))
