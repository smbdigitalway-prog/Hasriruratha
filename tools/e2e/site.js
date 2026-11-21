// Website test: new home page (/home-new) blocks and links, phone menu, internship form, Green Diary approval.
// Needs: Website Settings navbar/footer = HR Navbar / HR Footer, and seed_care.py (volunteer 9555500001 / Water2026x).
const { chromium, devices } = require('playwright');
const { execSync } = require('child_process');
const B = 'http://hr.localhost:8000', OUT = process.argv[2], PHOTO = process.argv[3];
let fails = 0;
const ok = (c, w, d) => { if (!c) fails++; console.log(c ? 'PASS' : 'FAIL', '|', w, d ? '| ' + d : ''); };

(async () => {
	const b = await chromium.launch({ args: ['--host-resolver-rules=MAP hr.localhost 127.0.0.1'] });
	const g = await (await b.newContext({ ...devices['iPhone 13'] })).newPage();

	// ---- home page blocks and links
	await g.goto(B + '/home-new', { waitUntil: 'networkidle' });
	const text = await g.locator('body').innerText();
	for (const s of ["We don't just plant trees.", 'Trees on our map', 'Our work, every week.', 'The Green Chariot', 'From the Green Diary',
		'Age is just a number.', 'Intern with Hasiru Ratha', 'Learn & Grow', 'Stay connected.'])
		ok(text.includes(s), 'Home shows: ' + s);
	ok(/\d+\s*\n?\s*Trees on our map/.test(text), 'Impact shows a live number');
	const links = await g.evaluate(() => [...new Set([...document.querySelectorAll('a[href^="/"]')].map(a => a.getAttribute('href').split('#')[0]).filter(Boolean))]);
	const broken = [];
	for (const l of links) { const r = await g.request.get(B + l, { maxRedirects: 0 }).catch(() => null); if (!r || r.status() >= 400) broken.push(l + ' ' + (r && r.status())); }
	ok(!broken.length, 'All internal links on the home page work', broken.length ? broken.join(', ') : links.length + ' links');
	const ext = await g.evaluate(() => [...document.querySelectorAll('a[href^="http"]')].map(a => a.href));
	ok(['instagram.com/hasiruratha_blr', 'chat.whatsapp.com/FivfJpNwrBK0NYr0PuU5ks', 'facebook.com/rathahasiru', 'x.com/RathaHasiru', 'linktr.ee/hasiruratha'].every(u => ext.some(h => h.includes(u))),
		'Social links are the ones you gave');

	// ---- phone menu
	await g.click('.hrw-mobile summary');
	ok(await g.locator('.hrw-mobile .hrw-menu a[href="/volunteer-login"]').isVisible(), 'Phone menu opens with sign-in links');
	await g.screenshot({ path: `${OUT}/S1-phone-menu.png` });

	// ---- internship (guest)
	await g.goto(B + '/internship', { waitUntil: 'networkidle' });
	const email = 'intern.' + Date.now() + '@example.com';
	await g.fill('#nm', 'Priya Intern'); await g.fill('#eml', email); await g.fill('#mob', '9876500011');
	await g.selectOption('#dur', '2 months'); await g.check('#skills input[value="Photography"]'); await g.fill('#about', 'I love trees and photos.');
	await g.click('#send'); await g.waitForTimeout(400);
	ok((await g.locator('#m').innerText()).includes('agree'), 'Internship form needs consent');
	await g.check('#consent'); await g.click('#send');
	await g.waitForSelector('#done:not(.hr-hidden)', { timeout: 10000 }).catch(() => {});
	ok(await g.locator('#done:not(.hr-hidden)').count() === 1, 'Internship application sent');
	const bot = await g.evaluate(() => fetch('/api/method/hasiruratha.site_forms.internship_apply', { method: 'POST',
		headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ full_name: 'Bot', email: 'bot@example.com', phone: '9999999999',
			duration: '1 month', consent: 1, website: 'http://spam' }) }).then(r => r.status));
	const count = (q) => JSON.parse(execSync(`asfrappe /home/frappe/frappe-bench/env/bin/python -c "import frappe,json;frappe.init('hr.localhost',sites_path='/home/frappe/frappe-bench/sites');frappe.connect();print(json.dumps(${q}))"`, { cwd: '/home/frappe/frappe-bench/sites' }).toString().trim().split('\n').pop());
	ok(bot === 200 && count(`frappe.db.count('HR Internship Application', {'email': 'bot@example.com'})`) === 0, 'Spam trap: bot submission silently dropped');

	// ---- green diary: volunteer submits, hidden until approved
	const v = await (await b.newContext({ ...devices['iPhone 13'] })).newPage();
	await v.goto(B + '/volunteer-login', { waitUntil: 'networkidle' });
	await v.fill('#login-phone', '9555500001'); await v.fill('#login-pin', 'Water2026x'); await v.click('#login-btn');
	await v.waitForURL(/\/hasiruratha/, { timeout: 15000 }).catch(() => {});
	await v.goto(B + '/green-diary-new', { waitUntil: 'networkidle' });
	const cap = 'Test diary ' + Date.now();
	await v.fill('#cap', cap); await v.fill('#area', 'Jayanagar 2nd Block');
	await v.setInputFiles('#photos', PHOTO);
	await v.waitForFunction(() => document.querySelector('#m').innerText.includes('added'), null, { timeout: 15000 }).catch(() => {});
	await v.check('#consent'); await v.click('#send');
	await v.waitForSelector('#done:not(.hr-hidden)', { timeout: 10000 }).catch(() => {});
	ok(await v.locator('#done:not(.hr-hidden)').count() === 1, 'Volunteer submitted a diary entry');
	await g.goto(B + '/green-diary', { waitUntil: 'networkidle' }); await g.waitForTimeout(800);
	ok(!(await g.locator('body').innerText()).includes(cap), 'Entry is not public before approval');
	execSync(`asfrappe /home/frappe/frappe-bench/env/bin/python -c "import frappe;frappe.init('hr.localhost',sites_path='/home/frappe/frappe-bench/sites');frappe.connect();frappe.set_user('Administrator');d=frappe.get_doc('HR Diary Entry',{'title':'${cap}'});d.status='Approved';d.save();frappe.db.commit()"`, { cwd: '/home/frappe/frappe-bench/sites' });
	await g.goto(B + '/green-diary', { waitUntil: 'networkidle' }); await g.waitForTimeout(800);
	ok((await g.locator('body').innerText()).includes(cap), 'Approved entry appears on /green-diary');
	await g.goto(B + '/home-new', { waitUntil: 'networkidle' });
	ok((await g.locator('#diary').innerText()).includes(cap), 'Approved entry appears on the home page');
	await g.locator('#diary').screenshot({ path: `${OUT}/S2-home-diary.png` });

	console.log(fails ? fails + ' FAILED' : 'ALL PASSED');
	await b.close();
})();
