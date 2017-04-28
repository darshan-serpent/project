# -*- coding: utf-8 -*-
# Copyright 2017 Eficent Business and IT Consulting Services S.L.
# Copyright 2017 Luxim d.o.o.
# Copyright 2017 Matmoz d.o.o.
# Copyright 2017 Deneroteam.
# Copyright 2017 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from openerp import api, fields, models, _


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    _order = 'complete_wbs_code'

    @api.multi
    def get_child_accounts(self):
        result = {}
        for curr_id in self.ids:
            result[curr_id] = True
        # Now add the children
        self.env.cr.execute('''
        WITH RECURSIVE children AS (
        SELECT parent_id, id
        FROM account_analytic_account
        WHERE parent_id IN %s
        UNION ALL
        SELECT a.parent_id, a.id
        FROM account_analytic_account a
        JOIN children b ON(a.parent_id = b.id)
        )
        SELECT * FROM children order by parent_id
        ''', (tuple(self.ids),))
        res = self.env.cr.fetchall()
        for x, y in res:
            result[y] = True
        return result

    @api.multi
    @api.depends('code')
    def _complete_wbs_code_calc(self):
        for account in self:
            data = []
            acc = account
            while acc:
                if acc.code:
                    data.insert(0, acc.code)

                acc = acc.parent_id
            if data:
                if len(data) >= 2:
                    data = '/'.join(data)
                else:
                    data = data[0]
                data = '[' + data + '] '
            account.complete_wbs_code = data or ''

    @api.multi
    @api.depends('name')
    def _complete_wbs_name_calc(self):
        for account in self:
            data = []
            acc = account
            while acc:
                if acc.name:
                    data.insert(0, acc.name)

                acc = acc.parent_id
            if data:
                if len(data) >= 2:
                    data = '/'.join(data)
                else:
                    data = data[0]
            account.complete_wbs_name = data or ''

    @api.multi
    def _wbs_indent_calc(self):
        for account in self:
            data = []
            acc = account
            while acc:
                if acc.name and acc.parent_id.parent_id:
                    data.insert(0, '>')

                acc = acc.parent_id
            if data:
                if len(data) >= 2:
                    data = ''.join(data)
                else:
                    data = data[0]
            account.wbs_indent = data or ''

    @api.multi
    @api.depends('account_class')
    def _get_project_account_id(self):
        for account in self:
            acc = account
            while acc:
                if acc.account_class == 'project':
                    account.project_analytic_account_id = acc.id
                    break
                acc = acc.parent_id

    @api.model
    def _default_parent(self):
        return self.env.context.get('parent_id', False)

    @api.model
    def _default_partner(self):
        return self.env.context.get('partner_id', False)

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', False)

    wbs_indent = fields.Char(
        compute=_wbs_indent_calc,
        string='Level',
        readonly=True
    )
    complete_wbs_code_calc = fields.Char(
        compute=_complete_wbs_code_calc,
        string='Full WBS Code',
        help='Computed WBS code'
    )
    complete_wbs_code = fields.Char(
        compute=_complete_wbs_code_calc,
        string='Full WBS Code',
        help='The full WBS code describes the full path of this component '
             'within the project WBS hierarchy',
        store=True
    )
    complete_wbs_name = fields.Char(
        compute=_complete_wbs_name_calc,
        string='Full WBS path',
        help='Full path in the WBS hierarchy',
        store=True
    )
    project_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        compute=_get_project_account_id,
        string='Analytic Account',
        store=True
    )
    user_id = fields.Many2one(
        'res.users', 'Project Manager', track_visibility='onchange',
        default=_default_user)
    manager_id = fields.Many2one('res.users', 'Account Manager',
                                 track_visibility='onchange')
    date_start = fields.Date('Start Date')
    date = fields.Date('Expiration Date', select=True,
                       track_visibility='onchange')
    state = fields.Selection(
        [('template', 'Template'), ('draft', 'New'), ('open', 'In Progress'),
         ('pending', 'To Renew'), ('close', 'Closed'),
         ('cancelled', 'Cancelled')], 'Status', required=True,
        track_visibility='onchange')

    account_class = fields.Selection(
        [('project', 'Project'), ('phase', 'Phase'),
         ('deliverable', 'Deliverable'),
         ('work_package', 'Work Package')], 'Class',
        help='The classification allows you to create a proper project '
             'Work Breakdown Structure'
    )
    parent_id = fields.Many2one(default=_default_parent)
    partner_id = fields.Many2one(default=_default_partner)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        args = args[:]
        if name:
            accountbycode = self.search(
                [(
                    'complete_wbs_code',
                    'ilike',
                    '%%%s%%' % name
                )] + args, limit=limit
            )
            accountbyname = self.search(
                [('complete_wbs_name', 'ilike', '%%%s%%' % name)] + args,
                limit=limit
            )
            account = accountbycode + accountbyname
        else:
            account = self.search(args, limit=limit)
        return account.name_get()

    @api.multi
    @api.depends('code')
    def code_get(self):
        res = []
        for account in self:
            data = []
            acc = account
            while acc:
                if acc.code:
                    data.insert(0, acc.code)
                else:
                    data.insert(0, '')

                acc = acc.parent_id
            data = '/'.join(data)
            res.append((account.id, data))
        return res

    @api.multi
    @api.depends('name')
    def name_get(self):
        res = []
        for account in self:
            data = []
            acc = account
            while acc:
                if acc.name:
                    data.insert(0, acc.name)
                else:
                    data.insert(0, '')
                acc = acc.parent_id

            data = '/'.join(data)
            res2 = account.code_get()
            if res2 and res2[0][1]:
                data = '[' + res2[0][1] + '] ' + data

            res.append((account.id, data))
        return res
