import requests
from odoo import fields, models, exceptions, _

class TecfySallaStatus(models.Model):
    _name = 'tecfysalla.status'
    _description= 'Salla Status'
    name = fields.Char(string="Name")
    salla_status_id = fields.Integer(required=True,string="Salla Id")
    