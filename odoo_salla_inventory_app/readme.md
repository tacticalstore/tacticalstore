
```
sql = "delete from tecfysalla_quantity where product_id not in (select id from product_product)"
env.cr.execute(sql)
env.cr.commit()

count = 5000
companies = env['res.company'].search([('tecfy_salla_update_quantity', '=', True)])
for company in companies:
    sync_id = company.tecfy_salla_sync_id
    if company.tecfy_salla_is_sync != True:
      sync_id = company.tecfy_salla_sync_id + 1
      sql = "update res_company set tecfy_salla_is_sync = {}, tecfy_salla_sync_id = {} where id = {}".format(True,  sync_id, company.id)
      env.cr.execute(sql)
      env.cr.commit()

    sql = "select p.id, t.name, t.company_id, p.product_tmpl_id  from product_product p left join product_template t on t.id = p.product_tmpl_id where t.detailed_type = 'product' and p.id not in (select product_id from tecfysalla_quantity where sync_id = {} ) limit {};".format(company.tecfy_salla_sync_id, count)
    env.cr.execute(sql)
    productsList = env.cr.dictfetchall()
    # productIds = [p['id'] for p in productsList]
    # products = env['product.product'].search([('id', 'in', productIds)])
    
    # log('Products {} / {}'.format(len(products),len(productIds)), level='info')
    
    for product in productsList:
        # if(product.company_id.id != False and product.company_id.id != company.id):
        #     continue
        quantities = env['stock.quant'].search(
            [('product_id', '=', product['id']),('location_id' ,'in', company.tecfy_salla_location_ids.ids)])
        odoo_qty = 0
        for qty in quantities:
          odoo_qty += qty.available_quantity
        salla_qty = env['tecfysalla.quantity'].search([('product_id', '=', product['id']), ('company_id', '=', company.id)])
        if len(salla_qty) == 0:
            env['tecfysalla.quantity'].create({
                'product_id': product['id'],
                'company_id': company.id,
                'product_tmpl_id': product['product_tmpl_id'],
                'display_name': product['name'],
                'available_quantity': odoo_qty,
                'merchant_id': company.tecfy_salla_merchant_id,
                'is_posted': False,
                'sync_id': sync_id
            })
            env.cr.commit()
        else:
            salla_qty_rec = salla_qty[0]
            if salla_qty_rec.available_quantity != odoo_qty or salla_qty_rec.merchant_id != company.tecfy_salla_merchant_id:
              sql = "update tecfysalla_quantity set available_quantity = {}, write_date =now(),is_posted={},merchant_id={},sync_id={} where id =  {}".format(odoo_qty,False,company.tecfy_salla_merchant_id,sync_id, salla_qty_rec.id)
              env.cr.execute(sql)
            else:
              sql = "update tecfysalla_quantity set sync_id={} where id =  {}".format(sync_id, salla_qty_rec.id)
              env.cr.execute(sql)
    if len(productsList) == 0: # if we finished all products
        sql = "update res_company set tecfy_salla_is_sync = {} where id =  {}".format(False, company.id)
        log('reset sync, final products, {} '.format(len(productsList)), level='info')
        env.cr.execute(sql)

    env.cr.commit()

```