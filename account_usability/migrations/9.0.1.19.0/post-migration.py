# -*- coding: utf-8 -*-
from openupgradelib import openupgrade, openupgrade_90


def fill_blacklisted_fields(cr):
    """Fill data of fields for which recomputation was surpressed."""
    # Set fields on account_invoice_line
    # For the moment use practical rounding of result to 2 decimals,
    # no currency that I know of has more precision at the moment.
    openupgrade.logged_query(
        cr,
        """\
        UPDATE account_invoice
        SET amount_untaxed_signed_real = amount_untaxed * -1
        WHERE type in ('in_refund', 'out_refund')
        """)
    openupgrade.logged_query(
        cr,
        """\
        UPDATE account_invoice
        SET amount_untaxed_signed_real = amount_untaxed
        WHERE type not in ('in_refund', 'out_refund')
        """)


def reset_blacklist_field_recomputation():
    """Make sure blacklists are disabled, to prevent problems in other
    modules.
    """
    from openerp.addons.account_usability.models.account_invoice import \
        AccountInvoice
    AccountInvoice._openupgrade_recompute_fields_blacklist = []


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    fill_blacklisted_fields(env.cr)
    reset_blacklist_field_recomputation()
