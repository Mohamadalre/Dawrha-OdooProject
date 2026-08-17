# -*- coding: utf-8 -*-
"""Arabic must survive the trip into a printed PDF.

Two independent things have to be true, and each failed on its own:

1. **The bytes must be decoded as UTF-8.** They were not. Odoo renders a
   document, splits it into header/body/footer FRAGMENTS with
   `lxml.html.tostring`, and writes each to a temp `.html` file. A fragment has
   no `<html>` and no `<head>`, so `web.report_layout`'s `<meta charset>` is
   discarded with the head it lives in, and Qt 4 WebKit falls back to Latin-1.
   "محمد" printed as "Ù…Ø­Ù…Ø¯". Only `--encoding utf-8` on the command line
   reaches the files themselves.

2. **A font with Arabic JOINING rules must be available.** The base image ships
   only DejaVu, which carries the code points without the shaping tables — so
   even correctly decoded text renders as disconnected letters. Noto Naskh
   Arabic ships with this addon and is mounted into the container's font path.

Both are invisible in every other check: the HTML is correct, the report
generates, the PDF is valid, and the page is unreadable.
"""
import re

from odoo.tests.common import TransactionCase, tagged
from .common import make_warehouse

ARABIC = re.compile(r'[؀-ۿ]')
# A name whose rendering exercises joining: every letter here connects.
ARABIC_NAME = 'عبد الله محمد الحلبي'


@tagged('post_install', '-at_install')
class TestReportArabic(TransactionCase):

    def test_wkhtmltopdf_is_told_the_html_is_utf8(self):
        """The fix that actually worked, pinned.

        Asserted on the ARGUMENTS rather than on the output, because this is
        the only layer that can carry the answer — the template cannot, and
        trying there is what cost the first two attempts.
        """
        args = self.env['ir.actions.report']._build_wkhtmltopdf_args(
            paperformat_id=self.env['report.paperformat'],
            landscape=False,
        )
        self.assertIn('--encoding', args)
        self.assertEqual(args[args.index('--encoding') + 1], 'utf-8')

    def test_the_encoding_flag_wins_over_anything_odoo_set(self):
        """wkhtmltopdf takes the LAST occurrence of a repeated option.

        Appending rather than inserting is what makes this survive a future
        Odoo that sets its own encoding.
        """
        args = self.env['ir.actions.report']._build_wkhtmltopdf_args(
            paperformat_id=self.env['report.paperformat'],
            landscape=False,
        )
        self.assertEqual(args[-2:], ['--encoding', 'utf-8'])

    def test_an_arabic_shaping_font_is_installed(self):
        """DejaVu is not enough — it has the letters and not the joining."""
        import subprocess
        families = subprocess.run(
            ['fc-list', ':lang=ar', 'family'],
            capture_output=True, text=True, check=False).stdout
        self.assertIn('Noto Naskh Arabic', families,
                      'the Arabic font the reports depend on is not visible to '
                      'fontconfig — check the font mount in docker-compose.yml')

    def test_the_font_files_ship_with_the_addon(self):
        """Not apt-installed into a running container.

        A package installed into a container disappears the next time it is
        rebuilt, and the reports would quietly go back to garbling names.
        """
        import os
        fonts = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'static', 'src', 'fonts')
        for name in ('NotoNaskhArabic-Regular.ttf', 'NotoNaskhArabic-Bold.ttf'):
            path = os.path.join(fonts, name)
            self.assertTrue(os.path.exists(path), '%s is missing' % name)
            self.assertGreater(os.path.getsize(path), 50_000,
                               '%s looks truncated' % name)

    def test_both_driver_files_declare_the_charset_inside_the_body(self):
        """Belt to the braces above.

        The meta alone did not fix it — Qt WebKit had already chosen a codec
        for the file by the time it read the body. It stays because any other
        renderer (a browser previewing the HTML report) does honour it, and
        because its absence would make the document ambiguous about its own
        encoding.
        """
        for xmlid in ('recycle_warehouse.report_delivery_driver_file_doc',
                      'recycle_warehouse.report_collection_driver_file_doc'):
            arch = self.env.ref(xmlid).sudo().arch_db
            self.assertIn('driver_file_charset', arch,
                          '%s does not declare its encoding' % xmlid)

    def test_an_arabic_name_renders_without_mojibake(self):
        """End to end, on a real record.

        Mojibake is invisible to text extraction — the PDF's text layer can be
        perfect while the page shows boxes. So this checks the FONTS the page
        embedded: the Arabic-shaping one must be among them, which only happens
        when Arabic glyphs were actually drawn.
        """
        warehouse = make_warehouse(self.env, 
            {'name': 'مستودع الاختبار', 'code': 'ARTEST'})
        driver = self.env['recycle.delivery.driver'].create({
            'name': ARABIC_NAME,
            'phone': '0999111333',
            'national_id': 'AR-RENDER-1',
            'warehouse_id': warehouse.id,
        })

        # `force_report_rendering` because Odoo SKIPS wkhtmltopdf during tests
        # and hands back the HTML instead — which is exactly the layer that was
        # never wrong here. Without it this test would assert on the one thing
        # that always looked correct while the printed page was unreadable.
        pdf, _ext = self.env['ir.actions.report'].sudo().with_context(
            force_report_rendering=True,
        )._render_qweb_pdf(
            'recycle_warehouse.report_delivery_driver_file', res_ids=driver.ids)

        self.assertTrue(pdf.startswith(b'%PDF'))
        raw = pdf.decode('latin-1', 'replace')
        embedded = set(re.findall(r'/BaseFont\s*/([A-Za-z0-9+\-_,]+)', raw))
        self.assertTrue(
            any('Naskh' in font for font in embedded),
            'no Arabic-shaping font was embedded — the name would print as '
            'boxes or as disconnected letters. Embedded: %s' % sorted(embedded))
