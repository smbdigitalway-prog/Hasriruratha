// Desk (admin) test of citizen requests, laptop size, signed in as an HR Admin.
const { chromium, devices } = require('playwright');
const B = 'http://hr.localhost:8000', OUT = process.argv[2];
let fails = 0;
const ok = (c, w, d) => { if (!c) fails++; console.log(c ? 'PASS' : 'FAIL', '|', w, d ? '| ' + d : ''); };
const call = (p, m, args) => p.evaluate(([m, a]) => frappe.xcall(m, a), [m, args]);

(async () => {
	const b = await chromium.launch({ args: ['--host-resolver-rules=MAP hr.localhost 127.0.0.1'] });
	const ctx = await b.newContext({ viewport: { width: 1366, height: 900 } });
	const p = await ctx.newPage();
	const lr = await p.request.post(B + '/api/method/login', { data: { usr: 'boss@example.com', pwd: 'Admin2026pass' } });
	ok(lr.ok(), 'Admin signs in to Desk');

	// workspace
	await p.goto(B + '/app/hr-request', { waitUntil: 'networkidle' }); const wsHref = await p.evaluate(() => [...document.querySelectorAll('a')].find(a => a.textContent.trim() === 'hasiru_ratha_admin')?.getAttribute('href')); console.log('workspace link:', wsHref); await p.goto(B + wsHref, { waitUntil: 'domcontentloaded' }); await p.waitForTimeout(4000);
	const ws = await p.locator('body').innerText().catch(() => '');
	ok(ws.includes('Citizen requests') && ws.includes('Open Citizen Requests'), 'Workspace shows the Citizen requests section and cards');
	await p.screenshot({ path: `${OUT}/D1-workspace.png` });

	// list
	await p.goto(B + '/app/hr-request', { waitUntil: 'networkidle' }); await p.waitForTimeout(1500);
	const rows = await p.locator('.list-row-container').count();
	ok(rows >= 2, 'Request list shows the requests', rows + ' rows');
	ok(/Received|Under review|Scheduled|Accepted/.test(await p.locator('body').innerText()), 'Status shown in the list');
	await p.screenshot({ path: `${OUT}/D2-list.png` });

	for (const t of [{ request_type: 'New location' }, { request_type: 'Maintenance', issue_type: 'Watering', nearest_site: 'S-JAY-001' }])
		await call(p, 'frappe.client.insert', { doc: { doctype: 'HR Request', ...t, gps_lat: 12.9302, gps_lng: 77.5841, road: 'Ashoka Pillar Road',
			area: 'Jayanagar 2nd Block', pincode: '560011', zone: 'Z-JAY-001', citizen_name: 'Test', email: 'kanban.test@example.com' } });
	const reqs = await call(p, 'frappe.client.get_list', { doctype: 'HR Request', fields: ['name', 'request_type', 'status'], order_by: 'creation desc', limit_page_length: 50 });
	const newReq = reqs.find(r => r.request_type === 'New location' && ['Received', 'Under review'].includes(r.status));
	const mReq = reqs.find(r => r.request_type === 'Maintenance' && ['Received', 'Under review', 'Accepted'].includes(r.status));

	// new location -> register as spot
	await p.goto(`${B}/app/hr-request/${newReq.name}`, { waitUntil: 'networkidle' }); await p.waitForTimeout(2500);
	ok(await p.locator('.hr-rq-map .leaflet-tile-loaded, .hr-rq-map .leaflet-pane').count() > 0, 'Form shows the location map');
	await p.screenshot({ path: `${OUT}/D3-form-new.png` });
	await p.getByRole('button', { name: 'Actions' }).click(); await p.getByText('Register as new spot', { exact: true }).locator('visible=true').first().click();
	await p.getByRole('button', { name: 'Yes' }).click(); await p.waitForTimeout(2500);
	let d = await call(p, 'frappe.client.get', { doctype: 'HR Request', name: newReq.name });
	ok(!!d.site && d.status === 'Accepted', 'Register as new spot: creates the spot and accepts the request', `${d.site} / ${d.status}`);

	// maintenance -> plan a visit
	await p.goto(`${B}/app/hr-request/${mReq.name}`, { waitUntil: 'networkidle' }); await p.waitForTimeout(2000);
	await p.getByRole('button', { name: 'Actions' }).click(); await p.getByText('Plan a visit', { exact: true }).locator('visible=true').first().click();
	await p.waitForSelector('.modal.show [data-fieldname="planned_date"] input');
	await p.screenshot({ path: `${OUT}/D4-plan-visit.png` });
	await p.getByRole('button', { name: 'Plan visit' }).click(); await p.waitForTimeout(2500);
	d = await call(p, 'frappe.client.get', { doctype: 'HR Request', name: mReq.name });
	const visits = await call(p, 'frappe.client.get_count', { doctype: 'HR Visit', filters: [['notes', 'like', `%${mReq.name}%`]] });
	ok(d.status === 'Scheduled' && visits >= 1, 'Plan a visit: visit created and request Scheduled', `${d.status}, ${visits} visit(s)`);

	// mark completed
	await p.getByRole('button', { name: 'Status' }).click(); await p.getByText('Completed', { exact: true }).locator('visible=true').first().click();
	await p.waitForTimeout(2000);
	d = await call(p, 'frappe.client.get', { doctype: 'HR Request', name: mReq.name });
	ok(d.status === 'Completed' && !!d.completed_on, 'Status > Completed sets the status and date', `${d.status} ${d.completed_on}`);

	// kanban
	await p.goto(B + '/app/hr-request/view/kanban/HR Requests', { waitUntil: 'networkidle' }); await p.waitForTimeout(2500);
	const kb = await p.locator('body').innerText(); ok(['Received','Under review','Accepted','Scheduled'].every(c => kb.includes(c)) && /New sapling|Care:/.test(kb), 'Kanban board: a column per status, cards titled by what and where');
	await p.screenshot({ path: `${OUT}/D5-kanban.png` });

	// /hasiruratha admin home link
	const m = await b.newContext({ ...devices['iPhone 13'] }), mp = await m.newPage();
	await mp.goto(B + '/hasiruratha', { waitUntil: 'networkidle' });
	await mp.fill('#login-phone', 'boss@example.com'); await mp.fill('#login-pin', 'Admin2026pass'); await mp.click('#login-btn');
	await mp.waitForURL(/\/desk\//, { timeout: 15000 }).catch(() => {});
	ok(mp.url().includes('/desk/'), 'Admin sign-in at /hasiruratha lands in the Desk workspace', mp.url());
	await mp.goto(B + '/hasiruratha', { waitUntil: 'networkidle' });   // Field App shortcut
	await mp.waitForSelector('.hx-req', { timeout: 15000 }).catch(() => {});
	await mp.waitForTimeout(1500);
	const link = await mp.locator('.hx-req').innerText().catch(() => '');
	ok(/Citizen requests/.test(link) && /open/.test(link), 'Admin home in /hasiruratha links to citizen requests with a count', link.replace(/\s+/g, ' '));
	await mp.screenshot({ path: `${OUT}/D6-admin-home.png` });

	console.log(fails ? fails + ' FAILED' : 'ALL PASSED');
	await b.close();
})();
