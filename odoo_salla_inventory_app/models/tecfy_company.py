from odoo import fields, models

class TecfyCompany(models.Model):
    
    _inherit = "res.company"

    tecfy_salla_merchant_id = fields.Char(required=False,string="Salla Merchant Id",help="if you have multi Salla stores, you can separate by comma like 11111,22222")
    tecfy_salla_ignore_error = fields.Boolean(required=False,string="Ignore Salla Error",help="Don't stop Odoo process when Salla connection is down")
    tecfy_salla_location_ids = fields.Many2many("stock.location",string="Salla Locations")
    tecfy_salla_update_quantity = fields.Boolean(required=False,string="Update Salla Quantity")
    tecfy_salla_is_sync = fields.Boolean(string="Is sync in progress")
    tecfy_salla_sync_id = fields.Integer(string="Current sync")
    