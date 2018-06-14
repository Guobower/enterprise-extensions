# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    sale_preparetion_time = fields.Integer(
        compute='_get_preparation_time',
        string='Tiempo De Preparacion')

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        """Quieren que cuando se haga una devolucion, si se factura en dolares,
        se use la cotizacion de la confirmación de la venta (para no acreditar)
        mayor importe en pesos del que pago.
        Es un metodo medio engorroso ya que se pueden crear facturas desde
        varias ventas pero luego se devuelve un listado de facturas en total y
        nosotros queremos saber para las que son completamente devoluciones,
        la cotización a la fecha de la orden y del listado de factura no
        sabriamos cual es la orden de venta, por eso empezamos recorriendo
        las ordenes de venta.
        NOTA: si se quiere generalizar esto tener en cuenta que tal vez desde
        una OV en una moneda se podría estar facturando en esa moneda en otra
        cia que tenga esa moneda como base y habria algun tipo de inconsistencia
        """
        invoice_ids = []

        if final:
            other_currency_sales = self.filtered(
                lambda x: x.currency_id != x.company_id.currency_id)
            self -= other_currency_sales

            for other_currency_sale in other_currency_sales:
                invoice_ids += super(
                    SaleOrder, other_currency_sale).action_invoice_create(
                    grouped=grouped, final=final)
                for refund in self.env['account.invoice'].browse(
                        invoice_ids).filtered(lambda x:
                            x.type == 'out_refund' and
                            x.currency_id != x.company_id.currency_id):

                    refund_currency = refund.currency_id
                    company_currency = refund.company_id.currency_id
                    rate = refund_currency.with_context(
                        date=other_currency_sale.date_confirm).compute(
                            1.0, company_currency)

                    self.env['account.change.currency'].with_context(
                        active_id=refund.id).create({
                            'currency_id': company_currency.id,
                            'currency_rate': rate,
                        }).change_currency()

                    # TODO en v11 esto ya lo podria resolver el wizard
                    # directamente
                    refund.update({
                        'move_currency_id': refund_currency.id,
                        'move_inverse_currency_rate': rate,
                    })

        # self podria no tener elementos a estas alturas
        if self:
            invoice_ids += super(SaleOrder, self).action_invoice_create(
                grouped=grouped, final=final)
        return invoice_ids

    @api.multi
    def action_confirm(self):
        param = self.env['ir.config_parameter'].get_param(
                'sale_order_action_confirm')
        if param == 'tracking_disable':
            _logger.info('tracking_disable on SO confirm ')
            self = self.with_context(tracking_disable=True)
        elif param == 'mail_notrack':
            _logger.info('mail_notrack on SO confirm ')
            self = self.with_context(mail_notrack=True)
        res = super(SaleOrder, self).action_confirm()
        if param:
            self.message_post(
                body=_('Orden validada con "no tracking=%s"') % param)
        return res

    @api.one
    def _get_preparation_time(self):
        if self.company_id.preparation_time_variable:
            preparation_time_variable = (
                self.company_id.preparation_time_variable)
            preparation_time_fixed = self.company_id.preparation_time_fixed
            self.sale_preparetion_time = len(
                self.order_line) * preparation_time_variable + (
                preparation_time_fixed)

    @api.one
    def update_requested_date(self):
        if self.sale_preparetion_time:
            self.requested_date = datetime.today() + timedelta(
                minutes=self.sale_preparetion_time)


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    supplier_code = fields.Char(
        related='product_id.product_tmpl_id.supplier_code',
        readonly=True)
    internal_code = fields.Char(
        related='product_id.internal_code',
        readonly=True)
    product_brand_id = fields.Many2one(
        related='product_id.product_tmpl_id.product_brand_id',
        readonly=True)
    additional_description = fields.Char(
    )

    @api.one
    @api.onchange('additional_description')
    def change_additional_description(self):
        line = self.new({'product_id': self.product_id.id})
        line.product_id_change()
        name = line.name
        if self.additional_description:
            name = "%s\n%s" % (name, self.additional_description or '')
        self.name = name
