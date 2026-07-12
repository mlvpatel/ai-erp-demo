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
	"Service Work Order": "ai_erp_service.permissions.service_work_order_query",
	"Service Closure Exception": "ai_erp_service.permissions.service_closure_exception_query",
}

has_permission = {
	"Service Work Order": "ai_erp_service.permissions.service_work_order_has_permission",
	"Service Closure Exception": "ai_erp_service.permissions.service_closure_exception_has_permission",
}

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "ai_erp_service",
# 		"logo": "/assets/ai_erp_service/logo.png",
# 		"title": "AI ERP Service",
# 		"route": "/ai_erp_service",
# 		"has_permission": "ai_erp_service.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ai_erp_service/css/ai_erp_service.css"
# app_include_js = "/assets/ai_erp_service/js/ai_erp_service.js"

# include js, css files in header of web template
# web_include_css = "/assets/ai_erp_service/css/ai_erp_service.css"
# web_include_js = "/assets/ai_erp_service/js/ai_erp_service.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ai_erp_service/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ai_erp_service/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ai_erp_service.utils.jinja_methods",
# 	"filters": "ai_erp_service.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ai_erp_service.install.before_install"
# after_install = "ai_erp_service.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "ai_erp_service.uninstall.before_uninstall"
# after_uninstall = "ai_erp_service.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ai_erp_service.utils.before_app_install"
# after_app_install = "ai_erp_service.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ai_erp_service.utils.before_app_uninstall"
# after_app_uninstall = "ai_erp_service.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "ai_erp_service.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ai_erp_service.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ai_erp_service.tasks.all"
# 	],
# 	"daily": [
# 		"ai_erp_service.tasks.daily"
# 	],
# 	"hourly": [
# 		"ai_erp_service.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ai_erp_service.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ai_erp_service.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "ai_erp_service.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "ai_erp_service.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ai_erp_service.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ai_erp_service.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["ai_erp_service.utils.before_request"]
# after_request = ["ai_erp_service.utils.after_request"]

# Job Events
# ----------
# before_job = ["ai_erp_service.utils.before_job"]
# after_job = ["ai_erp_service.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"ai_erp_service.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
