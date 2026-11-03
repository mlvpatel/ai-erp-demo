app_name = "ai_erp_core"
app_title = "AI ERP Core"
app_publisher = "AI ERP Demo contributors"
app_description = "Cross-industry policy and audit helpers for AI ERP Demo"
app_email = "mlvpatel@users.noreply.github.com"
app_license = "agpl-3.0"

fixture_auto_order = True
fixtures = [
	{
		"dt": "Role",
		"filters": [["role_name", "in", ["AI Proposal Approver", "AI Proposal Requester"]]],
	}
]

permission_query_conditions = {
	"AI Proposal": "ai_erp_core.permissions.ai_proposal_query",
}

has_permission = {
	"AI Proposal": "ai_erp_core.permissions.ai_proposal_has_permission",
}
