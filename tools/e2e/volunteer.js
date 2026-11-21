// Phone-size end-to-end test of the volunteer side on the local site.
const { chromium, devices } = require('playwright');
const fs = require('fs');
const { execSync } = require('child_process');
const B = 'http://hr.localhost:8000';
const OUT = process.argv[2];
const MAIL = '/opt/mailcatch/mail';
let fails = 0;
const ok = (c, what, d) => { if (!c) fails++; console.log(c ? 'PASS' : 'FAIL', '|', what, d ? '| ' + d : ''); };
const shot = (p, n) => p.screenshot({ path: `${OUT}/${n}.png` });
const overflow = p => p.evaluate(() => Math.max(document.documentElement.scrollWidth, innerWidth) - screen.width);
const bench = (script, arg) => execSync(`asfrappe /home/frappe/frappe-bench/env/bin/python /home/frappe/${script} ${arg}`, { cwd: '/home/frappe/frappe-bench/sites' }).toString().trim();
async function codeFor(email, after) {
	for (let i = 0; i < 40; i++) {
		const f = fs.readdirSync(MAIL).filter(x => x.includes(email) && +x.split('-')[0] > after).sort().pop();
		if (f) { const m = fs.readFileSync(`${MAIL}/${f}`, 'utf8').replace(/=\r?\n/g, '').match(/>\s*(\d{6})\s*</); if (m) return m[1]; }
		await new Promise(r => setTimeout(r, 250));
	}
	return null;
}
const now = () => Date.now() * 1e6;

(async () => {
	const browser = await chromium.launch({ args: ['--host-resolver-rules=MAP hr.localhost 127.0.0.1'] });
	const mk = () => browser.newContext({ ...devices['iPhone 13'] });
	const id = String(Date.now()).slice(-8);
	const email = `ravi.${id}@example.com`, mobile = '88' + id, pw = 'Green' + id;

	// ---------- sign up ----------
	let ctx = await mk(), page = await ctx.newPage();
	await page.goto(B + '/volunteer-signup', { waitUntil: 'networkidle' });
	await page.click('#send');
	ok((await page.locator('#m1').innerText()).includes('Please fill in'), 'Sign-up: all details are required');
	await page.fill('#nm', 'Ravi Volunteer'); await page.fill('#mob', mobile); await page.fill('#eml', email);
	await page.fill('#addr', '#45, 3rd Cross, 2nd Main'); await page.fill('#road', 'Ashoka Pillar Road');
	await page.fill('#area', 'Jayanagar 2nd Block'); await page.fill('#pin', '560011');
	await page.waitForFunction(() => document.querySelectorAll('#zone option').length > 1);
	await page.selectOption('#zone', 'Z-JAY-001');
	await page.check('#consent');
	await shot(page, 'V1-signup-form');
	ok(await overflow(page) <= 0, 'Sign-up: no sideways scroll');
	let t = now(); await page.click('#send');
	await page.waitForSelector('#step2:not(.hr-hidden)', { timeout: 10000 }).catch(() => {});
	const code = await codeFor(email, t);
	ok(!!code, 'Sign-up: confirmation code emailed');
	await page.fill('#code', code); await page.fill('#pw', 'password'); await page.fill('#pw2', 'password'); await page.click('#verify');
	await page.waitForTimeout(700);
	ok((await page.locator('#m2').innerText()).toLowerCase().includes('mix letters'), 'Sign-up: weak password refused', await page.locator('#m2').innerText());
	await page.fill('#pw', pw); await page.fill('#pw2', pw); await page.click('#verify');
	await page.waitForSelector('#done:not(.hr-hidden)', { timeout: 10000 }).catch(() => {});
	ok(await page.locator('#done:not(.hr-hidden)').count() === 1, 'Sign-up: registered, waiting for approval');
	await shot(page, 'V2-signup-done');
	await ctx.close();

	// ---------- sign in before approval ----------
	ctx = await mk(); page = await ctx.newPage();
	await page.goto(B + '/hasiruratha', { waitUntil: 'networkidle' });
	await shot(page, 'V3-volunteer-login');
	ok(await page.locator('#login-pin').isVisible(), 'Sign-in: password asked for volunteers');
	ok(await page.locator('a[href="/volunteer-reset"]').count() === 1, 'Sign-in: "Forgot or set password" link');
	await page.fill('#login-phone', mobile); await page.fill('#login-pin', pw); await page.click('#login-btn');
	await page.waitForTimeout(1500);
	ok((await page.locator('#login-err').innerText()).includes('approve'), 'Sign-in: not allowed until an admin approves', await page.locator('#login-err').innerText());

	// ---------- admin approves ----------
	t = now();
	bench('approve.py', email);
	let welcome = false;
	for (let i = 0; i < 6 && !welcome; i++) {          // the site's scheduler does this every minute
		execSync("asfrappe bash -c 'cd /home/frappe/frappe-bench && bench --site hr.localhost execute frappe.email.queue.flush'", { stdio: 'ignore' });
		welcome = fs.readdirSync(MAIL).some(f => f.includes(email) && +f.split('-')[0] > t && fs.readFileSync(`${MAIL}/${f}`, 'utf8').includes('approved'));
		if (!welcome) await new Promise(r => setTimeout(r, 2000));
	}
	ok(welcome, 'Approval: volunteer gets a welcome email');

	// ---------- sign in ----------
	await page.fill('#login-pin', 'WrongPass99'); await page.click('#login-btn'); await page.waitForTimeout(1200);
	ok((await page.locator('#login-err').innerText()).includes('not correct'), 'Sign-in: wrong password refused');
	await page.fill('#login-pin', pw); await page.click('#login-btn');
	await page.waitForURL(/\/desk\/hasiruratha\/hasiru_ratha$/, { timeout: 20000 }).catch(() => {});
	ok(/\/desk\/hasiruratha\/hasiru_ratha$/.test(page.url()), 'Sign-in: approved volunteer lands on the volunteer workspace in the Desk', page.url());
	await page.waitForTimeout(1500);
	await shot(page, 'V4-volunteer-app');
	await ctx.close();

	// ---------- old mobile-only sign-in is closed ----------
	const r = await (await browser.newContext()).request.post(B + '/api/method/hasiruratha.api.login_phone', { form: { phone: mobile } });
	ok(!(await r.text()).includes('"found":true'), 'Old mobile-only sign-in no longer works', (await r.text()).slice(0, 90));

	// ---------- forgot / set password for a volunteer added by an admin ----------
	const vEmail = `old.vol.${id}@example.com`;
	const vMob = '66' + id; bench('add_volunteer.py', vMob + ' ' + vEmail);
	ctx = await mk(); page = await ctx.newPage();
	await page.goto(B + '/volunteer-reset', { waitUntil: 'networkidle' });
	await page.fill('#mob', vMob); t = now(); await page.click('#send');
	await page.waitForSelector('#step2:not(.hr-hidden)', { timeout: 10000 }).catch(() => {});
	ok((await page.locator('#sentto').innerText()).includes('ol***@example.com'), 'Reset: code sent to the masked email on record', await page.locator('#sentto').innerText());
	const c2 = await codeFor(vEmail, t);
	await page.fill('#code', c2 || ''); await page.fill('#pw', 'Neem2026tree'); await page.fill('#pw2', 'Neem2026tree'); await page.click('#save');
	await page.waitForSelector('#done:not(.hr-hidden)', { timeout: 10000 }).catch(() => {});
	ok(await page.locator('#done:not(.hr-hidden)').count() === 1, 'Reset: new password saved');
	await shot(page, 'V5-reset-done');
	await page.goto(B + '/hasiruratha', { waitUntil: 'networkidle' });
	await page.fill('#login-phone', vMob); await page.fill('#login-pin', 'Neem2026tree'); await page.click('#login-btn');
	await page.waitForURL(/\/desk\/hasiruratha\/hasiru_ratha$/, { timeout: 20000 }).catch(() => {});
	ok(/\/desk\/hasiruratha\/hasiru_ratha$/.test(page.url()), 'Reset: admin-added volunteer can now sign in (lands in the Desk)', page.url());
	await ctx.close();

	// ---------- citizen upgrades to volunteer ----------
	ctx = await mk(); page = await ctx.newPage();
	const cEmail = `meera.${id}@example.com`, cMob = '77' + id;
	await page.goto(B + '/citizen-login', { waitUntil: 'networkidle' });
	await page.fill('#mob', cMob); await page.fill('#eml', cEmail); await page.click('#send');
	await page.waitForSelector('#namewrap:not(.hr-hidden)'); await page.fill('#nm', 'Meera Citizen');
	t = now(); await page.click('#send'); await page.waitForSelector('#step2:not(.hr-hidden)');
	await page.fill('#code', await codeFor(cEmail, t)); await page.click('#verify');
	await page.waitForURL(u => new URL(u).pathname === '/request', { timeout: 10000 }).catch(() => {});
	await page.goto(B + '/volunteer-signup', { waitUntil: 'networkidle' });
	ok(await page.inputValue('#eml') === cEmail && await page.locator('#eml[readonly]').count() === 1, 'Upgrade: signed-in citizen sees their details filled in');
	await page.fill('#addr', '#3, 1st Cross'); await page.fill('#road', 'Ashoka Pillar Road'); await page.fill('#area', 'Jayanagar 2nd Block');
	await page.fill('#pin', '560011'); await page.waitForFunction(() => document.querySelectorAll('#zone option').length > 1);
	await page.selectOption('#zone', 'Z-JAY-001');
	await page.check('#consent');
	t = now(); await page.click('#send'); await page.waitForSelector('#step2:not(.hr-hidden)', { timeout: 10000 }).catch(() => {});
	await page.fill('#code', (await codeFor(cEmail, t)) || ''); await page.fill('#pw', 'Meera2026x'); await page.fill('#pw2', 'Meera2026x'); await page.click('#verify');
	await page.waitForSelector('#done:not(.hr-hidden)', { timeout: 10000 }).catch(() => {});
	ok(await page.locator('#done:not(.hr-hidden)').count() === 1, 'Upgrade: citizen registered as volunteer (same account)');
	await ctx.close();

	console.log(fails ? `\n${fails} FAILED` : '\nALL PASSED');
	await browser.close();
})();
