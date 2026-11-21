// Volunteer Desk test, phone size: a volunteer signs in and lands in the Frappe Desk on the volunteer
// workspace; sees organisation records read-only, never other people's phone / email; can change and log
// care only for their own trees. Needs seed_care.py (volunteer 9555500001 owns the trees of S-JAY-001).
const { chromium, devices } = require('playwright');
const B = 'http://hr.localhost:8000', OUT = process.argv[2];
let fails = 0;
const ok = (c, w, d) => { if (!c) fails++; console.log(c ? 'PASS' : 'FAIL', '|', w, d ? '| ' + d : ''); };
const call = (p, m, args, get) => p.evaluate(([m, args, get]) => {
	const q = new URLSearchParams(); Object.entries(args).forEach(([k, v]) => q.append(k, typeof v === 'string' ? v : JSON.stringify(v)));
	return fetch('/api/method/' + m + (get ? '?' + q : ''), get ? { headers: { Accept: 'application/json' } } : { method: 'POST',
		headers: { Accept: 'application/json', 'X-Frappe-CSRF-Token': frappe.csrf_token }, body: q }).then(r => r.json());
}, [m, args, get]);

(async () => {
	const b = await chromium.launch({ args: ['--host-resolver-rules=MAP hr.localhost 127.0.0.1'] });
	const p = await (await b.newContext({ ...devices['iPhone 13'] })).newPage();
	await p.goto(B + '/hasiruratha', { waitUntil: 'networkidle' });
	ok(p.url().includes('/volunteer-login'), 'Old field app link now goes to sign-in', p.url());
	await p.fill('#login-phone', '9555500001'); await p.fill('#login-pin', 'Water2026x'); await p.click('#login-btn');
	await p.waitForURL(/\/desk/, { timeout: 20000 }).catch(() => {}); await p.waitForTimeout(4000);
	const home = await p.evaluate(() => document.body.innerText);
	ok(p.url().includes('/desk') && home.includes('Welcome to Hasiru Ratha'), 'Volunteer lands on the volunteer workspace in the Desk', p.url());
	ok(home.includes('GPS Tagging') && home.includes('My Trees & Care Log') && home.includes('Citizen Requests'), 'Workspace has field tools and organisation lists');
	ok(!home.includes('Duplicate Reports') && !home.includes('Deleted Sites'), 'Admin-only shortcuts are not shown');
	await p.screenshot({ path: `${OUT}/V1-volunteer-desk.png`, fullPage: true });
	await p.goto(B + '/hasiruratha', { waitUntil: 'networkidle' }); await p.waitForTimeout(1500);
	ok(p.url().includes('/desk'), 'Signed-in volunteer opening /hasiruratha goes to the Desk', p.url());

	// organisation data, read-only; no contact details of others
	const vols = await call(p, 'frappe.client.get_list', { doctype: 'HR Volunteer', fields: ['name', 'volunteer_name', 'phone', 'email'], limit_page_length: 5 }, true);
	const leaked = (vols.message || []).some(v => v.phone || v.email);
	ok(!vols.exc && (vols.message || []).length > 0 && !leaked, 'Volunteer list is readable but phone/email are not returned', JSON.stringify((vols.message || [])[0] || vols.exc_type));
	const one = await call(p, 'frappe.client.get', { doctype: 'HR Volunteer', name: (vols.message || [{}])[0].name || 'x' }, true);
	ok(one.message && !one.message.phone && !one.message.email, 'Opening a volunteer record does not include phone/email');
	await p.goto(B + '/desk/hr-volunteer/' + encodeURIComponent((vols.message || [{}])[0].name), { waitUntil: 'networkidle' }); await p.waitForTimeout(2500);
	const vtext = await p.evaluate(() => document.body.innerText);
	ok(!/\b\d{10}\b/.test(vtext) && !vtext.includes('@example.com'), 'Volunteer form shows no phone number or email');
	await p.screenshot({ path: `${OUT}/V2-volunteer-record.png` });
	const reqs = await call(p, 'frappe.client.get_list', { doctype: 'HR Request', fields: ['name', 'mobile', 'email', 'citizen_name'], limit_page_length: 5 }, true);
	ok(!reqs.exc && !(reqs.message || []).some(r => r.mobile || r.email), 'Citizen requests readable without citizen phone/email');
	const app = await call(p, 'frappe.client.get_list', { doctype: 'HR Application', fields: ['name'] }, true);
	ok(!!app.exc_type || (app.message || []).length === 0, 'Volunteer applications (personal details) are not visible', app.exc_type);
	const site = await call(p, 'frappe.client.set_value', { doctype: 'HR Site', name: 'S-JAY-001', fieldname: 'site_name', value: 'hacked' });
	ok(!!site.exc_type, 'Cannot edit spots', site.exc_type);

	// trees: own vs others
	const mine = (await call(p, 'frappe.client.get_list', { doctype: 'HR Tree', filters: { owner_volunteer_id: 'VOL-CARE1' }, fields: ['name'] }, true)).message.map(t => t.name);
	const other = (await call(p, 'frappe.client.get_list', { doctype: 'HR Tree', filters: [['owner_volunteer_id', 'is', 'not set']], fields: ['name'], limit_page_length: 1 }, true)).message[0].name;
	let r = await call(p, 'frappe.client.set_value', { doctype: 'HR Tree', name: mine[0], fieldname: 'notes', value: 'Guard needs tightening' });
	ok(!r.exc_type, 'Can update notes on own tree', r.exc_type);
	r = await call(p, 'frappe.client.set_value', { doctype: 'HR Tree', name: mine[0], fieldname: 'owner_volunteer_id', value: '' });
	ok(r.exc_type === 'PermissionError', 'Cannot unassign / reassign own tree', r.exc_type);
	r = await call(p, 'frappe.client.set_value', { doctype: 'HR Tree', name: other, fieldname: 'notes', value: 'x' });
	ok(r.exc_type === 'PermissionError', "Cannot edit someone else's tree", r.exc_type);
	r = await call(p, 'frappe.client.insert', { doc: { doctype: 'HR Care Log', tree: other, activity: 'Watering', log_date: new Date().toISOString().slice(0, 10) } });
	ok(!!r.exc_type, "Cannot log care for someone else's tree", r.exc_type);

	// own tree form in the Desk: Log care button
	await p.goto(B + '/desk/hr-tree/' + mine[0], { waitUntil: 'networkidle' }); await p.waitForTimeout(3000);
	ok((await p.evaluate(() => document.body.innerText)).includes('This tree is assigned to you'), 'Own tree form explains what they can do');
	const btn = p.locator('button.hr-log-care');
	ok(await btn.count() === 1 && await btn.isVisible(), 'Own tree shows a "Log care" button on the phone');
	await p.screenshot({ path: `${OUT}/V3-own-tree.png` });
	if (await btn.count()) {
		await btn.click(); await p.waitForTimeout(1200);
		await p.screenshot({ path: `${OUT}/V3b-log-dialog.png` });
		const dlg = p.locator('.modal.show').last();
		await dlg.getByRole('button', { name: 'Save' }).click(); await p.waitForTimeout(2500);
		const n = (await call(p, 'frappe.client.get_count', { doctype: 'HR Care Log', filters: { tree: mine[0] } }, true)).message;
		ok(n >= 1, 'Logging care from the Desk works', n + ' log entries');
	}
	await p.goto(B + '/desk/hr-tree/' + other, { waitUntil: 'networkidle' }); await p.waitForTimeout(3000);
	ok((await p.evaluate(() => document.body.innerText)).includes('Only its assigned volunteer or an admin can change it'), "Someone else's tree is shown read-only");
	ok(await p.locator('button.hr-log-care').count() === 0, "No Log care button on someone else's tree");
	await p.screenshot({ path: `${OUT}/V4-other-tree.png` });
	ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Desk fits the phone width');

	console.log(fails ? fails + ' FAILED' : 'ALL PASSED');
	await b.close();
})();
