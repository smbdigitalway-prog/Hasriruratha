from hasiruratha import web_context

no_cache = 1


def get_context(context):
	web_context.base(context, "internship", "Intern with Hasiru Ratha")
	context.full_width = 1
