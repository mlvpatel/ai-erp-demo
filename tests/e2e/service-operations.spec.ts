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
});
