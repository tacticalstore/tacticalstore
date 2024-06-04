import requests
import logging
from odoo import fields, models, exceptions, api
_logger = logging.getLogger(__name__)
class TecfySaleOrder(models.Model):
    _inherit = "sale.order"

    tecfy_salla_update = fields.Boolean(string="Create Salla Order", help="عند تفعليها ثم الحفظ، سيقوم النظام بانشاء طلب جديد في سله تلقائي ، ولكن يجب التاكد من نسجيل رقم التاجر في بيانات الشركه")
    tecfy_salla_ref = fields.Char(string="Salla #", readonly=True)
    tecfy_salla_id = fields.Char(string="Salla ID", readonly=True)
    tecfy_salla_status = fields.Char(string="Salla Status", readonly=True)
    tecfy_salla_status_id = fields.Char(string="Salla Status Id", readonly=True)
    tecfy_salla_status_customized = fields.Char(string="Salla Customized Status", readonly=True)
    tecfy_salla_status_customized_id = fields.Char(string="Salla Customized Status Id", readonly=True)
    tecfy_source = fields.Char(string="Source", readonly=True)
    tecfy_source_device = fields.Char(string="Source Device", readonly=True)
    tecfy_source_info = fields.Char(string="Source Info", readonly=True)
    tecfy_shipping_company = fields.Char(string="Shipping Company")
    tecfy_shipping_company_logo = fields.Char(string="Shipping Logo", readonly=True)
    tecfy_shipping_tracking_no = fields.Char(string="Tracking Number")
    tecfy_shipping_tracking_url = fields.Char(string="Tracking URL")
    tecfy_shipping_pdf = fields.Char(string="Shipment Label URL")
    tecfy_payment_method = fields.Char(string="Salla Payment Method")
    tecfy_is_pending = fields.Boolean(string="Salla Update Pending", readonly=True)
    tecfy_salla_status_update_id = fields.Many2one("tecfysalla.status",string="Salla Status")


    def seializeItems(self, items):
        result = []
        for item in items:
            result.append({
                'product_template_id': item.product_template_id.id,
                'product_template_name': item.product_template_id.name,
                'template_barcode': item.product_template_id.barcode,
                'product_id': item.product_id.id,
                'product_name': item.product_id.name,
                'barcode': item.product_id.barcode,
                'quantity': item.product_uom_qty,
                'unit_price': item.price_unit,
            })
        return result

    def processRecord(self, values):
        if "state" not in values and "tecfy_salla_status_update_id" not in values and self.tecfy_salla_id != False and self.tecfy_salla_id != "":
            return 
        if "tecfy_is_pending" in values or self.tecfy_is_pending == True:
            return 
        
        company_id = False
        if 'company_id' in values:
            values['company_id']
        if self.company_id != False and self.company_id.id != False:
            company_id = self.company_id.id
        if company_id == False:
            return
        merchantData = self.getMerchantId(company_id)
        if merchantData == False or merchantData == 0:
            return 
        merchantId = merchantData['tecfy_salla_merchant_id']
        merchantUpdateStatus = merchantData['tecfy_salla_order_status_update']
        ignore_error = merchantData['tecfy_salla_ignore_error']
        tecfy_post_realtime = merchantData['tecfy_post_realtime']

        if tecfy_post_realtime == False and self.tecfy_is_pending == True:
            return 

        # order already on data and the conpmany configuration is not to update salla status
        if self.tecfy_salla_id != False and self.tecfy_salla_id != "":
            # order in salla already
            if merchantUpdateStatus != True:
                return 
        else:
            # order NOT in salla
            # ignore if user has choosed not to send to Salla
            if "tecfy_salla_update" not in values and self.tecfy_salla_update != True:
                return 
            if "tecfy_salla_update" in values and values["tecfy_salla_update"] != True:
                return 

        if tecfy_post_realtime == True:
            result = self.postToOdooNow(merchantId)
            if result != True and ignore_error != True:
                raise exceptions.ValidationError(str(result))
        else:
            self.tecfy_is_pending = True
            values["tecfy_is_pending"] = True

    def postToOdooNow(self, merchantId):
        try:
            if merchantId == False or merchantId == 0:
                return 'You need to add the Salla mechant id in the company profile!'
            salla_status_id = False
            if self.tecfy_salla_status_update_id != False:
                salla_status_id = self.tecfy_salla_status_update_id.salla_status_id
            
            data = {
                'customer': {
                    'id': self.partner_id.id,
                    'name': self.partner_id.name,
                    'email': self.partner_id.email,
                    'mobile': self.partner_id.mobile,
                    'city': self.partner_id.city,
                    'street': self.partner_id.street,
                    'street2': self.partner_id.street2,
                    'barcode': self.partner_id.barcode,
                },
                'merchant_id': merchantId,
                'items': self.seializeItems(self.order_line),
                'state': self.state,
                'display_name': self.display_name,
                'company_id': self.company_id.id,
                'salla_status_id': salla_status_id,
                'sale_order_id': self.id
            }
            response = requests.request(
                'POST', 'https://salla.tecfy.co/odoo/webhooks/sale_order', json=data)

            if response.json()["success"] == True:
                return True
            return str(response.json())
        except Exception as e: 
            _logger.error(str(e))
            return False

    def write(self, values):
        res = super(TecfySaleOrder, self).write(values)
        if res == False:
            return res
        self.processRecord(values)
        return res
    
    @api.model
    def create(self,values):
        values['tecfy_salla_update'] = False # must activate it on update only
        res = super(TecfySaleOrder, self).create(values)
        return res

    def getMerchantId(self, companyId):
        sql = "select * from res_company where id = {};".format(companyId)
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        if len(res) == 0:
            return 0
        if res[0]['tecfy_salla_merchant_id'] == None:
            return 0
        return res[0]

    def tryPost(self):
        orders = self.env['sale.order'].search(
            [('tecfy_is_pending', '=', True)], limit=100)
        for order in orders:
            merchantData = self.getMerchantId(order.company_id.id)
            merchantId = merchantData['tecfy_salla_merchant_id']
            tecfy_post_realtime = merchantData['tecfy_post_realtime']
            if tecfy_post_realtime == True:
                continue
            result = order.postToOdooNow(merchantId)
            if result != False:
                order.tecfy_is_pending = False
                self.env.cr.commit()
