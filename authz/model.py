"""The OpenFGA authorization model: RBAC (organization roles) + FGA (per-expense sharing).

Relations, in plain English:
  - organization.admin: users with this relation can view/edit/delete/share
    every expense in the org - this is the RBAC layer (a role).
  - organization.member: everyone, implicitly (admins are members too).
  - expense.owner / expense.viewer / expense.editor: direct, per-expense
    grants - this is the FGA layer (an owner can share one specific expense
    with one specific other user, independent of any role).
  - expense.can_view/can_edit/can_delete/can_share: the actual permissions
    checked by the app, computed as a union of the relations above. Nothing
    outside this module should ever check owner/viewer/editor/admin
    directly - always check a can_* relation.

There is a single, fixed organization for the whole app (ORG_OBJECT) -
this app has no multi-tenancy concept, so one org covering every user and
expense is sufficient to get a real RBAC admin role without inventing
tenants that don't otherwise exist here.
"""

STORE_NAME = "expense-tracker"
ORG_OBJECT = "organization:main"

AUTHORIZATION_MODEL = {
    "schema_version": "1.1",
    "type_definitions": [
        {"type": "user", "relations": {}, "metadata": None},
        {
            "type": "organization",
            "relations": {
                "admin": {"this": {}},
                "member": {
                    "union": {
                        "child": [
                            {"this": {}},
                            {"computedUserset": {"relation": "admin"}},
                        ]
                    }
                },
            },
            "metadata": {
                "relations": {
                    "admin": {"directly_related_user_types": [{"type": "user"}]},
                    "member": {"directly_related_user_types": [{"type": "user"}]},
                }
            },
        },
        {
            "type": "expense",
            "relations": {
                "parent_org": {"this": {}},
                "owner": {"this": {}},
                "viewer": {"this": {}},
                "editor": {"this": {}},
                "can_view": {
                    "union": {
                        "child": [
                            {"computedUserset": {"relation": "viewer"}},
                            {"computedUserset": {"relation": "owner"}},
                            {"computedUserset": {"relation": "editor"}},
                            {
                                "tupleToUserset": {
                                    "tupleset": {"relation": "parent_org"},
                                    "computedUserset": {"relation": "admin"},
                                }
                            },
                        ]
                    }
                },
                "can_edit": {
                    "union": {
                        "child": [
                            {"computedUserset": {"relation": "owner"}},
                            {"computedUserset": {"relation": "editor"}},
                            {
                                "tupleToUserset": {
                                    "tupleset": {"relation": "parent_org"},
                                    "computedUserset": {"relation": "admin"},
                                }
                            },
                        ]
                    }
                },
                "can_delete": {
                    "union": {
                        "child": [
                            {"computedUserset": {"relation": "owner"}},
                            {
                                "tupleToUserset": {
                                    "tupleset": {"relation": "parent_org"},
                                    "computedUserset": {"relation": "admin"},
                                }
                            },
                        ]
                    }
                },
                "can_share": {
                    "union": {
                        "child": [
                            {"computedUserset": {"relation": "owner"}},
                            {
                                "tupleToUserset": {
                                    "tupleset": {"relation": "parent_org"},
                                    "computedUserset": {"relation": "admin"},
                                }
                            },
                        ]
                    }
                },
            },
            "metadata": {
                "relations": {
                    "parent_org": {"directly_related_user_types": [{"type": "organization"}]},
                    "owner": {"directly_related_user_types": [{"type": "user"}]},
                    "viewer": {"directly_related_user_types": [{"type": "user"}]},
                    "editor": {"directly_related_user_types": [{"type": "user"}]},
                }
            },
        },
    ],
}
