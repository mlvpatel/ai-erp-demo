import { APIRequestContext, expect, Page, request as requestFactory, test } from "@playwright/test";

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
  expect(technicianRecords.some((record) => record.subject === "AI ERP E2E Unassigned Work Order")).toBeFalsy();

  const dispatcherSession = await newSession(dispatcher);
  try {
    const dispatcherRecords = await matchingWorkOrders(dispatcherSession);
    expect(dispatcherRecords.some((record) => record.subject === "AI ERP E2E Unassigned Work Order")).toBeTruthy();
  } finally {
    await dispatcherSession.dispose();
  }
});

test("five authenticated sessions preserve stock idempotency and finance separation", async () => {
  const technicianSession = await newSession(technician);
  const managerSession = await newSession(manager);
  const financeSession = await newSession(finance);
  const approverSession = await newSession(aiApprover);
  const concurrentManagerSessions = await Promise.all(concurrentManagers.map((user) => newSession(user)));

  try {
    const candidates = await matchingWorkOrders(technicianSession);
    const target = candidates.find((record) => record.subject.startsWith("AI ERP E2E Full Workflow"));
    expect(target).toBeTruthy();
    const workOrderName = target!.name;

    let workOrder = await getDoc(technicianSession, "Service Work Order", workOrderName);
    expect(workOrder.status).toBe("Scheduled");
    workOrder.status = "In Progress";
    workOrder = await saveDoc(technicianSession, workOrder);
    workOrder.time_entries = [
      ...(workOrder.time_entries || []),
      {
        doctype: "Service Work Order Time",
        technician,
        work_date: new Date().toISOString().slice(0, 10),
        time_type: "Work",
        hours: 1,
      },
    ];
    workOrder.closeout_notes = "Synthetic browser closeout completed.";
    workOrder.closeout_evidence = "/private/files/synthetic-e2e-evidence.txt";
    workOrder.status = "Closeout Submitted";
    workOrder = await saveDoc(technicianSession, workOrder);

    const proposalResponse = await call(
      technicianSession,
      "ai_erp_service.ai_drafts.request_closeout_summary",
      { name: workOrderName },
    );
    expect(proposalResponse.ok()).toBeTruthy();
    const proposalName = (await proposalResponse.json()).message.name as string;
    const approval = await call(
      approverSession,
      "ai_erp_core.ai_erp_core.doctype.ai_proposal.ai_proposal.approve",
      { name: proposalName, reviewer_note: "Synthetic evidence reviewed." },
    );
    expect(approval.ok()).toBeTruthy();
    workOrder = await getDoc(technicianSession, "Service Work Order", workOrderName);
    expect(workOrder.status).toBe("Closeout Submitted");
    expect(workOrder.sales_invoice).toBeFalsy();

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

    workOrder.status = "Closed";
    workOrder = await saveDoc(managerSession, workOrder);
    workOrder.status = "Invoice Ready";
    workOrder = await saveDoc(managerSession, workOrder);

    const invoiceMethod =
      "ai_erp_service.ai_erp_service.doctype.service_work_order.service_work_order.make_draft_sales_invoice";
    const managerInvoiceAttempt = await call(managerSession, invoiceMethod, { name: workOrderName });
    expect(managerInvoiceAttempt.ok()).toBeFalsy();

    const firstInvoice = await call(financeSession, invoiceMethod, { name: workOrderName });
    expect(firstInvoice.ok()).toBeTruthy();
    const invoiceName = (await firstInvoice.json()).message as string;
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
      approverSession.dispose(),
      ...concurrentManagerSessions.map((session) => session.dispose()),
    ]);
  }
});

test("configured industry demos expose draft shortages without posting", async () => {
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
