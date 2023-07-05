# Copyright 2018 David Juaneda - <djuaneda@sdi.es>
# Copyright 2023 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests import common, new_test_user


class TestMailActivityBoardMethods(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                no_reset_password=True,
                tracking_disable=True,
            )
        )
        # Create a user as 'Crm Salesman' and added few groups
        cls.employee = new_test_user(cls.env, login="csu")
        # Create a user who doesn't have access to anything except activities
        cls.employee2 = new_test_user(
            cls.env,
            login="alien",
            groups="mail_activity_board.group_show_mail_activity_board",
        )
        cls.activity1 = cls._create_mail_activity_type(
            cls, "Initial Contact", 5, "ACT 1 : Presentation, barbecue, ... "
        )
        cls.activity2 = cls._create_mail_activity_type(
            cls, "Call for Demo", 6, "ACT 2 : I want to show you my ERP !"
        )
        cls.activity3 = cls._create_mail_activity_type(
            cls,
            "Celebrate the sale",
            3,
            "ACT 3 : Beers for everyone because I am a good salesman !",
        )
        # I create an opportunity, as employee
        cls.partner = cls.env["res.partner"].create({"name": "Test partner"})

        # assure there isn't any mail activity yet
        cls.env["mail.activity"].sudo().search([]).unlink()

        cls.act1 = cls._create_mail_activity(
            cls, cls.activity1, cls.partner, cls.employee
        )
        cls.act2 = cls._create_mail_activity(
            cls, cls.activity2, cls.partner, cls.employee
        )
        cls.act3 = cls._create_mail_activity(
            cls, cls.activity3, cls.partner, cls.employee
        )

    def _create_mail_activity_type(self, name, delay_count, summary):
        return self.env["mail.activity.type"].create(
            {
                "name": name,
                "delay_count": delay_count,
                "delay_unit": "days",
                "summary": summary,
                "res_model": "res.partner",
            }
        )

    def _create_mail_activity(self, activity_type, record, user):
        model = self.env["ir.model"].sudo().search([("model", "=", record._name)])
        return (
            self.env["mail.activity"]
            .sudo()
            .create(
                {
                    "activity_type_id": activity_type.id,
                    "note": "Partner activity %s." % activity_type.id,
                    "res_id": record.id,
                    "res_model_id": model.id,
                    "user_id": user.id,
                }
            )
        )

    def get_view(self, activity):
        action = activity.open_origin()
        result = self.env[action.get("res_model")].load_views(action.get("views"))
        return result.get("fields_views").get(action.get("view_mode"))

    def test_open_origin_res_partner(self):
        """This test case checks
        - If the method redirects to the form view of the correct one
        of an object of the 'res.partner' class to which the activity
        belongs.
        """
        # Id of the form view for the class 'crm.lead', type 'lead'
        form_view_partner_id = self.env.ref("base.view_partner_form").id

        # Id of the form view return open_origin()
        view = self.get_view(self.act1)

        # Check the next view is correct
        self.assertEqual(form_view_partner_id, view.get("view_id"))

        # Id of the form view return open_origin()
        view = self.get_view(self.act2)

        # Check the next view is correct
        self.assertEqual(form_view_partner_id, view.get("view_id"))

        # Id of the form view return open_origin()
        view = self.get_view(self.act3)

        # Check the next view is correct
        self.assertEqual(form_view_partner_id, view.get("view_id"))

    def test_redirect_to_activities(self):
        """This test case checks
        - if the method returns the correct action,
        - if the correct activities are shown.
        """
        action_id = self.env.ref("mail_activity_board.open_boards_activities").id
        action = self.partner.redirect_to_activities(**{"id": self.partner.id})
        self.assertEqual(action.get("id"), action_id)

        kwargs = {"groupby": ["activity_type_id"]}
        kwargs["domain"] = action.get("domain")

        result = self.env[action.get("res_model")].load_views(action.get("views"))
        fields = result.get("fields_views").get("kanban").get("fields")
        kwargs["fields"] = list(fields.keys())

        result = self.env["mail.activity"].read_group(**kwargs)

        acts = []
        for group in result:
            records = self.env["mail.activity"].search_read(
                domain=group.get("__domain"), fields=kwargs["fields"]
            )
            acts += [record_id.get("id") for record_id in records]

        for act in acts:
            self.assertIn(act, self.partner_client.activity_ids.ids)

    def test_related_model_instance(self):
        """This test case checks the direct access from the activity to the
        linked model instance
        """
        self.assertEqual(self.act3.related_model_instance, self.partner)
        self.act3.write({"res_id": False, "res_model": False})
        self.assertFalse(self.act3.related_model_instance)
