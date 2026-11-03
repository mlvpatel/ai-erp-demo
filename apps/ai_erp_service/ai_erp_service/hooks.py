app_name = "ai_erp_service"
app_title = "AI ERP Service"
app_publisher = "AI ERP Demo contributors"
app_description = "Auditable service work orders and technician closeout for AI ERP Demo"
app_email = "mlvpatel@users.noreply.github.com"
app_license = "agpl-3.0"

required_apps = ["erpnext", "ai_erp_core"]

fixture_auto_order = True
fixtures = [
	{
		"dt": "Role",
		"filters": [
			[
				"role_name",
				"in",
				["Service Manager", "Service Dispatcher", "Service Technician", "Service Closure Owner"],
			]
		],
	},
	{
		"dt": "Custom Field",
		"filters": [["name", "in", ["Sales Invoice-service_work_order"]]],
	}
]

permission_query_conditions = {
	"Service Location": "ai_erp_service.permissions.service_location_query",
	"Service Request": "ai_erp_service.permissions.service_request_query",
	"Service Work Order": "ai_erp_service.permissions.service_work_order_query",
	"Service Closure Exception": "ai_erp_service.permissions.service_closure_exception_query",
	"Service Technician Capability": "ai_erp_service.permissions.service_technician_capability_query",
}

has_permission = {
	"Service Location": "ai_erp_service.permissions.service_location_has_permission",
	"Service Request": "ai_erp_service.permissions.service_request_has_permission",
	"Service Work Order": "ai_erp_service.permissions.service_work_order_has_permission",
	"Service Closure Exception": "ai_erp_service.permissions.service_closure_exception_has_permission",
	"Service Technician Capability": "ai_erp_service.permissions.service_technician_capability_has_permission",
}

app_include_css = [
	"/assets/ai_erp_service/css/evidence_replay.css",
	"/assets/ai_erp_service/css/mobile_field.css",
]
# Service Work Order Desk JS lives only at
# ai_erp_service/doctype/service_work_order/service_work_order.js (Frappe auto-load).
# Do not also register doctype_js here — dual registration loads competing UIs.

scheduler_events = {
	"hourly": ["ai_erp_service.tasks.escalate_overdue_closure_exceptions"],
	"cron": {"*/5 * * * *": ["ai_erp_service.tasks.publish_queue_age_metric"]},
}

after_request = ["ai_erp_service.observability.record_permission_failure"]
