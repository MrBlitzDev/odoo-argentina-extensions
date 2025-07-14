# -*- coding: utf-8 -*-
# from odoo import http


# class L10nArAfipwsWsct(http.Controller):
#     @http.route('/l10n_ar_afipws_wsct/l10n_ar_afipws_wsct', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_ar_afipws_wsct/l10n_ar_afipws_wsct/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_ar_afipws_wsct.listing', {
#             'root': '/l10n_ar_afipws_wsct/l10n_ar_afipws_wsct',
#             'objects': http.request.env['l10n_ar_afipws_wsct.l10n_ar_afipws_wsct'].search([]),
#         })

#     @http.route('/l10n_ar_afipws_wsct/l10n_ar_afipws_wsct/objects/<model("l10n_ar_afipws_wsct.l10n_ar_afipws_wsct"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_ar_afipws_wsct.object', {
#             'object': obj
#         })

