# -*- coding: utf-8 -*-
from openupgradelib import openupgrade


def blacklist_field_recomputation(env):
    """Create computed fields that take long time to compute, but will be
    filled with valid values by migration."""
    from openerp.addons.account_usability.models.account_invoice import \
        AccountInvoice
    AccountInvoice._openupgrade_recompute_fields_blacklist = [
        'amount_untaxed_signed_real',
    ]


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    blacklist_field_recomputation(env)
