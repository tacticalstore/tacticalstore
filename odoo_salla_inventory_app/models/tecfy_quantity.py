import requests
from odoo import fields, models, exceptions, _


class TecfySallaQuantity(models.Model):

    _name = 'tecfysalla.quantity'
    _description = "Salla Quantity Model"
    product_id = fields.Many2one('product.product', string="Product")
    location_id = fields.Many2one('stock.location', string="Location")
    company_id = fields.Many2one('res.company', string="company")
    product_tmpl_id = fields.Many2one('product.template', string="template")
    display_name = fields.Char(string="Name")
    write_date = fields.Date(string="Salla Update Time")
    available_quantity = fields.Integer(string="Salla Quantity")
    is_posted = fields.Boolean(string="Is Posted")
    merchant_id = fields.Char(required=False, string="Salla Merchant Id")
    error = fields.Char(string="Error")
    sync_id = fields.Integer(string="Sync Id")
    
    def postToOdooNow(self,data):       
        try:
            response = requests.request('POST', 'https://salla.tecfy.co/odoo/webhooks/stock_quant_batch', json=data)
            if response.status_code != 200:
                return { 'success': False, 'message': 'Error Posting to Salla, Response Code is ' + str(response.status_code)}
            json = response.json()
            if json == False:
                return { 'success': False, 'message': 'Error Updating Salla, cannot read response'}
            if "success" in json :
                return json
            return { 'success': False, 'message': 'Error'}
        except requests.ConnectionError as e:
            return { 'success': False, 'message': 'Error Updating Salla,connError, ' + str(e)}
        except requests.exceptions.HTTPError as e:
            return { 'success': False, 'message': 'Error Updating Salla,httperror, ' + str(e)}
        except Exception as e:
            return { 'success': False, 'message': str(e)}
        except:
            return { 'success': False, 'message': 'Error Updating Salla, Ganaral Error'}

    def prepareQuantities(self):
        count = 5000
        companies = self.env['res.company'].search([('tecfy_salla_update_quantity', '=', True)])
        for company in companies:
            if company.tecfy_salla_is_sync != True:
                company.tecfy_salla_is_sync = True
                company.tecfy_salla_sync_id = company.tecfy_salla_sync_id + 1
                self.env.cr.commit()
            
            sql = "select p.id from product_product p left join product_template t on t.id = p.product_tmpl_id where t.detailed_type = 'product' and p.id not in (select product_id from tecfysalla_quantity where sync_id = {} ) limit {};".format(company.tecfy_salla_sync_id, count)
            self._cr.execute(sql)
            res = self._cr.dictfetchall()
            productIds = [p['id'] for p in res]
            
            products = self.env['product.product'].search([('id', 'in', productIds)]) 
            
            for product in products:
                if(product.company_id.id != False and product.company_id.id != company.id):
                    continue
                quantities = self.env['stock.quant'].search(
                    [('product_id', '=', product.id),('location_id' ,'in', company.tecfy_salla_location_ids.ids)])
                odoo_qty = 0
                for qty in quantities:
                        odoo_qty += qty.available_quantity
                salla_qty = self.env['tecfysalla.quantity'].search(
                    [('product_id', '=', product.id), ('company_id', '=', company.id)])
                if len(salla_qty) == 0:
                    self.env['tecfysalla.quantity'].create({
                        'product_id': product.id,
                        'company_id': company.id,
                        'product_tmpl_id': product.product_tmpl_id.id,
                        'display_name': product.display_name,
                        'available_quantity': odoo_qty,
                        'merchant_id': company.tecfy_salla_merchant_id,
                        'is_posted': False,
                        'sync_id': company.tecfy_salla_sync_id
                    })
                else:
                    salla_qty_rec = salla_qty[0]
                    if salla_qty_rec.available_quantity != odoo_qty or salla_qty_rec.merchant_id != company.tecfy_salla_merchant_id:
                        salla_qty_rec.available_quantity = odoo_qty
                        salla_qty_rec.write_date = fields.Datetime.now()
                        salla_qty_rec.is_posted = False
                        salla_qty_rec.merchant_id = company.tecfy_salla_merchant_id
                    salla_qty_rec.sync_id = company.tecfy_salla_sync_id
                self.env.cr.commit()
            if len(products) < count: # if we finished all products
                company.tecfy_salla_is_sync = False
                self.env.cr.commit()
            
    def tryPost(self):
        companies = self.env['res.company'].search(
            [('tecfy_salla_update_quantity', '=', True)])
        for company in companies:
            records = self.env['tecfysalla.quantity'].search(
                [('is_posted', '=', False),('company_id','=',company.id)], limit=100)
            if len(records) == 0:
                continue
            data = []
            for rec in records:
                data.append({
                    'product_id': rec.product_id.id,
                    'merchant_id': rec.merchant_id,
                    'display_name': rec.display_name,
                    'product_tmpl_id': rec.product_tmpl_id.id,
                    'company_id': rec.company_id.id,
                    'location_id': rec.location_id.id,
                    'available_quantity': rec.available_quantity,
                })
            result = self.postToOdooNow({'merchant_id':company.tecfy_salla_merchant_id, 'products' : data})
            for rec in records:
                if result["success"] != False:
                    rec.is_posted = True
                    rec.error = ''
                else:
                    rec.error = str(result["message"])
            self.env.cr.commit()
