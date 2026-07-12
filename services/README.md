# Services

Only services that cannot live safely in a Frappe app belong here. The first
service is `ai_control_plane`, responsible for model routing, tool permission
checks, retrieval, evaluations, and AI audit records. It must not write to the
ERP database directly.
