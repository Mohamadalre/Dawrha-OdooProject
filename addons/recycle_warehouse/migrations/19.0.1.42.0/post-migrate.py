# -*- coding: utf-8 -*-
"""Clear the "asked for" flag from documents that were ACCEPTED.

Accepting a document now closes any outstanding request for it — there is
nothing left for the driver to send. Rows written before that did both at once:
the document reads `accepted` and still carries `reupload_requested`, so the
review screen shows an "Asked for" badge beside a document nobody is waiting
on. A reviewer reading that has no way to tell whether the driver still owes
them something.

Only the contradictory pairing is touched. A document that is genuinely still
requested is rejected, not accepted, and is left exactly as it is.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        UPDATE recycle_driver_request_image
           SET reupload_requested = FALSE
         WHERE status = 'accepted'
           AND reupload_requested = TRUE
    """)
    _logger.info(
        'Driver documents: cleared the stale "asked for" flag on %s accepted '
        'document(s).', cr.rowcount)
