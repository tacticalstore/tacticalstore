from odoo import  fields, models

class TecfyCompany(models.Model):

    _inherit = "res.company"
    tecfy_salla_order_status_update = fields.Boolean(required=False, string="Update Salla Order", help="if checked, then the connector will update salla order to in_progress when approve sales order in Odoo")
    tecfy_post_realtime = fields.Boolean(required=False,string="Post To Salla Realtime",help="Immediately post to Salla when create sales order in Odoo or update quantity in Odoo")
