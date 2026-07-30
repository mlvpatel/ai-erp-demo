import { APIRequestContext, Browser, expect, Page, request as requestFactory, test } from "@playwright/test";
import path from "node:path";

const technician = "service.technician@example.test";
const dispatcher = "service.dispatcher@example.test";
const manager = "service.manager@example.test";
const finance = "service.finance@example.test";
const aiApprover = "service.ai.approver@example.test";
const concurrentManagers = Array.from(
  { length: 5 },
  (_, index) => `service.manager.concurrent.${index + 1}@example.test`,
);
const distributionUser = "distribution.user@example.test";
const manufacturingUser = "manufacturing.user@example.test";
const password = process.env.E2E_USER_PASSWORD;
const baseURL = process.env.E2E_BASE_URL || "http://frappe:8000";
const siteName = process.env.E2E_SITE_NAME || "ai-erp.localhost";
const assignmentSubjectPrefix = "AI ERP E2E Assignment";

if (!password) throw new Error("E2E_USER_PASSWORD is required");

// Dates must stay relative. The demo site timezone is Europe/Berlin
// (see demo_seed); UTC ISO calendar dates disagree with site today() near
// local midnight and can make closure_due_date look like the past.
function offsetDate(days: number) {
  const siteTz = process.env.E2E_SITE_TIMEZONE || "Europe/Berlin";
  const when = new Date(Date.now() + days * 86_400_000);
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: siteTz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(when);
}

async function login(client: APIRequestContext, user: string) {
  const response = await client.post("/api/method/login", {
    form: { usr: user, pwd: password! },
  });
  expect(response.ok()).toBeTruthy();
}

async function loginPage(page: Page, user: string) {
  await login(page.request, user);
}

async function rolePage(browser: Browser, user: string, viewport = { width: 1440, height: 900 }) {
  const context = await browser.newContext({
    baseURL,
    extraHTTPHeaders: { "X-Frappe-Site-Name": siteName },
    viewport,
  });
  const page = await context.newPage();
  await loginPage(page, user);
  return { context, page };
}

async function openForm(page: Page, route: string, name: string) {
  await page.goto(`/app/${route}/${encodeURIComponent(name)}`);
  await expect(page).not.toHaveTitle(/Login/);
  await expect
    .poll(() => page.evaluate(() => (window as any).cur_frm?.doc?.name || ""))
    .toBe(name);
}

function field(page: Page, fieldname: string) {
  return page.locator(`[data-fieldname="${fieldname}"]`);
}

async function setTextField(page: Page, fieldname: string, value: string) {
  const input = field(page, fieldname).locator("textarea, input").first();
  await expect(input).toBeVisible();
  await input.fill(value);
  await input.press("Tab");
}

async function setLinkField(page: Page, fieldname: string, value: string) {
  const input = field(page, fieldname).locator("input").first();
  await expect(input).toBeVisible();
  await input.fill(value);
  const suggestion = page.getByText(value, { exact: true }).last();
  await expect(suggestion).toBeVisible();
  await suggestion.click();
  await expect
    .poll(() => page.evaluate((name) => (window as any).cur_frm?.doc?.[name] || "", fieldname))
    .toBe(value);
}

async function setSelectField(page: Page, fieldname: string, value: string) {
  const select = field(page, fieldname).locator("select").first();
  await expect(select).toBeVisible();
  await select.selectOption({ label: value });
}

async function saveForm(page: Page) {
  const save = page.locator("button.primary-action").filter({ hasText: /^Save$/ }).first();
  await expect(save).toBeVisible();
  await save.click();
  // Report the blocking message instead of only timing out on a still-dirty form.
  const blockingMessage = await page
    .locator(".modal:visible .modal-body")
    .last()
    .innerText({ timeout: 2000 })
    .catch(() => "");
  expect(blockingMessage.trim(), "save was rejected by a server validation dialog").toBe("");
  await expect.poll(() => page.evaluate(() => Boolean((window as any).cur_frm?.is_dirty?.()))).toBeFalsy();
}

async function clickAction(page: Page, name: string) {
  const action = page.getByRole("button", { name, exact: true }).first();
  if (await action.isVisible()) {
    await action.click();
    return;
  }
  await page.getByRole("button", { name: "Menu", exact: true }).click();
  const menuAction = page.getByText(name, { exact: true }).last();
  await expect(menuAction).toBeVisible();
  await menuAction.click();
}

async function newSession(user: string) {
  const client = await requestFactory.newContext({
    baseURL,
    extraHTTPHeaders: { "X-Frappe-Site-Name": siteName },
  });
  await login(client, user);
  return client;
}

async function call(client: APIRequestContext, method: string, args: Record<string, string>) {
  return client.post(`/api/method/${method}`, { form: args });
}

async function getDoc(client: APIRequestContext, doctype: string, name: string) {
  const parameters = new URLSearchParams({ doctype, name });
  const response = await client.get(`/api/method/frappe.client.get?${parameters}`);
  expect(response.ok()).toBeTruthy();
  return (await response.json()).message as Record<string, any>;
}

async function saveDoc(client: APIRequestContext, doc: Record<string, any>) {
  const response = await call(client, "frappe.client.save", { doc: JSON.stringify(doc) });
  expect(response.ok()).toBeTruthy();
  return (await response.json()).message as Record<string, any>;
}

async function matchingWorkOrders(client: APIRequestContext) {
  const parameters = new URLSearchParams({
    doctype: "Service Work Order",
    fields: JSON.stringify(["name", "subject", "assigned_technician", "status"]),
    filters: JSON.stringify([["subject", "like", "AI ERP%"]]),
    order_by: "creation desc",
    limit_page_length: "100",
  });
  const response = await client.get(`/api/method/frappe.client.get_list?${parameters}`);
  expect(response.ok()).toBeTruthy();
  return (await response.json()).message as Array<Record<string, string>>;
}

async function getList(
  client: APIRequestContext,
  doctype: string,
  fields: string[],
  filters: any[],
) {
  const parameters = new URLSearchParams({
    doctype,
    fields: JSON.stringify(fields),
    filters: JSON.stringify(filters),
    limit_page_length: "100",
  });
  const response = await client.get(`/api/method/frappe.client.get_list?${parameters}`);
  expect(response.ok()).toBeTruthy();
  return (await response.json()).message as Array<Record<string, any>>;
}

test("technician and dispatcher receive different permission-scoped queues", async ({ page }) => {
  await loginPage(page, technician);
  await page.goto("/app/service-work-order");
  await expect(page).not.toHaveTitle(/Login/);
  await expect.poll(() => page.evaluate(() => Boolean((window as any).frappe?.get_route))).toBeTruthy();

  const technicianRecords = await matchingWorkOrders(page.request);
  expect(technicianRecords.length).toBeGreaterThan(0);
  expect(technicianRecords.every((record) => record.assigned_technician === technician)).toBeTruthy();

  const dispatcherSession = await newSession(dispatcher);
  try {
    const dispatcherRecords = await matchingWorkOrders(dispatcherSession);
    expect(dispatcherRecords.some((record) => record.subject.startsWith(assignmentSubjectPrefix))).toBeTruthy();
  } finally {
    await dispatcherSession.dispose();
  }
});

test("dispatcher assigns scheduled work through visible form controls", async ({ browser }) => {
  const dispatcherSession = await newSession(dispatcher);
  const records = await matchingWorkOrders(dispatcherSession);
  const target = records.find(
    (record) => record.subject.startsWith(assignmentSubjectPrefix) && record.status === "Draft",
  );
  expect(target).toBeTruthy();
  await dispatcherSession.dispose();

  const { page } = await rolePage(browser, dispatcher);
  await openForm(page, "service-work-order", target!.name);
  await setSelectField(page, "status", "Scheduled");
  await page.locator("button.primary-action").filter({ hasText: /^Save$/ }).first().click();
  const validationDialog = page.locator(".modal:visible").last();
  await expect(validationDialog).toContainText("Assigned Technician is required");
  await validationDialog.locator(".btn-modal-close").click();

  await clickAction(page, "Suggest Technicians");
  const suggestionDialog = page.locator(".modal:visible").last();
  await expect(suggestionDialog).toContainText("Technician Suggestions");
  await expect(suggestionDialog).toContainText("open_workload");
  await suggestionDialog.locator(".suggestion-assign").first().click();
  await expect
    .poll(() => page.evaluate(() => (window as any).cur_frm?.doc?.assigned_technician || ""))
    .not.toBe("");

  await setLinkField(page, "assigned_technician", technician);
  await saveForm(page);
  await expect(field(page, "assigned_technician").locator("input").first()).toHaveValue(technician);
  await expect(field(page, "status").locator("select").first()).toHaveValue("Scheduled");
});

test("role-driven UI journey preserves stock idempotency and finance separation", async ({ browser }) => {
  const technicianSession = await newSession(technician);
  const managerSession = await newSession(manager);
  const financeSession = await newSession(finance);
  const concurrentManagerSessions = await Promise.all(concurrentManagers.map((user) => newSession(user)));
  const technicianBrowser = await rolePage(browser, technician, { width: 390, height: 844 });
  const managerBrowser = await rolePage(browser, manager);
  const financeBrowser = await rolePage(browser, finance);
  const approverBrowser = await rolePage(browser, aiApprover);

  try {
    const candidates = await matchingWorkOrders(technicianSession);
    const target = candidates.find((record) => record.subject.startsWith("AI ERP E2E Full Workflow"));
    expect(target).toBeTruthy();
    const workOrderName = target!.name;

    const technicianPage = technicianBrowser.page;
    await openForm(technicianPage, "service-work-order", workOrderName);
    await expect(technicianPage.getByRole("button", { name: "Issue Parts", exact: true })).toHaveCount(0);
    await expect(technicianPage.getByRole("button", { name: "Draft Sales Invoice", exact: true })).toHaveCount(0);
    await technicianPage.getByRole("button", { name: "Menu", exact: true }).click();
    await expect(technicianPage.getByText("Issue Parts", { exact: true })).toHaveCount(0);
    await expect(technicianPage.getByText("Draft Sales Invoice", { exact: true })).toHaveCount(0);
    await technicianPage.keyboard.press("Escape");
    const keyboardStatus = field(technicianPage, "status").locator("select").first();
    await keyboardStatus.focus();
    await expect(keyboardStatus).toBeFocused();
    await technicianPage.keyboard.press("ArrowDown");
    await technicianPage.keyboard.press("ArrowUp");
    await setSelectField(technicianPage, "status", "In Progress");
    await saveForm(technicianPage);
    await setTextField(technicianPage, "closeout_notes", "Synthetic browser closeout completed.");
    await field(technicianPage, "closeout_evidence").getByRole("button", { name: "Attach" }).click();
    const uploadDialog = technicianPage.locator(".modal:visible").filter({
      has: technicianPage.getByRole("heading", { name: "Upload" }),
    });
    await expect(uploadDialog).toBeVisible();
    const fileChooserPromise = technicianPage.waitForEvent("filechooser");
    await uploadDialog.getByRole("button", { name: "My Device" }).click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(path.resolve(__dirname, "../fixtures/synthetic-closeout-evidence.txt"));
    await uploadDialog.getByRole("button", { name: "Upload", exact: true }).click();
    await expect(uploadDialog).toBeHidden();
    await expect
      .poll(() => technicianPage.evaluate(() => (window as any).cur_frm?.doc?.closeout_evidence || ""))
      .toContain("synthetic-closeout-evidence.txt");
    await setSelectField(technicianPage, "status", "Closeout Submitted");
    await saveForm(technicianPage);
    await openForm(technicianPage, "service-work-order", workOrderName);
    await clickAction(technicianPage, "Draft AI Closeout Summary");
    await expect
      .poll(() => technicianPage.evaluate(() => (window as any).cur_frm?.doctype || ""))
      .toBe("AI Proposal");
    const proposalName = await technicianPage.evaluate(() => (window as any).cur_frm.doc.name as string);

    await openForm(approverBrowser.page, "ai-proposal", proposalName);
    await clickAction(approverBrowser.page, "Approve Draft");
    await expect
      .poll(() => approverBrowser.page.evaluate(() => (window as any).cur_frm?.doc?.proposal_status))
      .toBe("Approved");

    let workOrder = await getDoc(technicianSession, "Service Work Order", workOrderName);
    expect(workOrder.status).toBe("Closeout Submitted");
    expect(workOrder.sales_invoice).toBeFalsy();

    await openForm(managerBrowser.page, "service-work-order", workOrderName);
    await expect(managerBrowser.page.getByRole("button", { name: "Draft Sales Invoice", exact: true })).toHaveCount(0);

    const issueMethod =
      "ai_erp_service.ai_erp_service.doctype.service_work_order.service_work_order.issue_parts";
    const issueResponses = await Promise.all(
      Array.from({ length: 10 }, (_, index) =>
        call(concurrentManagerSessions[index % concurrentManagerSessions.length], issueMethod, {
          name: workOrderName,
        }),
      ),
    );
    const issuePayloads = await Promise.all(issueResponses.map(async (response) => await response.json()));
    const issueFailures = issueResponses.flatMap((response, index) =>
      response.ok()
        ? []
        : [
            {
              status: response.status(),
              exception: issuePayloads[index].exception || "unknown",
              type: issuePayloads[index].exc_type || "unknown",
            },
          ],
    );
    expect(issueFailures, JSON.stringify(issueFailures)).toEqual([]);
    const issueResults = issuePayloads.map((payload) => payload.message);

    workOrder = await getDoc(managerSession, "Service Work Order", workOrderName);
    const linkedEntries = new Set(
      (workOrder.parts as Array<Record<string, string>>).map((row) => row.stock_entry).filter(Boolean),
    );
    expect(linkedEntries.size).toBe(1);
    const stockEntryName = [...linkedEntries][0];
    expect(
      issueResults.every(
        (value) => value === null || value === undefined || value === stockEntryName,
      ),
    ).toBeTruthy();

    const stockParameters = new URLSearchParams({
      doctype: "Stock Entry",
      fields: JSON.stringify(["name", "docstatus"]),
      filters: JSON.stringify([["remarks", "=", `Issued from Service Work Order ${workOrderName}`]]),
      limit_page_length: "20",
    });
    const stockResponse = await managerSession.get(`/api/method/frappe.client.get_list?${stockParameters}`);
    expect(stockResponse.ok()).toBeTruthy();
    const stockEntries = (await stockResponse.json()).message as Array<Record<string, any>>;
    expect(stockEntries).toEqual([{ name: stockEntryName, docstatus: 1 }]);

    await openForm(managerBrowser.page, "service-work-order", workOrderName);
    await setSelectField(managerBrowser.page, "status", "Closed");
    await saveForm(managerBrowser.page);
    await setSelectField(managerBrowser.page, "status", "Invoice Ready");
    await saveForm(managerBrowser.page);

    const invoiceMethod =
      "ai_erp_service.ai_erp_service.doctype.service_work_order.service_work_order.make_draft_sales_invoice";
    const managerInvoiceAttempt = await call(managerSession, invoiceMethod, { name: workOrderName });
    expect(managerInvoiceAttempt.ok()).toBeFalsy();

    await openForm(financeBrowser.page, "service-work-order", workOrderName);
    await clickAction(financeBrowser.page, "Draft Sales Invoice");
    await expect
      .poll(() => financeBrowser.page.evaluate(() => (window as any).cur_frm?.doctype || ""))
      .toBe("Sales Invoice");
    const invoiceName = await financeBrowser.page.evaluate(() => (window as any).cur_frm.doc.name as string);
    const retryInvoice = await call(financeSession, invoiceMethod, { name: workOrderName });
    expect(retryInvoice.ok()).toBeTruthy();
    expect((await retryInvoice.json()).message).toBe(invoiceName);
    const invoice = await getDoc(financeSession, "Sales Invoice", invoiceName);
    expect(invoice.docstatus).toBe(0);
    expect(invoice.update_stock).toBe(0);
  } finally {
    await Promise.all([
      technicianSession.dispose(),
      managerSession.dispose(),
      financeSession.dispose(),
      ...concurrentManagerSessions.map((session) => session.dispose()),
    ]);
  }
});

test("concurrent AI draft requests converge on one cited proposal", async () => {
  const technicianSession = await newSession(technician);
  const approverSession = await newSession(aiApprover);
  const concurrentManagerSessions = await Promise.all(concurrentManagers.map((user) => newSession(user)));
  try {
    const candidates = await matchingWorkOrders(technicianSession);
    const target = candidates.find(
      (record) =>
        record.subject.startsWith("AI ERP E2E Proposal Concurrency") &&
        record.status === "Closeout Submitted",
    );
    expect(target).toBeTruthy();
    const workOrderName = target!.name;

    const draftMethod = "ai_erp_service.ai_drafts.request_closeout_summary";
    const responses = await Promise.all(
      Array.from({ length: 10 }, (_, index) =>
        call(concurrentManagerSessions[index % concurrentManagerSessions.length], draftMethod, {
          name: workOrderName,
        }),
      ),
    );
    const payloads = await Promise.all(responses.map(async (response) => await response.json()));
    const failures = responses.flatMap((response, index) =>
      response.ok()
        ? []
        : [
            {
              status: response.status(),
              exception: payloads[index].exception || "unknown",
            },
          ],
    );
    expect(failures, JSON.stringify(failures)).toEqual([]);

    const proposalNames = new Set(payloads.map((payload) => payload.message.name as string));
    expect(proposalNames.size).toBe(1);
    const proposalName = [...proposalNames][0];

    const storedProposals = await getList(
      approverSession,
      "AI Proposal",
      ["name", "proposal_status", "policy_outcome"],
      [["reference_name", "=", workOrderName]],
    );
    expect(storedProposals).toEqual([
      { name: proposalName, proposal_status: "Draft", policy_outcome: "Draft Only" },
    ]);
  } finally {
    await Promise.all([
      technicianSession.dispose(),
      approverSession.dispose(),
      ...concurrentManagerSessions.map((session) => session.dispose()),
    ]);
  }
});

test("repair memory draft cites seeded history in the browser", async ({ browser }) => {
  const technicianSession = await newSession(technician);
  const managerSession = await newSession(manager);
  const technicianBrowser = await rolePage(browser, technician);
  try {
    const currentCandidates = await matchingWorkOrders(technicianSession);
    const current = currentCandidates.find(
      (record) =>
        record.subject.startsWith("AI ERP E2E Repair Memory Current") &&
        record.status === "Scheduled",
    );
    expect(current).toBeTruthy();

    const currentDoc = await getDoc(managerSession, "Service Work Order", current!.name);
    const historyCandidates = await getList(
      managerSession,
      "Service Work Order",
      ["name", "subject", "status"],
      [
        ["service_location", "=", currentDoc.service_location],
        ["status", "=", "Closed"],
        ["name", "!=", current!.name],
      ],
    );
    expect(historyCandidates).toHaveLength(1);
    const history = historyCandidates[0];
    expect(history.subject.startsWith("AI ERP E2E Repair Memory History")).toBeTruthy();

    await openForm(technicianBrowser.page, "service-work-order", current!.name);
    await clickAction(technicianBrowser.page, "Draft Repair Memory");
    await expect
      .poll(() => technicianBrowser.page.evaluate(() => (window as any).cur_frm?.doctype || ""))
      .toBe("AI Proposal");

    const proposalName = await technicianBrowser.page.evaluate(
      () => (window as any).cur_frm.doc.name as string,
    );
    const proposal = await getDoc(managerSession, "AI Proposal", proposalName);
    expect(proposal.proposal_type).toBe("Repair Memory");
    expect(proposal.proposal_status).toBe("Draft");
    expect(proposal.policy_outcome).toBe("Draft Only");
    expect(proposal.draft_content).toContain(history!.name);
    expect(proposal.draft_content).toContain("Likely fix based on cited prior work");
    expect(proposal.draft_content).toContain("Synthetic prior fix");
    expect(proposal.draft_content).not.toContain("owner@example.test");

    const historyCitations = (proposal.sources || []).filter(
      (source: { source_field: string; source_name: string }) => source.source_field === "history",
    );
    expect(historyCitations.map((source: { source_name: string }) => source.source_name)).toEqual([
      history!.name,
    ]);

    await expect(technicianBrowser.page.locator(`[data-fieldname="draft_content"]`)).toContainText(
      history!.name,
    );
  } finally {
    await Promise.all([
      technicianSession.dispose(),
      managerSession.dispose(),
      technicianBrowser.context.close(),
    ]);
  }
});

test("evidence replay stays role-scoped across desktop and mobile viewports", async ({ browser }) => {
  const technicianSession = await newSession(technician);
  const financeSession = await newSession(finance);
  const managerSession = await newSession(manager);
  const managerBrowser = await rolePage(browser, manager);
  const technicianBrowser = await rolePage(browser, technician, { width: 390, height: 844 });
  const financeBrowser = await rolePage(browser, finance);
  try {
    const candidates = await matchingWorkOrders(technicianSession);
    const target = candidates.find(
      (record) =>
        record.subject.startsWith("AI ERP E2E Proposal Concurrency") &&
        record.status === "Closeout Submitted",
    );
    expect(target).toBeTruthy();
    const workOrderName = target!.name;

    const technicianPacketDenied = await call(
      technicianSession,
      "ai_erp_service.evidence.get_evidence_packet",
      { name: workOrderName },
    );
    expect(technicianPacketDenied.ok()).toBeFalsy();

    const technicianChainResponse = await call(
      technicianSession,
      "ai_erp_service.evidence.get_evidence_chain",
      { name: workOrderName },
    );
    expect(technicianChainResponse.ok()).toBeTruthy();
    const technicianChain = (await technicianChainResponse.json()).message as Record<string, any>;
    expect(technicianChain.sections.finance).toBeUndefined();
    expect(
      (technicianChain.ledger_narrative?.stages || []).some(
        (stage: { stage: string }) => stage.stage === "finance_handoff",
      ),
    ).toBeFalsy();

    await openForm(managerBrowser.page, "service-work-order", workOrderName);
    await clickAction(managerBrowser.page, "Evidence Replay");
    const managerDialog = managerBrowser.page.locator(".modal:visible").last();
    await expect(managerDialog).toContainText("Evidence complete");
    await expect(managerDialog).toContainText("AI proposal status");
    await expect(managerDialog).toContainText("Ledger narrative");
    await expect(managerDialog).toContainText("finance_handoff");
    await expect(managerDialog).toContainText("Projected margin percent");
    await expect(managerDialog).toContainText("Chain hash");
    const managerClose = managerDialog.locator(".btn-modal-close");
    await expect(managerClose).toBeVisible();
    expect(await managerClose.evaluate((element) => element.tagName)).toBe("BUTTON");
    await managerClose.click();
    await expect(managerDialog).toBeHidden();

    const downloadEvent = managerBrowser.page.waitForEvent("download");
    await clickAction(managerBrowser.page, "Evidence Packet");
    const download = await downloadEvent;
    expect(download.suggestedFilename()).toBe(`evidence-packet-${workOrderName}.json`);

    const managerPacketResponse = await call(
      managerSession,
      "ai_erp_service.evidence.get_evidence_packet",
      { name: workOrderName },
    );
    expect(managerPacketResponse.ok()).toBeTruthy();
    const managerPacket = (await managerPacketResponse.json()).message as Record<string, any>;
    expect(managerPacket.packet_kind).toBe("evidence_to_cash_ledger");
    expect(managerPacket.proposal_idempotency?.length).toBeGreaterThan(0);
    expect(managerPacket.proposal_idempotency[0].input_context_hash).toHaveLength(64);
    expect(managerPacket.chain_hash).toHaveLength(64);

    await openForm(technicianBrowser.page, "service-work-order", workOrderName);
    await clickAction(technicianBrowser.page, "Evidence Replay");
    const technicianDialog = technicianBrowser.page.locator(".modal:visible").last();
    await expect(technicianDialog).toContainText("Evidence complete");
    await expect(technicianDialog).toContainText("Parts issued");
    await expect(technicianDialog).toContainText("Ledger narrative");
    await expect(technicianDialog).not.toContainText("finance_handoff");
    await expect(technicianDialog).not.toContainText("Projected margin percent");
    await expect(technicianDialog).not.toContainText("Invoice handoff");
    await expect(technicianDialog.locator(".btn-modal-close")).toBeVisible();
    await technicianDialog.locator(".btn-modal-close").click();
    await expect(technicianDialog).toBeHidden();
    await expect(
      technicianBrowser.page.getByRole("button", { name: "Evidence Packet", exact: true }),
    ).toHaveCount(0);

    const invoiced = await getList(
      financeSession,
      "Service Work Order",
      ["name", "sales_invoice"],
      [["sales_invoice", "is", "set"]],
    );
    expect(invoiced.length).toBeGreaterThan(0);
    const invoicedWorkOrder = invoiced[0];

    await openForm(financeBrowser.page, "service-work-order", invoicedWorkOrder.name);
    await clickAction(financeBrowser.page, "Evidence Replay");
    const financeDialog = financeBrowser.page.locator(".modal:visible").last();
    await expect(financeDialog).toContainText("Invoice handoff");
    await expect(financeDialog).toContainText("finance_handoff");
    await expect(financeDialog).toContainText("Ledger narrative");
    await expect(financeDialog).toContainText(invoicedWorkOrder.sales_invoice);
    await financeDialog.locator(".btn-modal-close").click();
    await expect(financeDialog).toBeHidden();

    const financeDownloadEvent = financeBrowser.page.waitForEvent("download");
    await clickAction(financeBrowser.page, "Evidence Packet");
    const financeDownload = await financeDownloadEvent;
    expect(financeDownload.suggestedFilename()).toBe(
      `evidence-packet-${invoicedWorkOrder.name}.json`,
    );

    const financePacketResponse = await call(
      financeSession,
      "ai_erp_service.evidence.get_evidence_packet",
      { name: invoicedWorkOrder.name },
    );
    expect(financePacketResponse.ok()).toBeTruthy();
    const financePacket = (await financePacketResponse.json()).message as Record<string, any>;
    expect(financePacket.sales_invoice).toBe(invoicedWorkOrder.sales_invoice);
    expect(financePacket.packet_kind).toBe("evidence_to_cash_ledger");
    expect(Array.isArray(financePacket.proposal_idempotency)).toBeTruthy();
    expect(
      (financePacket.ledger_narrative?.stages || []).some(
        (stage: { stage: string }) => stage.stage === "finance_handoff",
      ),
    ).toBeTruthy();

    await openForm(financeBrowser.page, "service-work-order", invoicedWorkOrder.name);
    await clickAction(financeBrowser.page, "Evidence Replay");
    const financeInvoiceDialog = financeBrowser.page.locator(".modal:visible").last();
    await financeInvoiceDialog.getByRole("button", { name: "Open Draft Invoice", exact: true }).click();
    await expect
      .poll(() => financeBrowser.page.evaluate(() => (window as any).cur_frm?.doctype || ""))
      .toBe("Sales Invoice");
    await expect
      .poll(() => financeBrowser.page.evaluate(() => (window as any).cur_frm?.doc?.name || ""))
      .toBe(invoicedWorkOrder.sales_invoice);
  } finally {
    await Promise.all([
      technicianSession.dispose(),
      financeSession.dispose(),
      managerSession.dispose(),
      managerBrowser.context.close(),
      technicianBrowser.context.close(),
      financeBrowser.context.close(),
    ]);
  }
});

test("technician mobile journey guides validation and cannot-close without finance access", async ({ browser }) => {
  const managerSession = await newSession(manager);
  const technicianSession = await newSession(technician);
  const technicianBrowser = await rolePage(browser, technician, { width: 390, height: 844 });
  try {
    const subject = `AI ERP E2E Mobile ${Date.now()}`;
    const insertResponse = await call(managerSession, "frappe.client.insert", {
      doc: JSON.stringify({
        doctype: "Service Work Order",
        subject,
        customer: "AI ERP Demo Customer",
        service_location: "SVC-LOC-.00001",
        status: "Draft",
      }),
    });
    expect(insertResponse.ok()).toBeTruthy();
    const inserted = (await insertResponse.json()).message as Record<string, any>;
    inserted.assigned_technician = technician;
    inserted.scheduled_start = `${offsetDate(1)} 09:00:00`;
    inserted.scheduled_end = `${offsetDate(1)} 11:00:00`;
    inserted.closure_owner = manager;
    inserted.closure_due_date = offsetDate(7);
    inserted.status = "Scheduled";
    await saveDoc(managerSession, inserted);
    const workOrderName = inserted.name as string;

    const page = technicianBrowser.page;
    await page.goto("/app/service-work-order");
    await expect(page).not.toHaveTitle(/Login/);
    await expect(page.getByText(subject).first()).toBeVisible();

    await openForm(page, "service-work-order", workOrderName);

    const saveButton = page.locator("button.primary-action").filter({ hasText: /^Save$/ }).first();
    await expect(saveButton).toBeVisible();
    const saveBox = await saveButton.boundingBox();
    expect(saveBox, "Save must render a measurable touch target").toBeTruthy();
    expect(saveBox!.height).toBeGreaterThanOrEqual(44);

    const statusSelect = field(page, "status").locator("select").first();
    await expect(statusSelect).toBeVisible();
    const statusAccessibleName = await statusSelect.evaluate((element) => {
      const labeledBy = element.getAttribute("aria-labelledby");
      if (labeledBy) {
        return labeledBy
          .split(/\s+/)
          .map((id) => document.getElementById(id)?.textContent?.trim() || "")
          .join(" ")
          .trim();
      }
      const ariaLabel = element.getAttribute("aria-label");
      if (ariaLabel) return ariaLabel.trim();
      const control = element.closest(".frappe-control");
      const label = control?.querySelector(".control-label, label");
      return (label?.textContent || "").trim();
    });
    expect(statusAccessibleName.toLowerCase()).toContain("status");

    const statusBox = await statusSelect.boundingBox();
    expect(statusBox, "Status select must render a measurable touch target").toBeTruthy();
    expect(statusBox!.height).toBeGreaterThanOrEqual(44);

    await statusSelect.focus();
    await expect(statusSelect).toBeFocused();
    await page.keyboard.press("Tab");
    await setSelectField(page, "status", "In Progress");
    await saveForm(page);

    await setSelectField(page, "status", "Closeout Submitted");
    await saveButton.click();
    const validationDialog = page.locator(".modal:visible").last();
    await expect(validationDialog).toContainText("time entry is required");
    const validationBody = validationDialog.locator(".modal-body, .msgprint").first();
    await expect(validationBody).toBeVisible();
    const validationMetrics = await validationBody.evaluate((element) => {
      const styles = window.getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return {
        fontSize: Number.parseFloat(styles.fontSize),
        width: rect.width,
        height: rect.height,
        text: (element.textContent || "").trim(),
      };
    });
    expect(validationMetrics.fontSize).toBeGreaterThanOrEqual(16);
    expect(validationMetrics.width).toBeGreaterThan(200);
    expect(validationMetrics.height).toBeGreaterThan(24);
    expect(validationMetrics.text.toLowerCase()).toContain("time entry is required");
    await validationDialog.locator(".btn-modal-close").click();
    await expect(validationDialog).toBeHidden();

    await setSelectField(page, "status", "In Progress");
    await setSelectField(page, "status", "Cannot Close");
    const reasonSelect = field(page, "cannot_close_reason").locator("select").first();
    await expect(reasonSelect).toBeVisible();
    const reasonAccessibleName = await reasonSelect.evaluate((element) => {
      const control = element.closest(".frappe-control");
      const label = control?.querySelector(".control-label, label");
      return (element.getAttribute("aria-label") || label?.textContent || "").trim();
    });
    expect(reasonAccessibleName.toLowerCase()).toMatch(/cannot close|reason/);
    await setSelectField(page, "cannot_close_reason", "Parts unavailable");
    await saveForm(page);

    const saved = await getDoc(technicianSession, "Service Work Order", workOrderName);
    expect(saved.status).toBe("Cannot Close");
    expect(saved.closure_exception).toBeTruthy();
    const exception = await getDoc(
      technicianSession,
      "Service Closure Exception",
      saved.closure_exception,
    );
    expect(exception.status).toBe("Open");
    expect(exception.exception_owner).toBe(manager);

    const financeStatuses = await page.evaluate(() => {
      const frm = (window as any).cur_frm;
      return {
        hourly_rate: frm?.fields_dict?.hourly_rate?.disp_status || "None",
        projected_revenue: frm?.fields_dict?.projected_revenue?.disp_status || "None",
        assigned_technician: frm?.fields_dict?.assigned_technician?.disp_status || "None",
      };
    });
    expect(financeStatuses.hourly_rate).not.toBe("Write");
    expect(financeStatuses.projected_revenue).not.toBe("Write");
    expect(financeStatuses.assigned_technician).not.toBe("Write");
  } finally {
    await Promise.all([
      managerSession.dispose(),
      technicianSession.dispose(),
      technicianBrowser.context.close(),
    ]);
  }
});

test("configured industry demos expose draft shortages without posting", async ({ browser }) => {
  const distributionSession = await newSession(distributionUser);
  const manufacturingSession = await newSession(manufacturingUser);
  try {
    const distributionOrders = await getList(
      distributionSession,
      "Sales Order",
      ["name", "docstatus"],
      [["po_no", "=", "AI-ERP-CONFIG-DEMO-DISTRIBUTION"]],
    );
    expect(distributionOrders).toHaveLength(1);
    expect(distributionOrders[0].docstatus).toBe(0);
    const distributionWarehouses = await getList(
      distributionSession,
      "Warehouse",
      ["name"],
      [["warehouse_name", "like", "AI ERP Distribution%"]],
    );
    expect(distributionWarehouses).toHaveLength(2);
    const distributionOrder = await getDoc(
      distributionSession,
      "Sales Order",
      distributionOrders[0].name,
    );
    expect(distributionOrder.items).toHaveLength(2);
    expect(new Set(distributionOrder.items.map((row: any) => row.warehouse)).size).toBe(1);
    const distributionBins = await getList(
      distributionSession,
      "Bin",
      ["item_code", "warehouse", "actual_qty"],
      [["item_code", "in", distributionOrder.items.map((row: any) => row.item_code)]],
    );
    expect(distributionBins.reduce((total, row) => total + Number(row.actual_qty || 0), 0)).toBe(0);
    const distributionBrowser = await rolePage(browser, distributionUser, { width: 390, height: 844 });
    await openForm(distributionBrowser.page, "sales-order", distributionOrders[0].name);
    await expect(field(distributionBrowser.page, "status")).toContainText("Draft");
    await expect(
      distributionBrowser.page.getByRole("link", { name: /^AI-ERP-DIST-AVAILABLE:/ }),
    ).toBeVisible();
    await expect(
      distributionBrowser.page.getByRole("link", { name: /^AI-ERP-DIST-SHORTAGE:/ }),
    ).toBeVisible();

    const manufacturingOrders = await getList(
      manufacturingSession,
      "Sales Order",
      ["name", "docstatus"],
      [["po_no", "=", "AI-ERP-CONFIG-DEMO-MANUFACTURING"]],
    );
    expect(manufacturingOrders).toHaveLength(1);
    expect(manufacturingOrders[0].docstatus).toBe(0);
    const manufacturingWarehouses = await getList(
      manufacturingSession,
      "Warehouse",
      ["name"],
      [["warehouse_name", "like", "AI ERP Manufacturing%"]],
    );
    expect(manufacturingWarehouses).toHaveLength(3);
    const manufacturingBoms = await getList(
      manufacturingSession,
      "BOM",
      ["name", "item", "docstatus"],
      [["item", "=", "AI-ERP-MFG-FINISHED"]],
    );
    expect(manufacturingBoms).toHaveLength(1);
    expect(manufacturingBoms[0].docstatus).toBe(0);
    const bom = await getDoc(manufacturingSession, "BOM", manufacturingBoms[0].name);
    const componentBins = await getList(
      manufacturingSession,
      "Bin",
      ["item_code", "actual_qty"],
      [["item_code", "in", bom.items.map((row: any) => row.item_code)]],
    );
    expect(componentBins.reduce((total, row) => total + Number(row.actual_qty || 0), 0)).toBe(0);
    const manufacturingBrowser = await rolePage(browser, manufacturingUser, { width: 390, height: 844 });
    await openForm(manufacturingBrowser.page, "bom", manufacturingBoms[0].name);
    await expect(field(manufacturingBrowser.page, "docstatus")).toHaveCount(0);
    await expect(
      manufacturingBrowser.page.getByRole("link", { name: /^AI-ERP-MFG-FINISHED:/ }),
    ).toBeVisible();
    await expect(
      manufacturingBrowser.page.getByRole("link", { name: /^AI-ERP-MFG-COMPONENT-A:/ }),
    ).toBeVisible();
    await expect(
      manufacturingBrowser.page.getByRole("link", { name: /^AI-ERP-MFG-COMPONENT-SHORTAGE:/ }),
    ).toBeVisible();
  } finally {
    await Promise.all([distributionSession.dispose(), manufacturingSession.dispose()]);
  }
});

test("manager can open the permission-scoped profitability report", async ({ page }) => {
  await loginPage(page, manager);
  await page.goto("/app/query-report/Service%20Profitability");
  await expect(page).not.toHaveTitle(/Login/);
  await expect.poll(() => page.evaluate(() => (window as any).frappe?.get_route?.()[0])).toBe("query-report");
  await expect(page.getByText("Margin Risks")).toBeVisible();
});

test("margin leakage summary is manager or finance only on the work-order desk", async ({ browser }) => {
  const technicianSession = await newSession(technician);
  const financeSession = await newSession(finance);
  const managerBrowser = await rolePage(browser, manager);
  const technicianBrowser = await rolePage(browser, technician);
  const financeBrowser = await rolePage(browser, finance);
  try {
    const technicianOrders = await matchingWorkOrders(technicianSession);
    expect(technicianOrders.length).toBeGreaterThan(0);
    const workOrderName = technicianOrders[0].name;

    await openForm(managerBrowser.page, "service-work-order", workOrderName);
    await clickAction(managerBrowser.page, "Margin Leakage Summary");
    const managerDialog = managerBrowser.page.locator(".modal:visible").last();
    await expect(managerDialog).toContainText("Category counts");
    await expect(managerDialog).toContainText("High-risk work orders");
    await expect(managerDialog).toContainText("Failed inspection");
    await expect(managerDialog).toContainText("Risks and evidence");
    await expect(managerDialog.getByText("Status filter")).toBeVisible();
    await expect(managerDialog.getByText("From date")).toBeVisible();
    await expect(managerDialog.getByRole("button", { name: "Apply Filter" })).toBeVisible();
    await managerDialog.locator(".btn-modal-close").click();
    await expect(managerDialog).toBeHidden();

    const invoiced = await getList(
      financeSession,
      "Service Work Order",
      ["name", "sales_invoice"],
      [["sales_invoice", "is", "set"]],
    );
    expect(invoiced.length).toBeGreaterThan(0);
    await openForm(financeBrowser.page, "service-work-order", invoiced[0].name);
    await clickAction(financeBrowser.page, "Margin Leakage Summary");
    const financeDialog = financeBrowser.page.locator(".modal:visible").last();
    await expect(financeDialog).toContainText("Category counts");
    await expect(financeDialog).toContainText("Deterministic categories only");
    await expect(financeDialog.getByText("To date")).toBeVisible();
    await financeDialog.locator(".btn-modal-close").click();
    await expect(financeDialog).toBeHidden();

    await openForm(technicianBrowser.page, "service-work-order", workOrderName);
    await expect(
      technicianBrowser.page.getByRole("button", { name: "Margin Leakage Summary", exact: true }),
    ).toHaveCount(0);
    const menu = technicianBrowser.page.getByRole("button", { name: "Menu", exact: true });
    if (await menu.isVisible()) {
      await menu.click();
      await expect(technicianBrowser.page.getByText("Margin Leakage Summary", { exact: true })).toHaveCount(0);
    }
  } finally {
    await Promise.all([
      technicianSession.dispose(),
      financeSession.dispose(),
      managerBrowser.context.close(),
      technicianBrowser.context.close(),
      financeBrowser.context.close(),
    ]);
  }
});
