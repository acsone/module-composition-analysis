# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models
from odoo.tools.safe_eval import safe_eval


class OdooProjectStat(models.Model):
    _name = "odoo.project.stat"
    _description = "Odoo Project Stats"
    _rec_name = "name"
    _order = "sequence, name"

    odoo_project_id = fields.Many2one(
        comodel_name="odoo.project",
        ondelete="cascade",
        string="Project",
        required=True,
        readonly=True,
    )
    config_id = fields.Many2one(
        comodel_name="odoo.project.stat.config",
        ondelete="restrict",
        string="Project Stat Configuration",
        required=True,
        readonly=True,
    )
    sequence = fields.Integer(related="config_id.sequence", store=True)
    name = fields.Char(related="config_id.name", store=True)
    color = fields.Char(related="config_id.color")
    modules_count = fields.Integer(readonly=True)
    sloc = fields.Integer(string="Lines of code", readonly=True)

    _sql_constraints = [
        (
            "odoo_project_config_uniq",
            "UNIQUE (odoo_project_id, config_id)",
            "This project stats record already exists.",
        ),
    ]

    def _generate_stats(self, odoo_project_id):
        """Generate the stats for a given `odoo_project_id`."""
        odoo_project = self.env["odoo.project"].browse(odoo_project_id).exists()
        odoo_project.ensure_one()
        modules = odoo_project.project_module_ids
        total_count = len(modules)
        total_sloc = (
            sum(modules.mapped("sloc_python"))
            + sum(modules.mapped("sloc_xml"))
            + sum(modules.mapped("sloc_js"))
            + sum(modules.mapped("sloc_css"))
        )
        configs = self.env["odoo.project.stat.config"].search([])
        for config in configs:
            # Create or update existing stat record
            stat = odoo_project.module_stats_ids.filtered(
                lambda o: o.config_id == config
            )
            values = self._generate_stat_values(odoo_project, config, total_count)
            if stat:
                stat.sudo().write(values)
            else:
                self.sudo().create(values)
        stat_residual = odoo_project.module_stats_ids.filtered(
            lambda o: o.config_id.residual
        )
        if stat_residual:
            other_stats = odoo_project.module_stats_ids - stat_residual
            stat_residual.sudo().write(
                {
                    "modules_count": (
                        total_count - sum(other_stats.mapped("modules_count"))
                    ),
                    "sloc": (total_sloc - sum(other_stats.mapped("sloc"))),
                }
            )
        return True

    def _generate_stat_values(self, odoo_project, config, total_count):
        # Counter
        if config.residual:
            modules_count = 0
            sloc = 0
        else:
            domain = safe_eval(config.domain)
            # FIXME: use odoo.osv.expression.AND
            domain.append(("odoo_project_id", "=", odoo_project.id))
            modules = self.env["odoo.project.module"].search(domain)
            modules_count = len(modules)
            sloc = (
                sum(modules.mapped("sloc_python"))
                + sum(modules.mapped("sloc_xml"))
                + sum(modules.mapped("sloc_js"))
                + sum(modules.mapped("sloc_css"))
            )
        return {
            "odoo_project_id": odoo_project.id,
            "config_id": config.id,
            "modules_count": modules_count,
            "sloc": sloc,
        }
