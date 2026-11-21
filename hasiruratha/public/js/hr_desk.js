// Hasiru Ratha in the Desk: the bare /desk page (Frappe's app "Desktop") is empty for our users, so send
// admins and volunteers to their own Hasiru Ratha workspace instead.
(function () {
	const home = () => (window.frappe && frappe.boot && frappe.boot.hr_home) || null;
	const check = () => {
		const path = window.location.pathname.replace(/\/+$/, "");
		if ((path === "/desk" || path === "/app") && home()) window.location.replace(home());
	};
	document.addEventListener("DOMContentLoaded", () => {
		check();
		if (window.frappe && frappe.router && frappe.router.on) frappe.router.on("change", check);
	});
})();
