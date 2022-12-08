import base64
from ast import literal_eval
from odoo import api, models, fields
import json
from datetime import datetime


class ConfSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_reports = fields.Boolean(string="Sale Report", required=True)
    customer_id = fields.Many2many('res.partner', string="Customer", required=True)
    sale_team = fields.Many2one('crm.team', string="Sale Team", required=True)
    report_type = fields.Selection([('weekly', 'Weekly'), ('monthly', 'Monthly')],
                                   string="Report Type", required=True)
    from_date = fields.Datetime(string="From Date", required=True)
    to_date = fields.Datetime(string="To Date", required=True)

    @api.model
    def set_values(self):
        res = super(ConfSettings, self).set_values()
        self.env['ir.config_parameter'].set_param(
            'sale_report.sale_reports', self.sale_reports)
        self.env['ir.config_parameter'].set_param(
            'sale_report.customer_id', self.customer_id.ids)
        self.env['ir.config_parameter'].set_param(
            'sale_report.sale_team', self.sale_team.id)
        self.env['ir.config_parameter'].set_param(
            'sale_report.report_type', self.report_type)
        self.env['ir.config_parameter'].set_param(
            'sale_report.from_date', self.from_date)
        self.env['ir.config_parameter'].set_param(
            'sale_report.to_date', self.to_date)
        # print(self.sale_team.id)
        return res

    @api.model
    def get_values(self):
        res = super(ConfSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        is_sale_reports = params.get_param('sale_report.sale_reports')
        res.update(sale_reports=is_sale_reports)
        is_customers_id = params.get_param('sale_report.customer_id')
        res.update(customer_id=[(6, 0, literal_eval(is_customers_id))] if is_customers_id else False)
        is_sale_team = params.get_param('sale_report.sale_team')
        res.update(sale_team=int(is_sale_team))
        is_report_type = params.get_param('sale_report.report_type')
        res.update(report_type=is_report_type)
        is_from_date = params.get_param('sale_report.from_date')
        res.update(from_date=is_from_date)
        is_to_date = params.get_param('sale_report.to_date')
        res.update(to_date=is_to_date)
        # print(res)
        return res


class Sale(models.Model):
    _inherit = 'sale.order'

    # Send Email on Every week

    def sale_order_action(self):

        params = self.env['ir.config_parameter'].sudo()
        is_customers_id = params.get_param('sale_report.customer_id')
        is_sale_team = params.get_param('sale_report.sale_team')
        is_report_type = params.get_param('sale_report.report_type')
        is_from_date = params.get_param('sale_report.from_date')

        is_to_date = params.get_param('sale_report.to_date')
        # print('to', is_to_date)
        # print('to', type(is_to_date))

        from_date = datetime.strptime(is_from_date, '%Y-%m-%d %H:%M:%S')
        # print("a", from_date)
        # # print("b", is_from_date)
        # print("c", type(from_date))
        #
        to_date = datetime.strptime(is_to_date, '%Y-%m-%d %H:%M:%S')
        # print("a", to_date)
        # # print("b", is_to_date)
        # print("c", type(to_date))

        customer_id = json.loads(is_customers_id)
        # print("e", type(customer_id))
        # print("e", customer_id)
        # print("---", is_customers_id)
        # print("---", customer_id)
        # print(type(is_customers_id))
        # print(type(customer_id))

        sale_team = json.loads(is_sale_team)
        # print("000", is_sale_team)
        # print("000", sale_team)
        # print("000",type(sale_team))
        if is_report_type == 'weekly':
            var = """select sale_order.name as sname,res_partner.name as pname,sale_order.date_order as date,
            sale_order.amount_total as total from sale_order inner join res_partner on
            sale_order.partner_id=res_partner.id"""

            if from_date:
                new_var = """ and sale_order.date_order >= '%s' """ % from_date
                var += new_var

            if to_date:
                new_var = """ and sale_order.date_order <= '%s' """ % to_date
                var += new_var

            if sale_team:
                new_var = """ and sale_order.team_id = {sale_team}""".format(sale_team=sale_team)
                # print(new_var)
                var += new_var

            if len(customer_id) == 1:
                new_var = """ and sale_order.partner_id = {customer_id[0]}""".format(customer_id=customer_id)
                print(new_var)
                var += new_var
            elif len(customer_id) > 1:
                customer_ids = tuple(customer_id)
                new_var = """ and sale_order.partner_id in {customer_ids}""".format(customer_ids=customer_ids)
                print(new_var, "multi")
                var += new_var
            self.env.cr.execute(var)
            record = self.env.cr.dictfetchall()
            # print(record)
            data = {
                'query': record
            }
            print(data)

            # Create Attachment in Mail

            sale_report_id = self.env.ref('sale_report.action_sale_report')._render_qweb_pdf(self, data=data)
            data_record = base64.b64encode(sale_report_id[0])
            ir_values = {
                'name': 'Sale Report',
                'type': 'binary',
                'datas': data_record,
                'store_fname': data_record,
                'mimetype': 'application/pdf',
                'res_model': 'sale.order',
            }
            report_attachment = self.env['ir.attachment'].sudo().create(ir_values)

            # Send mail to customers and sale managers

            customer_list = []
            customers = self.env['res.partner'].search([('id', '=', customer_id)])
            # print("customers", customers)
            for rec in customers:
                customer_list.append(rec.email)
                # print("cust_list", customer_list)
            users = self.env['res.users'].search([]).filtered(
                lambda lm: lm.has_group('sales_team.group_sale_manager'))
            # print(users)
            for rec in users:
                customer_list.append(rec.login)
                for dec in customer_list:
                    # print('----------------', customer_list)
                    email_values = {
                        'email_to': dec,
                        'attachment_ids': report_attachment
                    }
                    print('email_values', email_values)
                    mail = self.env['mail.mail'].sudo().create(email_values)
                    mail.send()

                    # Send Email on Every month

    def sale_order_action2(self):

        params = self.env['ir.config_parameter'].sudo()
        is_customers_id = params.get_param('sale_report.customer_id')
        is_sale_team = params.get_param('sale_report.sale_team')
        is_report_type = params.get_param('sale_report.report_type')
        is_from_date = params.get_param('sale_report.from_date')

        is_to_date = params.get_param('sale_report.to_date')
        # print('to', is_to_date)
        # print('to', type(is_to_date))

        from_date = datetime.strptime(is_from_date, '%Y-%m-%d %H:%M:%S')
        # print("a", from_date)
        # # print("b", is_from_date)
        # print("c", type(from_date))
        #
        to_date = datetime.strptime(is_to_date, '%Y-%m-%d %H:%M:%S')
        # print("a", to_date)
        # # print("b", is_to_date)
        # print("c", type(to_date))

        customer_id = json.loads(is_customers_id)
        # print("e", type(customer_id))
        # print("e", customer_id)
        # print("---", is_customers_id)
        # print("---", customer_id)
        # print(type(is_customers_id))
        # print(type(customer_id))

        sale_team = json.loads(is_sale_team)
        # print("000", is_sale_team)
        # print("000", sale_team)
        # print("000",type(sale_team))
        if is_report_type == 'monthly':
            var = """select sale_order.name as sname,res_partner.name as pname,sale_order.date_order as date,
            sale_order.amount_total as total from sale_order inner join res_partner on
            sale_order.partner_id=res_partner.id"""

            if from_date:
                new_var = """ and sale_order.date_order >= '%s' """ % from_date
                var += new_var

            if to_date:
                new_var = """ and sale_order.date_order <= '%s' """ % to_date
                var += new_var

            if sale_team:
                new_var = """ and sale_order.team_id = {sale_team}""".format(sale_team=sale_team)
                # print(new_var)
                var += new_var

            if len(customer_id) == 1:
                new_var = """ and sale_order.partner_id = {customer_id[0]}""".format(customer_id=customer_id)
                print(new_var)
                var += new_var
            elif len(customer_id) > 1:
                new = tuple(customer_id)
                new_var = """ and sale_order.partner_id in {new}""".format(new=new)
                print(new_var, "multi")
                var += new_var

            self.env.cr.execute(var)
            record = self.env.cr.dictfetchall()
            # print(record)
            data = {
                'query': record
            }
            print(data)

            # Create Attachment in Mail

            sale_report_id = self.env.ref('sale_report.action_sale_report')._render_qweb_pdf(self, data=data)
            data_record = base64.b64encode(sale_report_id[0])
            ir_values = {
                'name': 'Sale Report',
                'type': 'binary',
                'datas': data_record,
                'store_fname': data_record,
                'mimetype': 'application/pdf',
                'res_model': 'sale.order',
            }
            report_attachment = self.env['ir.attachment'].sudo().create(ir_values)

            # Send mail to customers and sale managers

            customer_list = []
            customers = self.env['res.partner'].search([('id', '=', customer_id)])
            # print("customers", customers)
            for rec in customers:
                customer_list.append(rec.email)
                # print("cust_list", customer_list)
            users = self.env['res.users'].search([]).filtered(
                lambda lm: lm.has_group('sales_team.group_sale_manager'))
            # print(users)
            for rec in users:
                customer_list.append(rec.login)
                for dec in customer_list:
                    # print('----------------', customer_list)
                    email_values = {
                        'email_to': dec,
                        'attachment_ids': report_attachment
                    }
                    print('email_values', email_values)
                    mail = self.env['mail.mail'].sudo().create(email_values)
                    mail.send()
