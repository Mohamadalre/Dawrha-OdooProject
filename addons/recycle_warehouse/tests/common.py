# -*- coding: utf-8 -*-
"""Shared fixtures.

A warehouse now has to say WHERE IT IS when it is created — order allocation
matches buyers to warehouses by governorate, and a driver is sent to an address.
Every fixture in this suite was creating warehouses with neither, which is not a
test detail: they were creating buildings that no order could ever be routed to,
and the tests passed because nothing asked them to receive one.

Rather than repeat the same two keys in fifteen files, they are defaulted here.
A test that cares about the location still passes its own.
"""


def make_warehouse(env, vals=None, **kwargs):
    """A warehouse with a governorate and an address unless the caller names them.

    Takes the values either as a dict or as keywords, because it replaced
    `env['recycle.warehouse'].create({...})` in fifteen files and both shapes
    read naturally at the call sites. Accepting one and rewriting the other
    would have been fifteen more chances to typo a fixture.

    The province is looked up rather than created each time: the governorates
    are mirrored reference data, so a fixture that invented its own would be
    testing against a table shape the real system never has. One is created only
    if the mirror is genuinely empty, which happens on a bare test database.
    """
    vals = dict(vals or {}, **kwargs)
    if 'province_id' not in vals:
        Province = env['recycle.province'].sudo()
        province = Province.with_context(active_test=False).search([], limit=1)
        if not province:
            province = Province.create({
                'backend_province_id': 'test-province',
                'name_en': 'Test Governorate',
                'name_ar': 'محافظة الاختبار',
            })
        vals['province_id'] = province.id
    vals.setdefault('address', 'Test address')
    return env['recycle.warehouse'].create(vals)
