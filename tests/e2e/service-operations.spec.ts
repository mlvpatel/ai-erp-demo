import { expect, Page, test } from "@playwright/test";

const technician = "service.technician@example.test";
const manager = "service.manager@example.test";
const password = process.env.E2E_USER_PASSWORD;

if (!password) throw new Error("E2E_USER_PASSWORD is required");

async function login(page: Page, user: string) {
  const response = await page.request.post("/api/method/login", {
    form: { usr: user, pwd: password },
  });
  expect(response.ok()).toBeTruthy();
}

async function matchingWorkOrders(page: Page) {
  const parameters = new URLSearchParams({
    doctype: "Service Work Order",
    fields: JSON.stringify(["name", "subject", "assigned_technician"]),
    filters: JSON.stringify([["subject", "like", "AI ERP%"]]),
    limit_page_length: "100",
  });
  const response = await page.request.get(`/api/method/frappe.client.get_list?${parameters}`);
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  return body.message as Array<{ name: string; subject: string; assigned_technician: string }>;
}

test("technician browser session cannot discover an unassigned work order", async ({ page }) => {
  await login(page, technician);
  await page.goto("/app/service-work-order");
  await expect(page).not.toHaveTitle(/Login/);
  await expect.poll(() => page.evaluate(() => Boolean((window as any).frappe?.get_route))).toBeTruthy();

  const records = await matchingWorkOrders(page);
  expect(records.length).toBeGreaterThan(0);
  expect(records.every((record) => record.assigned_technician === technician)).toBeTruthy();
  expect(records.some((record) => record.subject === "AI ERP E2E Unassigned Work Order")).toBeFalsy();
});

test("manager browser session sees the aggregate list and profitability report route", async ({ page }) => {
  await login(page, manager);
  await page.goto("/app/service-work-order");
  await expect(page).not.toHaveTitle(/Login/);
  const records = await matchingWorkOrders(page);
  expect(records.some((record) => record.subject === "AI ERP E2E Unassigned Work Order")).toBeTruthy();

  await page.goto("/app/query-report/Service%20Profitability");
  await expect(page).not.toHaveTitle(/Login/);
  await expect.poll(() => page.evaluate(() => (window as any).frappe?.get_route?.()[0])).toBe("query-report");
});
