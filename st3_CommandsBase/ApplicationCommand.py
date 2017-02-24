import sublime, sublime_plugin

def NoneFunction():
	return

class stApplicationCommand(sublime_plugin.ApplicationCommand):
	def SelectItem(Self, Items, OnSelect, OnCancel = NoneFunction):
		sublime.set_timeout(
			lambda: sublime.active_window().show_quick_panel(
				Items,
				lambda index: OnSelect(index) if index > -1 else OnCancel()),
			0)