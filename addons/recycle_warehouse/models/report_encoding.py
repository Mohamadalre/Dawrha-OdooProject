# -*- coding: utf-8 -*-
"""Tell wkhtmltopdf the HTML is UTF-8. It cannot work it out on its own.

Every Arabic name printed as mojibake — "محمد" came out as "Ù…Ø­Ù…Ø¯" and the
em-dashes as "â€"". That is UTF-8 bytes decoded as Latin-1, and it is not a
font problem: the text handed to the renderer was correct and the renderer read
it wrongly.

Why nothing in the TEMPLATE could fix it
────────────────────────────────────────
Odoo does not give wkhtmltopdf a document. It renders one, then splits it into
header / body / footer fragments with `lxml.html.tostring(node)`, writes each
fragment to its own temp `.html` file, and passes the file paths.

A fragment has no `<html>` and no `<head>`. So:

  * `web.report_layout`'s `<meta charset="utf-8">` is discarded with the head
    it lives in — which is why declaring it there changed nothing;
  * a `<meta http-equiv>` placed inside the body survives the split but arrives
    after Qt WebKit has already chosen a codec for the file, so it is ignored
    too.

The file therefore reaches wkhtmltopdf as bytes with no declared encoding, and
Qt 4 WebKit falls back to Latin-1.

`--encoding utf-8` is the one place the answer can be given: it applies to the
files themselves, before anything inside them is parsed. Appended to whatever
Odoo built rather than replacing it, so paper format, margins and DPI are
untouched — and appended LAST, because wkhtmltopdf takes the final occurrence
of a repeated option, which makes this win even if a future Odoo sets its own.
"""
from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _build_wkhtmltopdf_args(self, *args, **kwargs):
        command_args = super()._build_wkhtmltopdf_args(*args, **kwargs)
        return command_args + ['--encoding', 'utf-8']
