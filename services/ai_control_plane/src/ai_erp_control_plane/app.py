"""HTTP boundary for the stateless AI control plane."""

import hmac
import logging
import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import ProposalResponse, ServiceCloseoutSummaryRequest
from .openai_provider import OpenAIConfig, OpenAIProviderError, render_openai
from .render import render_development_template


logger = logging.getLogger("ai_erp_control_plane.provider")

app = FastAPI(
	title="AI ERP Control Plane API",
	version="1.2.0",
	description=(
		"Site-scoped, draft-only AI proposal boundary. The control plane never has "
		"credentials for an ERP database and never receives permission to post ERP transactions."
	),
)
bearer = HTTPBearer(
	scheme_name="ControlPlaneServiceKey",
	bearerFormat="opaque-service-key",
	auto_error=False,
)


def require_service_key(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
	expected = os.environ.get("AI_CONTROL_PLANE_SHARED_SECRET", "")
	provided = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else ""
	if not expected or not hmac.compare_digest(provided, expected):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid service credential")


@app.get("/healthz")
def healthz():
	return {"status": "ok"}


@app.get(
	"/readyz",
	summary="Report approved provider configuration readiness",
	responses={
		status.HTTP_503_SERVICE_UNAVAILABLE: {
			"description": "The configured provider is missing or not approved."
		}
	},
)
def readyz():
	provider = os.environ.get("AI_ERP_PROVIDER", "template")
	if provider == "template":
		return {"status": "ready"}
	if provider == "openai":
		try:
			OpenAIConfig.from_environment()
		except OpenAIProviderError:
			raise HTTPException(
				status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
				detail="approved model provider is unavailable",
			) from None
		return {"status": "ready"}
	else:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="approved model provider is unavailable",
		)


@app.post(
	"/v1/proposals/service-closeout-summary",
	summary="Draft a cited service-work-order closeout summary",
	operation_id="draftServiceCloseoutSummary",
	response_model=ProposalResponse,
	response_description="A draft-only proposal. It has no ERP side effect.",
	responses={
		status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid service credential."},
		422: {"description": "Invalid or unsupported request payload."},
		status.HTTP_503_SERVICE_UNAVAILABLE: {
			"description": "The selected approved model provider is unavailable."
		},
	},
	dependencies=[Depends(require_service_key)],
)
def draft_service_closeout_summary(request: ServiceCloseoutSummaryRequest):
	provider = os.environ.get("AI_ERP_PROVIDER", "template")
	if provider == "template":
		return render_development_template(request)
	if provider == "openai":
		logger.info("ai_provider_attempt")
		try:
			result = render_openai(request)
		except OpenAIProviderError as exc:
			logger.error("ai_provider_failure", extra={"error_category": exc.category})
			raise HTTPException(
				status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
				detail="approved model provider is unavailable",
				) from None
		logger.info(
			"ai_provider_success",
			extra={
				"duration_ms": result.audit.duration_ms,
				"input_tokens": result.audit.input_tokens,
				"output_tokens": result.audit.output_tokens,
				"redaction_count": result.audit.redaction_count,
			},
		)
		return result
	else:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="approved model provider is unavailable",
		)
